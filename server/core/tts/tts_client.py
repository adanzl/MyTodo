import traceback
import os

import dashscope
from dashscope.audio.tts_v2 import *

from core.tools.ws_owner_send import install as install_ws_owner_send
from core.tts.tts_worker import SdkWorker

# SDK 内部用 websocket-client：连接建立在它自己起的 run_forever 线程里，
# 而文本帧从我们的工作线程发送 —— 必须让发送发生在连接所属线程上，
# 否则跨线程使用 gevent socket 会抛 Cannot switch to a different thread
install_ws_owner_send()

try:
    from core.config import app_logger, config
    import core.db.rds_mgr as rds_mgr

    log = app_logger
    ALI_KEY = config.ALI_KEY
    FASTAPI_URL = config.ZERO_TTS_FASTAPI_URL
except ImportError:
    from dotenv import load_dotenv
    load_dotenv()
    import logging

    log = logging.getLogger()
    rds_mgr = None
    ALI_KEY = os.getenv('ALI_KEY', '')
    FASTAPI_URL = os.getenv("ZERO_TTS_FASTAPI_URL",
                            "http://192.168.50.172:9099/inference_zero_shot")

ROLE_MAP = {
    # cSpell: disable-next-line
    "太乙": "/mnt/data/CosyVoice/pretrained_models/prompt/zh_taiyi_prompt.wav",
    "default": "/mnt/data/CosyVoice/pretrained_models/prompt/zero_shot_prompt.wav",
    "中文女": "/mnt/data/CosyVoice/pretrained_models/prompt/zh_woman_prompt.wav",
}

# cSpell: disable
DEFAULT_ROLE = "longwan_v3"
DEFAULT_MODEL = "cosyvoice-v3-flash"
MODEL_MAP = {
    "longwan_v2": "cosyvoice-v2",
    'longcheng_v2': 'cosyvoice-v2',
    'longhua_v2': 'cosyvoice-v2',
    'longshu_v2': 'cosyvoice-v2',
    'loongbella_v2': 'cosyvoice-v2',
    'longxiaochun_v2': 'cosyvoice-v2',
    'longxiaoxia_v2': 'cosyvoice-v2',
    'longwan_v3': 'cosyvoice-v3-flash',
}
# cSpell: enable


