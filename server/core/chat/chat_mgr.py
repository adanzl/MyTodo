"""Chat 管理器。

该模块负责 WebSocket（Flask-SocketIO）侧的会话管理与事件分发：
- 为每个 Socket 客户端维护 `ClientContext`（AI/ASR/TTS 管线）；
- 处理文本与音频消息，转发/聚合结果并推送给前端；
- chat_room 模式下将消息写入 Redis 列表用于房间广播。
"""

import base64
import time

import core.db.rds_mgr as rds_mgr
from core.ai.ai_local import AILocal
from core.chat.asr_client import AsrClient
from core.chat import chat_request_store
from core.config import app_logger
from core.chat import tts_cache
from core.chat.tts_phrase_buffer import TtsPhraseBuffer
from core.tts.tts_client import TTSClient
from flask import json, request

log = app_logger

MSG_TYPE_ERROR = "error"

EVENT_MESSAGE = "message"


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
        self.asr = AsrClient(self.on_asr_result, self.on_asr_err)  # 语音识别
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
