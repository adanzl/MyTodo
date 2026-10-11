"""Chat 管理器。

该模块负责两侧的会话管理：

1. **WebSocket（Flask-SocketIO）侧**：
   - 为每个 Socket 客户端维护 `ClientContext`（AI/ASR/TTS 管线）；
   - 处理文本与音频消息，转发/聚合结果并推送给前端；
   - chat_room 模式下将消息写入 Redis 列表用于房间广播。
2. **历史记录查询 / 导出侧**（HTTP 接口用到）：
   - `get_messages` / `get_conversations` 查询 Dify 的单页数据；
   - `collect_messages` 翻页拉全某个会话的消息；
   - `export_messages` 按日期范围汇总成 CSV，并直接返回可下发的文件响应。

Dify 的 HTTP 细节仍封装在 `AILocal`（`core/ai/ai_local.py`），本类只做编排。
"""

import base64
import csv
import io
import time
from datetime import datetime
from urllib.parse import quote

import core.db.rds_mgr as rds_mgr
from core.ai.ai_local import AILocal
from core.chat.asr_factory import create_asr_client
from core.chat import chat_request_store
from core.config import app_logger
from core.chat import tts_cache
from core.chat.tts_phrase_buffer import TtsPhraseBuffer
from core.tts.tts_client import TTSClient
from core.utils import _err, _ok
from flask import Response, json, request

log = app_logger

MSG_TYPE_ERROR = "error"

EVENT_MESSAGE = "message"

# 查询 Dify 时的单页条数上限（Dify 自身限制，超出会 422）与默认值
MAX_LIMIT = 100
DEFAULT_LIMIT = 20
# 导出时每页条数（Dify 单页上限 100）与翻页上限（防御异常数据）
EXPORT_PAGE_SIZE = 100
EXPORT_MAX_PAGES = 200
# 单次导出能覆盖的最大条数
MAX_EXPORT_MESSAGES = EXPORT_PAGE_SIZE * EXPORT_MAX_PAGES
# 导出列里的时间格式
EXPORT_TIME_FMT = '%Y-%m-%d %H:%M:%S'
# 导出响应类型（带 charset，Excel 才不会把中文读成乱码）
EXPORT_CONTENT_TYPE = 'text/csv; charset=utf-8'