class TTSClient(ResultCallback):

    def __init__(self, on_msg=None, on_err=None):
        self.on_msg = on_msg or (lambda x, y: None)
        self.on_err = on_err or (lambda x: None)
        dashscope.api_key = ALI_KEY
        self.synthesizer = None
        # 每个客户端一个 SDK 线程：既保证连接的线程归属，又避免不同会话
        # 互相排队（详见 tts_worker.py）
        self._sdk = SdkWorker(f'tts-sdk-{id(self):x}')
        self.role = DEFAULT_ROLE
        self.speed = 1.0
        self.vol = 50
        self.id = ''
        self._errored = False
        self._cache_session = None
        self._deferred_cache_msg_id = ''
        self._deferred_cache_audio = bytearray()
        self._deferred_cache_text = ''
        self._deferred_cache_role: str | None = None
        self._deferred_cache_speed: float | None = None

    def _model_for_role(self, role: str) -> str:
        return MODEL_MAP.get(role, DEFAULT_MODEL)

    def start_immediate_cache(
        self,
        msg_id: str,
        text: str,
        role: str | None = None,
        speed: float | None = None,
    ) -> None:
        from core.chat import tts_cache

        role = role or self.role
        speed = self.speed if speed is None else speed
        self._deferred_cache_msg_id = ''
        self._deferred_cache_audio = bytearray()
        self._deferred_cache_text = ''
        self._deferred_cache_role = None
        self._deferred_cache_speed = None
        self._cache_session = tts_cache.begin_session(
            msg_id,
            text,
            role,
            speed,
            self._model_for_role(role),
        )

    def start_deferred_cache(self, msg_id: str) -> None:
        self._cache_session = None
        self._deferred_cache_msg_id = msg_id or ''
        self._deferred_cache_audio = bytearray()
        self._deferred_cache_text = ''
        self._deferred_cache_role = None
        self._deferred_cache_speed = None

    def prepare_deferred_cache(
        self,
        text: str,
        role: str | None = None,
        speed: float | None = None,
    ) -> None:
        """记录流式 TTS 的最终文本；等 SDK on_complete 后再把完整音频落缓存。"""
        if not self._deferred_cache_msg_id:
            return
        self._deferred_cache_text = text or ''
        self._deferred_cache_role = role or self.role
        self._deferred_cache_speed = self.speed if speed is None else speed

    def _commit_deferred_cache(self) -> None:
        from core.chat import tts_cache

        msg_id = self._deferred_cache_msg_id
        text = self._deferred_cache_text
        audio = bytes(self._deferred_cache_audio)
        role = self._deferred_cache_role or self.role
        speed = self.speed if self._deferred_cache_speed is None else self._deferred_cache_speed
        if msg_id and text and audio and rds_mgr is not None:
            session = tts_cache.begin_session(
                msg_id,
                text,
                role,
                speed,
                self._model_for_role(role),
            )
            rds_mgr.append_value(session["audio_key"], audio)
            tts_cache.finalize_session(session)
        self._deferred_cache_msg_id = ''
        self._deferred_cache_audio = bytearray()
        self._deferred_cache_text = ''
        self._deferred_cache_role = None
        self._deferred_cache_speed = None

    def abort_cache(self) -> None:
        from core.chat import tts_cache

        if self._cache_session:
            tts_cache.abort_session(self._cache_session)
        self._cache_session = None
        self._deferred_cache_msg_id = ''
        self._deferred_cache_audio = bytearray()
        self._deferred_cache_text = ''
        self._deferred_cache_role = None
        self._deferred_cache_speed = None

    def finalize_cache(self) -> None:
        from core.chat import tts_cache

        if self._cache_session:
            tts_cache.finalize_session(self._cache_session)
        self._cache_session = None

    def _ensure_synthesizer(self, role: str):
        """创建/复用 synthesizer。**必须在 SDK 线程上调用**，连接才归属该线程。"""
        if self.synthesizer is None:
            self._errored = False
            self.synthesizer = SpeechSynthesizer(
                model=MODEL_MAP.get(role, DEFAULT_MODEL),
                voice=role,
                volume=self.vol,
                speech_rate=self.speed,
                callback=self,
            )
        return self.synthesizer

    def _submit_sdk(self, action, *, label: str, wait: bool = False, timeout=None):
        """把 SDK 操作投递到专用线程，异常就地报告。

        不能在 hub 上直接调用 SDK：`streaming_complete()` 会等最长 10 分钟、
        `call()` 等到整段合成结束，而 `threading.Event` 未被 patch，会把整个
        OS 线程占住。
        """
        def guarded():
            try:
                return action()
            except Exception as e:  # noqa: BLE001 - 与原先的内联处理保持一致
                # 用 exc_info 记录真实异常栈；在这里 print_stack 只会打出
                # SDK 线程自身的栈，没有诊断价值。
                log.error(f">>[TTS] {label} 失败: {e}", exc_info=True)
                self.on_err(e)
                return None

        return self._sdk.submit(guarded, wait=wait, timeout=timeout)

    def streaming_cancel(self):
        log.info(">>[TTS] cancel streaming")
        self.abort_cache()
        # 丢弃尚未执行的文本片段：取消之后不该再把它们发出去。
        # 必须先于取消动作执行，否则队列里残留的片段会在取消之后被发送。
        dropped = self._sdk.discard_pending()
        if dropped:
            log.info(f">>[TTS] 取消时丢弃了 {dropped} 个待执行动作")
        self._submit_sdk(self._do_cancel, label='streaming_cancel')

    def _do_cancel(self):
        """在 SDK 线程上执行取消。

        注意 SDK 的 socket 由它自己起的 `run_forever` 线程创建，`ws.send()`
        只应在那个线程发起；这里不额外起线程（详见模块顶部说明）。
        """
        synth = self.synthesizer
        self.synthesizer = None
        if synth is None:
            return
        if not getattr(synth, '_is_started', False):
            # 会话没真正开始（例如启动失败），SDK 会抛「尚未启动」，无需调用
            return
        synth.streaming_cancel()

    def process_msg(self, text: str, role: str = None, id=None):
        """ 一次性合成音频，文本需要一次性传入

        注意：SDK 的 `call()` 会等到整段合成结束，因此走专用线程执行，
        调用方（hub）只投递不等待；音频仍通过 on_data 回调返回。

        Args:
            text: 待合成的文本内容。
            role: 发音人/音色。

        Returns:
            None
        """
        if role is None:
            role = self.role
        else:
            self.role = role
        if id:
            self.id = id
        # call() 内部也是基于流式会话实现；保留实例才能让 ttsCancel 真正中止生成。
        self._submit_sdk(
            lambda: self._ensure_synthesizer(role).call(text),
            label='process_msg',
        )

    def stream_msg(self, text: str, role: str = None, id=None):
        """ 流式合成音频，文本需要流式传入

        按顺序投递到 SDK 线程执行，保持原有的调用次序（文本片段的先后有意义）。

        Args:
            text: 待合成的文本内容。
            role: 发音人/音色。
            id: 任务 ID。

        Returns:
            None
        """
        if role is None:
            role = self.role
        else:
            self.role = role
        if id:
            self.id = id
        self._submit_sdk(
            lambda: self._ensure_synthesizer(role).streaming_call(text),
            label='streaming_call',
        )

    def stream_complete(self):
        """结束流式合成。

        用 SDK 自带的 `async_streaming_complete()`：它把结束指令发出去就立刻返回，
        由 SDK 自己的线程等待完成并关闭。

        不能调同步的 `streaming_complete()`——它会等最长 10 分钟
        （`complete_timeout_millis` 默认 600000）。虽然本类已把 SDK 调用放到专用
        线程，不会阻塞 hub，但那会**占住串行队列**：期间排队的
        `streaming_cancel()` 无法执行，而取消恰恰是要用来打断这等待的。

        完成与否通过 `on_complete` 回调得知。
        """
        def action():
            synth = self.synthesizer
            # 从未发送过文本时不应创建实例、也不该向 SDK 发结束指令
            # （SDK 会抛「speech synthesizer has not been started」）。
            # 这个判断必须放在**动作内部**：放在外面会在投递时就把它读成 None，
            # 而那时前面的 stream_msg 可能还没执行、实例尚未创建。
            if synth is None:
                return
            if not getattr(synth, '_is_started', False):
                # 会话存在但未真正启动（例如启动失败），同样无需发送
                self.synthesizer = None
                return
            synth.async_streaming_complete()

        self._submit_sdk(action, label='streaming_complete')

    def on_open(self):
        log.debug(">>[TTS] on_open 回调")
        ...

    def on_complete(self):
        log.debug(">>[TTS] on_complete 回调")
        # 回调来自 SDK 的 ws 线程（或 SDK 线程），而 on_msg 最终会 socketio.emit。
        # 跨线程 emit 会用到归属 hub 的 gevent socket，必须交回 hub；
        # 用**保序**通道：完成事件必须排在所有音频分片之后。
        from core.tools.hub_dispatch import post_to_hub_ordered

        def emit_complete():
            self.finalize_cache()
            self._commit_deferred_cache()
            self.on_msg(">>[TTS] Completed", 1)

        post_to_hub_ordered(emit_complete)

    def on_error(self, message: str):
        log.error(f">>[TTS] failed, {message}")
        self.synthesizer = None
        self.abort_cache()
        # 去重必须在当前（SDK）线程就地判定：若把整个方法推迟到 hub，
        # 连续两次 on_error 都会先通过判断，导致重复上报。
        if self._errored:
            return
        self._errored = True

        # 只有 on_err（最终会 socketio.emit）需要交回 hub：
        # 跨线程 emit 会用到归属 hub 的 gevent socket。
        from core.tools.hub_dispatch import post_to_hub_ordered

        def report_error():
            try:
                self.on_err(Exception(message))
            except Exception as e:
                log.error(f">>[TTS] on_err callback failed: {e}")
                traceback.print_stack()

        post_to_hub_ordered(report_error)

    def on_close(self):
        log.debug(f">>[TTS] on_close 回调")
        self.synthesizer = None
        self._errored = False

    def on_event(self, message):
        pass

    def on_data(self, data: bytes) -> None:
        log.debug(
            f">>[TTS] on_data 回调，数据长度: {len(data) if isinstance(data, bytes) else 'N/A'}")
        if self._deferred_cache_msg_id:
            self._deferred_cache_audio.extend(data)
        elif self._cache_session is not None and rds_mgr is not None:
            try:
                from core.chat import tts_cache

                tts_cache.append_audio(self._cache_session, data)
            except Exception as e:
                log.warning(f">>[TTS] Redis append failed, ignore: {e}")

        # 音频分片最终会 socketio.emit —— 必须交回 hub 执行（见 on_complete 说明），
        # 且必须走**保序**通道，否则分片乱序会让前端播放错乱。
        from core.tools.hub_dispatch import post_to_hub_ordered

        def emit_chunk():
            try:
                self.on_msg(data, 0)
            except Exception as e:
                log.error(f">>[TTS]{e}")
                traceback.print_stack()
                try:
                    self.on_err(e)
                except Exception:  # noqa: BLE001 - on_err 本身失败时不再抛出
                    log.error('>>[TTS] on_err 回调失败', exc_info=True)

        post_to_hub_ordered(emit_chunk)


def test_tts():
    f = None

    def on_data(data, type=0):
        nonlocal f
        if type == 0:
            # type=0 表示音频数据
            if isinstance(data, bytes):
                log.info(f">>[TTS] Data: {len(data)} bytes")
                if f is None:
                    f = open("output.mp3", "wb")
                f.write(data)
            else:
                log.info(f">>[TTS] Data: {data}")
        else:
            # type=1 表示完成消息
            log.info(f">>[TTS] Message END: {data}")
            if f is not None:
                f.close()
                f = None

    def on_err(err):
        log.error(f">>[TTS] Error: {err}")

    tts = TTSClient(on_msg=on_data, on_err=on_err)
    text = '可可……你这突如其来的表白让我眼泪都快下来了！😍 当然好啊！愿意，一千个一万个愿意！和你在一起的每一天都是我最珍贵的时光。这么多年的等待和错过，终于等来了这一刻。以后的日子里，不管是去故宫划船还是公园散步，我都想牵着你的手一起走。亲爱的，这一生一世，我都是你的楠楠啦～'
    tts.process_msg(text, 'longwan_v3')


if __name__ == "__main__":
    test_tts()
