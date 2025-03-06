import logging
import threading
import time
import websocket
import json

from app import socketio

log = logging.getLogger(__name__)

# ASR_SERVER = "ws://127.0.0.1:9095"
ASR_SERVER = "ws://192.168.50.171:9096"
# ASR_SERVER = "wss://www.funasr.com:10095/"
ASR_MODE = "offline"
ASR_CHUNK_SIZE = [5, 10, 5]  # 采样块的大小 [5,10,5]=600ms, [8,8,4]=480ms
ASR_CHUNK_INTERVAL = 10  # 音频块处理的间隔时间
ASR_MX_WORDS = 10000
ASR_WAV = "demo"


class AsrClient:

    def __init__(self):
        self.is_running = False
        self.sample_rate = -1
        self.package_size = -1
        self.buffer = bytearray()
        self.text_print = ""
        self.text_print_2pass_online = ""
        self.text_print_2pass_offline = ""

    def handle_message(self, msg):
        log.info(f"====> handle asr msg {msg}")
        try:
            meg = json.loads(msg)
            text = meg["text"]
            timestamp = ""
            offline_msg_done = meg.get("is_final", False)
            if "timestamp" in meg:
                timestamp = meg["timestamp"]
            if "mode" not in meg:
                return
            if meg["mode"] == "online":
                self.text_print += "{}".format(text)
                self.text_print = self.text_print[-ASR_MX_WORDS:]
                # self.on_message(self.text_print)
            elif meg["mode"] == "offline":
                if timestamp != "":
                    self.text_print += "{} timestamp: {}".format(text, timestamp)
                else:
                    self.text_print += "{}".format(text)
                # self.on_message(self.text_print)
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
                # self.on_message(self.text_print)
            # send_one(ws)
        except Exception as e:
            log.error("Exception:", e)

    def send_message(self, message):
        if self.is_running and self.ws:
            self.ws.send(message)

    def send_data(self, ws, bytes_msg):
        log.info(f"=> asr send_data {len(bytes_msg)} [{self.package_size}]")
        # with open("asr.pcm", "wb") as f:
        #     f.write(bytes_msg)
        self.buffer.extend(bytes_msg)
        while len(self.buffer) >= self.package_size:
            s_data = self.buffer[:self.package_size]
            self.buffer = self.buffer[self.package_size:]
            ws.send(s_data, opcode=websocket.ABNF.OPCODE_BINARY)
            time.sleep(0.001)

    def start_asr(self, ws, sample_rate):
        self.sample_rate = sample_rate
        chunk_size = 60 * ASR_CHUNK_SIZE[1] / ASR_CHUNK_INTERVAL
        self.package_size = int(sample_rate / 1000 * chunk_size)
        message = json.dumps({
            "mode": ASR_MODE,
            "chunk_size": ASR_CHUNK_SIZE,
            "chunk_interval": ASR_CHUNK_INTERVAL,
            "audio_fs": sample_rate,
            "wav_name": ASR_WAV,
            "wav_format": "pcm",
            "is_speaking": True,
        })
        log.info(f"=> start asr {message}")
        ws.send(message)
        self.text_print = ""
        self.text_print_2pass_online = ""
        self.text_print_2pass_offline = ""

    def end_asr(self, ws):
        if len(self.buffer):
            s_data = self.buffer
            self.buffer = bytearray()
            ws.send(s_data, opcode=websocket.ABNF.OPCODE_BINARY)
        message = json.dumps({"is_speaking": False})
        ws.send(message)
        log.info("=> end asr")

    def close(self):
        if self.is_running and self.ws:
            self.ws.close()

    def on_open(self, ws):
        log.info("=> asr open")
        try:
            self.start_asr(ws, self.sample_rate)
            self.send_data(ws, self.audio_data)
            self.end_asr(ws)
            self.is_running = False
        except Exception as e:
            log.error(f"Error : {e}")
            msg = {"type": "error", "content": json.dumps({"error": str(e)})}
            socketio.emit('message', msg, room=self.sid)

    def on_message(self, ws, msg):
        log.info(f"====> handle asr msg {msg}")
        try:
            meg = json.loads(msg)
            text = meg["text"]
            timestamp = ""
            offline_msg_done = meg.get("is_final", False)
            if "timestamp" in meg:
                timestamp = meg["timestamp"]
            if "mode" not in meg:
                log.warning("mode not in meg")
                return
            if meg["mode"] == "online":
                self.text_print += "{}".format(text)
                self.text_print = self.text_print[-ASR_MX_WORDS:]
                # self.on_message(self.text_print)
            elif meg["mode"] == "offline":
                if timestamp != "":
                    self.text_print += "{} timestamp: {}".format(text, timestamp)
                else:
                    self.text_print += "{}".format(text)
                # self.on_message(self.text_print)
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
                # self.on_message(self.text_print)
            msg = {"type": "recognition", "content": self.text_print}
            log.info(f"[CHAT] Emit result: {msg} , {self.sid}")
            socketio.emit('message', msg, room=self.sid)
            # send_one(ws)
            if offline_msg_done:
                self.close()
        except Exception as e:
            msg = {"type": "error", "content": json.dumps({"error": str(e)})}
            socketio.emit('message', msg, room=self.sid)
            log.error("Exception:", e)

    def on_error(self, ws, error):
        log.error(f"=> asr error {error}")

    def on_close(self, ws, close_status_code, close_msg):
        log.info(f"=> asr close {close_status_code} {close_msg}")

    def process_audio(self, sample_rate, audio_data, sid):

        self.sid = sid
        self.audio_data = audio_data
        self.sample_rate = sample_rate

        ws = websocket.WebSocketApp(
            ASR_SERVER,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        # 启动 WebSocket 连接
        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()
