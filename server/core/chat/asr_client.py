import json
import threading
import time

import websocket
from core.log_config import root_logger

log = root_logger()

# ASR_SERVER = "ws://127.0.0.1:9095"
ASR_SERVER = "ws://192.168.50.171:9096"
ASR_MODE = "offline"
ASR_CHUNK_SIZE = [5, 10, 5]  # 采样块的大小 [5,10,5]=600ms, [8,8,4]=480ms
ASR_CHUNK_INTERVAL = 10  # 音频块处理的间隔时间
ASR_MX_WORDS = 10000
ASR_WAV = "h5"


class AsrClient:

    def __init__(self, on_result=None, on_err=None):
        self.is_running = False
        self.sample_rate = -1
        self.package_size = -1
        self.buffer = bytearray()
        self.ws = None
        self.text_all = ""
        self.text_print = ""
        self.text_print_2pass_online = ""
        self.text_print_2pass_offline = ""
        self.on_result = on_result or (lambda text: None)
        self.on_err = on_err or (lambda text: None)
        self.cancel = False

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

    def on_open(self, ws):
        log.info(">>[ASR] open")
        try:
            self.start_asr(ws)
            self.is_running = True
        except Exception as e:
            log.error(f">>[ASR] Error : {e}")
            self.on_err(e)

    def on_message(self, ws, msg):
        log.info(f">>[ASR] handle asr msg {msg}")
        try:
            meg = json.loads(msg)
            text = meg["text"]
            timestamp = ""
            offline_msg_done = meg.get("is_final", False)
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
                offline_msg_done = True
            else:
                if meg["mode"] == "2pass-online":
                    self.text_print_2pass_online += "{}".format(text)
                    self.text_print = self.text_print_2pass_offline + self.text_print_2pass_online
                else:
                    self.text_print_2pass_online = ""
                    self.text_print = self.text_print_2pass_offline + "{}".format(text)
                    self.text_print_2pass_offline += "{}".format(text)
                self.text_print = self.text_print[-ASR_MX_WORDS:]
            msg = {"type": "recognition", "content": self.text_print, "timestamp": timestamp}
            log.info(f">>[ASR] Receive result: {msg} , {self.sid}")
            self.text_all = self.text_print
            self.text_print = ""
            # if offline_msg_done:
            #     self.close()
            if not self.cancel:
                self.on_result(self.text_all)
            self.cancel = False
        except Exception as e:
            self.on_err(e)
            log.error("Exception:", e)

    def on_error(self, ws, error):
        log.error(f">>[ASR] error {error}")

    def on_close(self, ws, close_status_code, close_msg):
        log.info(f">>[ASR] Close {close_status_code} {close_msg}")
        self.buffer = bytearray()
        self.ws = None
        self.is_running = False

    def connect(self, sid, sample_rate):
        self.sid = sid
        self.sample_rate = sample_rate

        self.ws = websocket.WebSocketApp(
            ASR_SERVER,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        # 启动 WebSocket 连接
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()

    def process_audio(self, sample_rate, audio_data, sid):
        self.buffer.extend(audio_data)
        if self.ws is None:
            self.connect(sid, sample_rate)
            # socketio.emit("message", {"type": "recognition", "content": "OK"}, room=sid)
        if self.is_running:
            while len(self.buffer) >= self.package_size:
                s_data = self.buffer[:self.package_size]
                self.buffer = self.buffer[self.package_size:]
                self.ws.send_bytes(s_data)
                time.sleep(0)