class ClientContext:
    """单个 Socket 客户端上下文。

    包含：
    - `AILocal`: 对话流式输出
    - `AsrClient`: 语音识别（音频 -> 文本）
    - `TTSClient`: 语音合成（文本 -> 音频）
    """

    def __init__(self, sid, socketio):
        self.sid = sid
        self.pending_audio = False
        self.ai = AILocal(self.on_ai_msg, self.on_err)
        self.asr = create_asr_client(self.on_asr_result, self.on_asr_err)  # 语音识别
        self.tts = TTSClient(self.on_tts_msg, self.on_tts_err)  # 语音合成
        self.autoTTS = False
        self.socketio = socketio
        # clientRequestId -> accepted | asr | ai | done | cancelled（进程内缓存）
        self._request_phase: dict[str, str] = {}
        self._tts_phrase_buffer = TtsPhraseBuffer()
        self._tts_stream_msg_id = ''
        self._tts_emit_request_id: str | None = None

    def _phase(self, client_request_id: str) -> str | None:
        rid = client_request_id or ''
        if not rid:
            return None
        phase = chat_request_store.get_phase(self.ai.user, rid)
        if phase:
            self._request_phase[rid] = phase
        elif rid in self._request_phase:
            del self._request_phase[rid]
        return phase

    def _set_phase(self, client_request_id: str, phase: str) -> None:
        rid = client_request_id or ''
        if not rid:
            return
        self._request_phase[rid] = phase
        chat_request_store.set_phase(self.ai.user, rid, phase)

    def _emit_msg_accepted(self, client_request_id: str, kind: str):
        if not client_request_id:
            return
        attempt = chat_request_store.get_attempt(self.ai.user, client_request_id)
        self.socketio.emit(
            'msgAccepted',
            {
                'clientRequestId': client_request_id,
                'kind': kind,
                'attempt': attempt,
            },
            room=self.sid,
        )

    def note_text_request(self, client_request_id: str) -> str:
        """返回 new | retry_ai | ignore。"""
        rid = client_request_id or ''
        if not rid:
            return 'new'
        phase = self._phase(rid)
        if phase is None:
            if chat_request_store.try_transition(
                self.ai.user, rid, None, 'accepted'
            ):
                self._request_phase[rid] = 'accepted'
                self._emit_msg_accepted(rid, 'text')
                return 'new'
            phase = self._phase(rid)
        if phase in chat_request_store.RETRYABLE:
            if chat_request_store.try_transition(
                self.ai.user, rid, chat_request_store.RETRYABLE, 'accepted'
            ):
                self._request_phase[rid] = 'accepted'
                self._emit_msg_accepted(rid, 'text')
                return 'retry_ai'
            self._emit_msg_accepted(rid, 'text')
            return 'ignore'
        if phase == 'accepted':
            self._emit_msg_accepted(rid, 'text')
            return 'retry_ai'
        if phase in ('ai', 'done', 'cancelled'):
            self._emit_msg_accepted(rid, 'text')
            return 'ignore'
        self._emit_msg_accepted(rid, 'text')
        return 'ignore'

    def note_audio_request(self, client_request_id: str) -> str:
        """返回 new | continue | ignore。"""
        rid = client_request_id or ''
        if not rid:
            return 'new'
        phase = self._phase(rid)
        if phase is None:
            if chat_request_store.try_transition(
                self.ai.user, rid, None, 'accepted'
            ):
                self._request_phase[rid] = 'accepted'
                self._emit_msg_accepted(rid, 'audio')
                return 'new'
            phase = self._phase(rid)
        if phase in ('accepted', 'asr'):
            self._emit_msg_accepted(rid, 'audio')
            return 'continue'
        self._emit_msg_accepted(rid, 'audio')
        return 'ignore'

    def mark_request_asr(self, client_request_id: str):
        if client_request_id:
            self._set_phase(client_request_id, 'asr')

    def try_begin_ai(self, client_request_id: str) -> bool:
        """在调用 stream_msg 前原子登记为 ai，避免生成期间仍被视为 accepted。"""
        rid = client_request_id or ''
        if not rid:
            return True
        ok = chat_request_store.try_transition(
            self.ai.user,
            rid,
            frozenset({'accepted', 'asr'}),
            'ai',
        )
        if ok:
            self._request_phase[rid] = 'ai'
        return ok

    def mark_request_done(self, client_request_id: str, attempt: int = 0):
        rid = client_request_id or ''
        if not rid:
            return
        if chat_request_store.mark_done(self.ai.user, rid, attempt):
            self._request_phase[rid] = 'done'

    def mark_request_cancelled(self, client_request_id: str):
        if client_request_id:
            self._set_phase(client_request_id, 'cancelled')

    def query_request_phases(self, request_ids: list[str]) -> list[dict]:
        items = []
        for rid in request_ids[:20]:
            rid = (rid or '').strip()
            if not rid:
                continue
            rec = chat_request_store.get_record(self.ai.user, rid)
            items.append(chat_request_store.record_to_client_item(rid, rec))
        return items

    def close(self):
        self.asr.close()

    def cancel_asr(self, request_id: str = ""):
        self.asr.cancel_session(request_id)

    def on_asr_result(self, text, client_request_id=""):
        '''
            处理asr的返回消息，收到消息后转发给ai和客户端
        '''
        if text == '' or not client_request_id:
            return
        rid = client_request_id
        phase = self._phase(rid)
        if phase not in ('accepted', 'asr'):
            log.info(
                f"[CHAT] ignore ASR result for {rid} (phase={phase!r})"
            )
            return
        if not self.try_begin_ai(rid):
            return
        msg = {"content": text, "clientRequestId": rid}
        self.socketio.emit('msgAsr', msg, room=self.sid)
        self.ai.stream_msg(text, client_request_id=rid)

    def _reset_auto_tts_stream(self, msg_id: str = '') -> None:
        self._tts_phrase_buffer.reset()
        self._tts_stream_msg_id = msg_id or ''

    def _ensure_auto_tts_stream(self, msg_id: str) -> bool:
        """在 feed AI chunk 之前绑定本轮 TTS，避免首个 chunk 的缓冲被重置丢失。"""
        msg_id = msg_id or ''
        if not msg_id:
            return False
        if msg_id != self._tts_stream_msg_id:
            self._reset_auto_tts_stream(msg_id)
            self.tts.start_deferred_cache(msg_id)
        return True

    def _flush_auto_tts_phrases(self, phrases: list[str], msg_id: str) -> None:
        if not msg_id or not phrases:
            return
        for phrase in phrases:
            self.tts.stream_msg(text=phrase, id=msg_id)

    def _finish_auto_tts(self) -> None:
        msg_id = self._tts_stream_msg_id
        tail = self._tts_phrase_buffer.flush_rest()
        if tail and msg_id:
            self.tts.stream_msg(text=tail, id=msg_id)
        if msg_id:
            # 先记录完整文本，再结束流。SDK 的 on_complete 可能同步或异步触发，
            # 真正写入“complete”缓存统一放在 on_complete，避免把半截音频标成完整。
            self.tts.prepare_deferred_cache(
                self._tts_phrase_buffer.full_text,
                role=self.tts.role,
                speed=self.tts.speed,
            )
        self.tts.stream_complete()
        self._reset_auto_tts_stream()

    def on_ai_msg(
        self,
        text,
        id,
        type=0,
        client_request_id="",
        *,
        attempt=0,
    ):
        '''
            处理AI的回复消息
        '''
        rid = client_request_id or ''
        if rid and not chat_request_store.matches_attempt(
            self.ai.user, rid, attempt
        ):
            log.info(
                f"[CHAT] ignore stale AI msg for {rid} (attempt={attempt})"
            )
            return
        if type == 0:
            event = 'msgChat'
            if rid and text:
                chat_request_store.append_reply_text(
                    self.ai.user, rid, text, attempt
                )
            if self.autoTTS and text and self._ensure_auto_tts_stream(id or ''):
                self._flush_auto_tts_phrases(
                    self._tts_phrase_buffer.feed(text),
                    id or '',
                )
        else:
            event = 'endChat'
            if self.autoTTS:
                self._finish_auto_tts()
            if rid:
                self.mark_request_done(rid, attempt)

        payload = {
            'content': text,
            'aiConversationId': self.ai.aiConversationId,
            'id': id,
            'clientRequestId': client_request_id,
            'attempt': int(attempt or 0),
        }
        self.socketio.emit(event, payload, room=self.sid)

    def on_asr_err(self, err: Exception):
        session = self.asr._session
        rid = session.request_id if session else ""
        attempt = chat_request_store.get_attempt(self.ai.user, rid) if rid else 0
        self.on_err(err, rid, attempt=attempt)

    def on_tts_err(self, err: Exception):
        self.on_err(err, "")

    def on_err(self, err: Exception, client_request_id="", *, attempt=0):
        log.error(f"[CHAT] Error: {err}")
        rid = client_request_id or ''
        if rid and not chat_request_store.matches_attempt(
            self.ai.user, rid, attempt
        ):
            log.info(
                f"[CHAT] ignore stale error for {rid} (attempt={attempt})"
            )
            return
        if rid:
            if chat_request_store.mark_failed(
                self.ai.user, rid, str(err), attempt
            ):
                self._request_phase[rid] = 'failed'
        msg = {
            "type": MSG_TYPE_ERROR,
            "content": str(err),
            "clientRequestId": client_request_id,
            "attempt": int(attempt or 0),
        }
        self.socketio.emit('error', msg, room=self.sid)

    def _emit_tts_playback(self, event: str, payload: dict) -> None:
        if self._tts_emit_request_id:
            payload = {**payload, 'ttsRequestId': self._tts_emit_request_id}
        self.socketio.emit(event, payload, room=self.sid)

    def on_tts_msg(self, data, type=0):
        '''
            处理tts的返回消息，type=0正常的流式返回，type=1表示tts已经结束的消息
        '''
        if type == 0:
            self._emit_tts_playback('dataAudio', {'type': 'tts', 'data': data})
        else:
            self._emit_tts_playback('endAudio', {'content': data})
            # 手动朗读的一次 request 到这里已经结束，不能污染下一次自动/手动 TTS。
            self._tts_emit_request_id = None


