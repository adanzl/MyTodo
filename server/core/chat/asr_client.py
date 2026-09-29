"""ASR WebSocket 客户端封装。

该模块负责将前端上传的音频（PCM bytes）分片后通过 WebSocket 推送至 ASR 服务端，
并将识别结果通过回调返回给上层（`core/chat/chat_mgr.py`）。

关注点：
- 连接生命周期管理（open/close）；
- 分片发送与缓冲；
- 将服务端识别结果聚合并回调。
"""

import json
import threading
import time
from dataclasses import dataclass

import websocket

from core.config import app_logger

log = app_logger

# ASR_SERVER = "ws://127.0.0.1:9095"
ASR_SERVER = "ws://192.168.50.172:9096"
ASR_MODE = "offline"
ASR_CHUNK_SIZE = [5, 10, 5]  # 采样块的大小 [5,10,5]=600ms, [8,8,4]=480ms
ASR_CHUNK_INTERVAL = 10  # 音频块处理的间隔时间
ASR_MX_WORDS = 10000
ASR_WAV = "h5"


@dataclass
class _AsrSession:
    request_id: str
    ws_generation: int
    cancelled: bool = False


class AsrClient:
    """ASR WebSocket 客户端。"""

    def __init__(self, on_result=None, on_err=None):
        """创建客户端。

        Args:
            on_result: 识别结果回调 `on_result(text, client_request_id)`。
            on_err: 错误回调 `on_err(err)`。
        """
        self.is_running = False
        self.sample_rate = -1
        self.package_size = -1
        self.buffer = bytearray()
        self.ws = None
        self.text_all = ""
        self.text_print = ""
        self.text_print_2pass_online = ""
        self.text_print_2pass_offline = ""
        self.on_result = on_result or (lambda text, rid="": None)
        self.on_err = on_err or (lambda text: None)
        self._session: _AsrSession | None = None
        self._sessions_by_generation: dict[int, _AsrSession] = {}
        self._ws_generation = 0
        self._next_session_request_id = ""
        self.sid = ""

    def _find_session(self, request_id: str) -> _AsrSession | None:
        if not request_id:
            return None
        if self._session and self._session.request_id == request_id:
            return self._session
        for session in self._sessions_by_generation.values():
            if session.request_id == request_id:
                return session
        return None

    def begin_session(self, request_id: str) -> None:
        if not request_id:
            return
        cur = self._session
        if cur and cur.request_id == request_id and not cur.cancelled:
            return
        if cur and cur.request_id != request_id:
            log.info(f">>[ASR] retire session {cur.request_id} for new {request_id}")
            cur.cancelled = True
            self._teardown_connection()
        self._next_session_request_id = request_id

    def cancel_session(self, request_id: str) -> None:
        if not request_id:
            return
        target = self._find_session(request_id)
        if not target:
            return
        target.cancelled = True
        if self._session is target and self.ws is not None:
            self._teardown_connection()

    def cancel_current_session(self) -> None:
        if self._session:
            self.cancel_session(self._session.request_id)

    def _teardown_connection(self) -> None:
        self.close()
        self.is_running = False
        self.ws = None
        self.buffer = bytearray()

    def start_asr(self, ws):
        chunk_size = 60 * ASR_CHUNK_SIZE[1] / ASR_CHUNK_INTERVAL
        self.package_size = int(self.sample_rate / 1000 * chunk_size)
        message = json.dumps({
            "mode": ASR_MODE,
            "chunk_size": ASR_CHUNK_SIZE,
            "chunk_interval": ASR_CHUNK_INTERVAL,
            "audio_fs": self.sample_rate,
            "wav_name": ASR_WAV,
            "is_speaking": False,
        })
        log.info(f">>[ASR] start {message}")
        ws.send(message)
        self.text_print = ""
        self.text_all = ""
        self.text_print_2pass_online = ""
        self.text_print_2pass_offline = ""

    def end_asr(self):
        if self.ws is None:
            log.info(">>[ASR] End (ws is None)")
            return
        if len(self.buffer):
            s_data = self.buffer
            self.buffer = bytearray()
            self.ws.send_bytes(s_data)
        message = json.dumps({"is_speaking": False})
        self.ws.send(message)
        log.info(">>[ASR] End")

    def close(self):
        if self.ws:
            self.ws.close()

    def _make_on_message(self, ws_generation: int):
        def on_message(ws, msg):
            if ws_generation != self._ws_generation:
                log.info(">>[ASR] ignore stale ws message")
                return
            session = self._sessions_by_generation.get(ws_generation)
            if session is None or session.cancelled or session.ws_generation != ws_generation:
                log.info(">>[ASR] ignore result for cancelled or stale session")
                return
            log.info(f">>[ASR] handle asr msg {msg}")
            try:
                meg = json.loads(msg)
                text = meg["text"]
                timestamp = ""
                if "timestamp" in meg:
                    timestamp = meg["timestamp"]
                if "mode" not in meg:
                    log.warning(">>[ASR] mode not in meg")
                    return
                if meg["mode"] == "online":
                    self.text_print += "{}".format(text)
                    self.text_print = self.text_print[-ASR_MX_WORDS:]
                elif meg["mode"] == "offline":
                    self.text_print += "{}".format(text)
                else:
                    if meg["mode"] == "2pass-online":
                        self.text_print_2pass_online += "{}".format(text)
                        self.text_print = self.text_print_2pass_offline + self.text_print_2pass_online
                    else:
                        self.text_print_2pass_online = ""
                        self.text_print = self.text_print_2pass_offline + "{}".format(text)
                        self.text_print_2pass_offline += "{}".format(text)
                    self.text_print = self.text_print[-ASR_MX_WORDS:]
                msg_out = {
                    "type": "recognition",
                    "content": self.text_print,
                    "timestamp": timestamp,
                }
                log.info(f">>[ASR] Receive result: {msg_out} , {self.sid}")
                self.text_all = self.text_print
                self.text_print = ""
                rid = session.request_id
                self.on_result(self.text_all, rid)
            except Exception as e:
                self.on_err(e)
                log.error("[ASR] Exception: %s", e)

        return on_message

    def _make_on_open(self, ws_generation: int):
        def on_open(ws):
            if ws_generation != self._ws_generation:
                log.info(">>[ASR] ignore stale ws open")
                return
            log.info(">>[ASR] open")
            try:
                self.start_asr(ws)
                self.is_running = True
            except Exception as e:
                log.error(f">>[ASR] Error : {e}")
                self.on_err(e)

        return on_open

    def _make_on_error(self, ws_generation: int):
        def on_error(ws, error):
            if ws_generation != self._ws_generation:
                log.info(">>[ASR] ignore stale ws error")
                return
            log.error(f">>[ASR] error {error}")

        return on_error

    def _make_on_close(self, ws_generation: int):
        def on_close(ws, close_status_code, close_msg):
            if ws_generation != self._ws_generation:
                log.info(">>[ASR] ignore stale ws close")
                return
            log.info(f">>[ASR] Close {close_status_code} {close_msg}")
            self.buffer = bytearray()
            self.ws = None
            self.is_running = False

        return on_close

    def connect(self, sid, sample_rate):
        self.sid = sid
        self.sample_rate = sample_rate
        self._ws_generation += 1
        ws_generation = self._ws_generation
        rid = self._next_session_request_id
        if not rid and self._session and not self._session.cancelled:
            rid = self._session.request_id
        if not rid:
            rid = ""
        self._next_session_request_id = ""
        session = _AsrSession(request_id=rid, ws_generation=ws_generation)
        self._session = session
        self._sessions_by_generation[ws_generation] = session

        self.ws = websocket.WebSocketApp(
            ASR_SERVER,
            on_open=self._make_on_open(ws_generation),
            on_message=self._make_on_message(ws_generation),
            on_error=self._make_on_error(ws_generation),
            on_close=self._make_on_close(ws_generation),
        )

        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()

    def process_audio(self, sample_rate, audio_data, sid):
        self.buffer.extend(audio_data)
        if self.ws is None:
            self.connect(sid, sample_rate)
        if self.is_running:
            while self.ws and len(self.buffer) >= self.package_size:
                s_data = self.buffer[:self.package_size]
                self.buffer = self.buffer[self.package_size:]
                self.ws.send_bytes(s_data)
                time.sleep(0)