def translate_text(text):
    return text


class ChatMgr:

    def __init__(self):
        self.clients: dict[str, ClientContext] = {}  # sid -> ClientContext

    def init(self, socketio):
        log.info("[CHAT] ChatMgr init")
        self.socketio = socketio
        self._register_events()

    def add_client(self, sid):
        try:
            self.clients[sid] = ClientContext(sid, self.socketio)
            return self.clients[sid]
        except Exception as e:
            log.error(f"[CHAT] Error adding client {sid}: {e}")

    def remove_client(self, sid):
        if sid in self.clients:
            del self.clients[sid]

    # ---------------- 历史记录查询 / 导出 ----------------

    @staticmethod
    def _parse_limit(raw) -> int:
        """把 limit 收敛到 `[1, MAX_LIMIT]`，非法值回落到 `DEFAULT_LIMIT`。

        `MAX_LIMIT` 是 Dify 自身的单页上限（超出会 422），必须在这里收敛。
        """
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return DEFAULT_LIMIT
        return max(1, min(value, MAX_LIMIT))

    def get_messages(self, conversation_id, limit=None, user=None, first_id=None) -> dict:
        """拉取某个会话的消息列表（单页，时间从旧到新）。

        Args:
            conversation_id: Dify 会话 id
            limit: 每页条数；会收敛到 `[1, MAX_LIMIT]`，非法值回落到 `DEFAULT_LIMIT`
            user: Dify 侧用户标识，同时决定用哪个 Dify 应用
            first_id: 本页最旧一条的 id，用于往更早翻页

        Returns:
            `_ok(<Dify 原始响应 {limit, has_more, data:[...]}>`；取数失败时
            底层 `AILocal.get_chat_messages` 会吞掉异常返回 `None`，此处**保持**
            `code:0` + `data:null` 这一既有行为不变（移动端历史加载依赖它的形状），
            排查该「静默失败」是另一件事，改动需单独评估。

        `limit` 与 `get_conversations` 一样在这里收敛：Dify 的单页上限是 100，
        越界会被它 422 拒绝；而上面的静默失败会把 422 表现成 `data:null`，
        与「这个会话没有消息」无法区分，所以不能把非法值原样透传下去。
        """
        try:
            return _ok(AILocal.get_chat_messages(
                conversation_id, self._parse_limit(limit), user, first_id))
        except Exception as e:
            log.error(f'[CHAT] 获取会话消息失败: {e}')
            return _err(str(e))

    def get_conversations(self, user, limit=None, last_id=None) -> dict:
        """拉取某个用户的会话列表（按 updated_at 倒序）。

        Args:
            user: 必填，Dify 侧用户标识（同时决定用哪个 Dify 应用）
            limit: 可选，默认 20，会收敛到 [1, 100]
            last_id: 可选，上一页最后一条会话 id，用于往更早翻页

        Returns:
            成功 `_ok(<Dify 原始响应>)`；失败 `_err(msg)`，并把上游错误透出，
            避免前端把「请求失败」误判成「没有会话」（与 `get_messages` 的
            静默失败不同）。
        """
        name = (user or '').strip()
        if not name:
            return _err('user is required')

        cursor = (last_id or '').strip() or None
        try:
            return _ok(AILocal.get_conversations(
                name, self._parse_limit(limit), cursor))
        except Exception as e:
            log.error(f'[CHAT] 获取会话列表失败: {e}')
            return _err(str(e))

    def collect_messages(self, conversation_id, user, stop_before=None,
                         limit=EXPORT_PAGE_SIZE, max_pages=EXPORT_MAX_PAGES):
        """翻页拉全某个会话的消息，返回 `(messages, truncated)`。

        Dify 的 `/messages` 只支持游标分页（`first_id` 指向更早的一页）且不返回
        总数，只能一直翻到 `has_more` 为假。`max_pages` 是防御上限，走满即
        `truncated=True`，由调用方决定怎么处理（不要静默截断）。

        `stop_before` 是可选下界（epoch 秒）：某页最旧一条早于它时提前停止——
        接口按时间从新到旧翻页，更早的页只会更旧，继续拉是白费的。

        取数失败时抛 `RuntimeError`：`get_messages` 会把「静默失败」表现为
        `data:null`，翻页场景下必须区分它和「没有更多数据」。
        """
        messages: list = []
        seen: set = set()
        first_id = None
        truncated = True

        for _ in range(max_pages):
            result = self.get_messages(conversation_id, limit, user, first_id)
            if result.get('code') != 0:
                raise RuntimeError(result.get('msg') or '获取会话消息失败')

            page = result.get('data')
            if not isinstance(page, dict):
                raise RuntimeError('获取会话消息失败')

            items = page.get('data') or []
            if not items:
                truncated = False
                break

            for msg in items:
                msg_id = (msg or {}).get('id')
                if msg_id:
                    if msg_id in seen:
                        continue
                    seen.add(msg_id)
                messages.append(msg)

            oldest = items[0] or {}
            created_at = oldest.get('created_at')
            if stop_before is not None and created_at is not None:
                try:
                    if int(created_at) < int(stop_before):
                        truncated = False
                        break
                except (TypeError, ValueError):
                    pass

            next_first_id = oldest.get('id')
            # 游标不前进必须停，否则 has_more 恒真时会死循环
            if not page.get('has_more') or not next_first_id or next_first_id == first_id:
                truncated = False
                break
            first_id = next_first_id

        return messages, truncated

    def export_messages(self, conversation_id, user, start=None, end=None):
        """按日期范围导出会话消息，成功时直接返回可下发的 CSV 文件响应。

        参数校验、取数、过滤、CSV 生成与响应头拼装都在这里完成，
        路由层只负责把请求参数原样传进来（见 `core/api/chat_routes.py`）。

        Args:
            conversation_id: 必填，Dify 会话 id
            user: 必填，Dify 侧用户标识（同时决定用哪个 Dify 应用，并用作列名）
            start / end: 可选，`YYYY-MM-DD`；留空表示不限，按服务端本地时区

        Returns:
            成功: `flask.Response` —— `text/csv` 附件，带 BOM 与 CRLF
            失败: `_err(msg)`（dict），被 Flask 序列化成统一 JSON。
                  **返回体是文件流而非 `{code,msg,data}`**，所以调用方（前端）
                  必须靠 `Content-Type` 区分「文件」与「错误」，不能只看状态码。
        """
        target = (conversation_id or '').strip()
        name = (user or '').strip()
        if not target:
            return _err('conversation_id is required')
        if not name:
            return _err('user is required')

        try:
            start_ts, end_ts = self._parse_date_range(start, end)
        except ValueError as e:
            return _err(str(e))

        try:
            # 起始日期同时作为翻页下界：比它更早的页无需再拉
            messages, truncated = self.collect_messages(
                target, name, stop_before=start_ts)
        except Exception as e:
            log.error(f"[CHAT] 导出取数失败: {e}")
            return _err(str(e))

        if truncated:
            # 宁可报错也不要静默给一份不完整的数据
            return _err(f'会话消息超过 {MAX_EXPORT_MESSAGES} 条，请缩小时间范围后重试')

        picked = self._filter_messages(messages, start_ts, end_ts)
        if not picked:
            return _err('所选时间范围内没有数据' if (start_ts or end_ts)
                        else '当前会话没有可导出的数据')

        filename = f"AI对话-{name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        log.info(f"[CHAT] 导出会话 {target} 共 {len(picked)} 条")
        return self._csv_response(self._build_csv(picked, name), filename,
                                 len(picked))

    @staticmethod
    def _content_disposition(filename) -> str:
        """构造 `Content-Disposition`：ASCII 回退 + RFC 5987 的 UTF-8 中文名。

        部分浏览器（UC 等）无视 `<a download>` 的中文名，只能依赖响应头；
        而 `filename=` 又必须是 ASCII，所以两个都给。
        """
        ascii_fallback = ''.join(
            c if ord(c) < 128 else '_' for c in filename).strip() or 'chat.csv'
        return (f"attachment; filename=\"{ascii_fallback}\"; "
                f"filename*=UTF-8''{quote(filename, safe='')}")

    @classmethod
    def _csv_response(cls, csv_text, filename, count) -> Response:
        """把 CSV 文本包成附件响应。

        直接用 `flask.Response` 而不是 `make_response`：后者部分分支依赖应用
        上下文，这里不需要，单测里也能直接构造与断言。
        """
        resp = Response(csv_text.encode('utf-8'), content_type=EXPORT_CONTENT_TYPE)
        resp.headers['Content-Disposition'] = cls._content_disposition(filename)
        # 条数与文件名一并回传，前端不用自己推算
        resp.headers['X-Export-Count'] = str(count)
        resp.headers['Cache-Control'] = 'no-store'
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        return resp

    @staticmethod
    def _parse_date_range(start, end):
        """把起止日期解析为闭区间的 `(start_ts, end_ts)`，单位 epoch 秒，None 表示不限。

        日期格式 `YYYY-MM-DD`（沿用项目其它模块的写法）；结束日期取当天
        23:59:59，保证时间范围「两端都包含」。格式非法或开始晚于结束抛 ValueError。
        """
        def parse_one(text):
            raw = (text or '').strip()
            if not raw:
                return None
            try:
                return datetime.strptime(raw, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f'日期格式应为 YYYY-MM-DD，收到：{raw}') from None

        start_date = parse_one(start)
        end_date = parse_one(end)
        if start_date and end_date and start_date > end_date:
            raise ValueError('开始日期不能晚于结束日期')

        # 注意：本模块已 `import time`，不能再用 `datetime.time`，所以显式拼出首尾时刻
        start_ts = None
        end_ts = None
        if start_date:
            start_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        if end_date:
            end_of_day = datetime.combine(end_date, datetime.min.time()).replace(
                hour=23, minute=59, second=59)
            end_ts = int(end_of_day.timestamp())
        return start_ts, end_ts

    @staticmethod
    def _format_ts(ts) -> str:
        """秒级时间戳 -> `YYYY-MM-DD HH:mm:ss`，非法值返回 `-`。"""
        if ts is None or ts == '':
            return '-'
        try:
            return datetime.fromtimestamp(int(ts)).strftime(EXPORT_TIME_FMT)
        except (TypeError, ValueError, OSError, OverflowError):
            return '-'

    @classmethod
    def _filter_messages(cls, messages, start_ts=None, end_ts=None) -> list:
        """按时间范围过滤并按时间从旧到新排序。

        没有 `created_at` 或时间戳非法的消息直接丢弃——导出的时间列填 `-`
        反而会让人误以为这份数据是完整的。
        """
        picked = []
        for msg in messages or []:
            if not isinstance(msg, dict):
                continue
            try:
                ts = int(msg.get('created_at'))
            except (TypeError, ValueError):
                continue
            if start_ts is not None and ts < start_ts:
                continue
            if end_ts is not None and ts > end_ts:
                continue
            picked.append((ts, msg))

        picked.sort(key=lambda item: item[0])
        return [msg for _, msg in picked]

    @classmethod
    def _build_csv(cls, messages, user_label) -> str:
        """生成 CSV 文本：序号 / 时间 /「<谁>说的话」/ 回答。

        - 用标准库 `csv` 负责转义（含逗号、引号、换行的字段自动加引号）；
        - 行尾 CRLF、开头加 BOM，Excel 打开中文不乱码。
        """
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator='\r\n')
        writer.writerow(['序号', '时间', f'{user_label}说的话', '回答'])

        for index, msg in enumerate(messages or [], 1):
            answer = msg.get('answer') or ''
            # 与页面表格保持一致：生成失败时该列显示失败原因，否则导出会丢信息
            if not answer and msg.get('error'):
                answer = f"失败：{msg['error']}"
            writer.writerow([
                index,
                cls._format_ts(msg.get('created_at')),
                msg.get('query') or '',
                answer,
            ])

        return '\ufeff' + buf.getvalue()

    # ---------------- Socket 事件 ----------------

    def handle_text(self, sid, data):
        try:
            chat_type = data.get('chatType', '')
            content = data.get('content', '')
            if chat_type == 'chat_room':
                room_id = data.get('roomId', '')
                user_id = data.get('userId', '')
                msg_data = {
                    'user_id': user_id,
                    'content': content,
                    'type': 'text',
                    'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'chat_type': chat_type,
                }
                rds_mgr.rpush("chat:" + room_id, json.dumps(msg_data, ensure_ascii=False))
                for client in self.clients.values():
                    if client.sid != sid:
                        log.info(f"[CHAT] Emitting [msgChat] to client {client.sid} msg {content}")
                        self.socketio.emit('msgChat', msg_data, room=client.sid)
                self.socketio.emit('endChat', {}, room=sid)

            else:
                client: ClientContext = self.clients.get(sid)
                rid = data.get('clientRequestId') or ''
                action = client.note_text_request(rid)
                if action == 'ignore':
                    return
                if not client.try_begin_ai(rid):
                    return
                client.ai.stream_msg(content, client_request_id=rid)
        except Exception as e:
            log.error(f"[CHAT] Error handling text for client {sid}: {e}")

    def handle_audio(self, sid, sample_rate, audio_bytes, room_id):
        '''
            处理音频数据
        '''
        client: ClientContext = self.clients.get(sid)
        if not client:
            log.warning(f"[CHAT] Client {sid} not found")
            return
        try:
            client.asr.process_audio(sample_rate, audio_bytes, sid)
        except Exception as e:
            log.error(f"[CHAT] Error emitting result to client {sid}: {e}")

    def _register_events(self):
        @self.socketio.on('handshake')
        def handle_handshake(data):
            if data['key'] != '123456':
                self.socketio.disconnect(request.sid)
                return {'status': 'rejected'}
            ctx = self.add_client(request.sid)
            ctx.ai.aiConversationId = data.get('aiConversationId', '')
            ctx.ai.user = data.get('user', 'user')
            ctx.autoTTS = data.get('ttsAuto', False)
            ctx.tts.vol = data.get('ttsVol', 50)
            ctx.tts.speed = data.get('ttsSpeed', 1.0)
            if data.get('ttsRole'):
                ctx.tts.role = data['ttsRole']
            log.info(
                f'[CHAT] Client {request.sid} connected. Total clients: {len(self.clients)}, {json.dumps(data, ensure_ascii=False)}'
            )

            self.socketio.emit('handshakeResponse', {'message': 'Handshake successful'}, room=request.sid)
            return {'message': 'Handshake successful', 'status': 'ok'}

        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            self.remove_client(client_id)
            log.info(f'[CHAT] Client {client_id} disconnected. Total clients: {len(self.clients)}')

        @self.socketio.on(EVENT_MESSAGE)
        def handle_message(msg):
            data = json.loads(msg)
            client_id = request.sid
            data_type = data['type']
            chat_type = data.get('chatType', '')
            content = data.get('content', '')
            room_id = data.get('roomId', '')

            if client_id not in self.clients:
                return
            ctx = self.clients[client_id]
            if data_type == 'text':
                log.info(f'[CHAT] Received {client_id}: [{data_type}-{chat_type}],{room_id}  {content}')
                self.handle_text(client_id, data)
            elif data_type == 'audio':
                rid = data.get('clientRequestId') or ''
                audio_action = ctx.note_audio_request(rid)
                if audio_action == 'ignore':
                    return
                if rid and audio_action == 'new':
                    ctx.asr.begin_session(rid)
                    ctx.mark_request_asr(rid)
                audio_bytes = base64.b64decode(content)
                self.handle_audio(client_id, data['sample'], audio_bytes, room_id)
                cancel = data.get('cancel', False)
                if cancel:
                    if rid:
                        ctx.asr.cancel_session(rid)
                        ctx.mark_request_cancelled(rid)
                elif data['finish']:
                    ctx.asr.end_asr()
            else:
                log.warning(f'[CHAT] Unknown message type: {data_type}')

        @self.socketio.on('tts')
        def handle_tts_request(msg):
            data = json.loads(msg)
            text = data.get('content')
            role = data.get('role') or None
            id = data.get('id', '')
            speed = data.get('speed')
            tts_request_id = (data.get('ttsRequestId') or '').strip() or None
            if not text:
                self.socketio.emit('error', {'error': 'Missing text'}, room=request.sid)
                return

            client_id = request.sid
            ctx = self.clients.get(client_id)
            if not ctx:
                return

            if role:
                ctx.tts.role = role
            if speed is not None:
                try:
                    ctx.tts.speed = float(speed)
                except (TypeError, ValueError):
                    pass

            ctx._tts_emit_request_id = tts_request_id
            voice = role or ctx.tts.role
            cached_audio = tts_cache.get_complete_audio(
                id,
                text,
                voice,
                ctx.tts.speed,
            )
            if cached_audio:
                chunk_size = 3000
                for i in range(0, len(cached_audio), chunk_size):
                    ctx.on_tts_msg(cached_audio[i:i + chunk_size], 0)
                ctx.on_tts_msg(">>[TTS] Completed", 1)
            else:
                ctx.tts.abort_cache()
                ctx.tts.start_immediate_cache(id, text, voice, ctx.tts.speed)
                ctx.tts.process_msg(text, role, id)

        @self.socketio.on('ttsCancel')
        def handle_tts_cancel(msg):
            ctx = self.clients[request.sid]
            ctx._tts_emit_request_id = None
            ctx.tts.streaming_cancel()

        @self.socketio.on('queryChatRequest')
        def handle_query_chat_request(payload=None):
            client_id = request.sid
            ctx = self.clients.get(client_id)
            if not ctx:
                return
            ids: list[str] = []
            if isinstance(payload, str) and payload:
                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError:
                    parsed = {}
            elif isinstance(payload, dict):
                parsed = payload
            else:
                parsed = {}
            raw = parsed.get('clientRequestIds') or parsed.get('clientRequestId') or []
            if isinstance(raw, str) and raw:
                ids = [raw]
            elif isinstance(raw, list):
                ids = [str(x) for x in raw if x]

            items = ctx.query_request_phases(ids)
            self.socketio.emit(
                'chatRequestStatus',
                {'items': items},
                room=client_id,
            )

        @self.socketio.on('chatCancel')
        def handle_chat_cancel(payload=None):
            ctx = self.clients[request.sid]
            rid = ''
            if isinstance(payload, str) and payload:
                try:
                    rid = json.loads(payload).get('clientRequestId', '') or ''
                except json.JSONDecodeError:
                    rid = ''
            elif isinstance(payload, dict):
                rid = payload.get('clientRequestId', '') or ''
            if rid:
                ctx.cancel_asr(rid)
                ctx.mark_request_cancelled(rid)
            ctx.ai.streaming_cancel(client_request_id=rid)
            ctx.tts.streaming_cancel()
            ctx._reset_auto_tts_stream()

        @self.socketio.on('config')
        def handle_chat_config(data):
            log.info(f'[CHAT] Config: {data}')
            ctx = self.clients[request.sid]
            if 'aiConversationId' in data:
                ctx.ai.aiConversationId = data['aiConversationId']
            if 'user' in data:
                ctx.ai.user = data['user']
            if 'ttsAuto' in data:
                ctx.autoTTS = data['ttsAuto']
            if 'ttsVol' in data:
                ctx.tts.vol = data['ttsVol']
            if 'ttsSpeed' in data:
                ctx.tts.speed = data['ttsSpeed']
            if 'ttsRole' in data and data['ttsRole']:
                ctx.tts.role = data['ttsRole']


chat_mgr = ChatMgr()
