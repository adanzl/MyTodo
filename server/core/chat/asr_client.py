import logging
import websocket
import json
import threading
import time

log = logging.getLogger(__name__)

ASR_SERVER = "ws://127.0.0.1:9095"
ASR_MODE = "online"
ASR_CHUNK_SIZE = [5, 10, 5]  # 采样块的大小 [5,10,5]=600ms, [8,8,4]=480ms
ASR_CHUNK_INTERVAL = 10  # 音频块处理的间隔时间
ASR_MX_WORDS = 10000
ASR_WAV = "demo"


class AsrClient:

    def __init__(self, on_message):
        self.ws = None
        self.is_running = False
        self.sample_rate = -1
        self.package_size = -1
        self.buffer = bytearray()
        self.text_print = ""
        self.text_print_2pass_online = ""
        self.text_print_2pass_offline = ""
        self.on_message = on_message

    def handle_message(self, msg):
        log.info(f"handle msg {msg}")
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
                # print("\rpid" + str(id) + ": " + text_print)
                self.on_message(self.text_print)
            else:
                if meg["mode"] == "2pass-online":
                    self.text_print_2pass_online += "{}".format(text)
                    self.text_print = self.text_print_2pass_offline + self.text_print_2pass_online
                else:
                    self.text_print_2pass_online = ""
                    self.text_print = self.text_print_2pass_offline + "{}".format(text)
                    self.text_print_2pass_offline += "{}".format(text)
                self.text_print = self.text_print[-ASR_MX_WORDS:]
                # print("\rpid" + str(id) + ": " + text_print)
                self.on_message(self.text_print)
            # send_one(ws)
        except Exception as e:
            log.error("Exception:", e)


    def handle_open(self):
        log.info(f"====> ws opened")

    def handle_error(self, error):
        # 当发生错误时，打印错误信息
        log.info(f"====> ws 发生错误: {error}")

    def handle_close(self, close_status_code, close_msg):
        # 当WebSocket连接关闭时，打印关闭信息
        log.info(f"====> ws 连接已关闭 {close_status_code}: {close_msg}")
        self.is_running = False

    def connect(self):
        self.ws = websocket.WebSocketApp(
            ASR_SERVER,
            on_open=self.handle_open,
            on_message=self.handle_message,
            on_error=self.handle_error,
            on_close=self.handle_close,
        )
        self.is_running = True
        # 使用线程来运行 WebSocket 连接，避免阻塞主线程
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.start()

    def send_message(self, message):
        if self.is_running and self.ws:
            self.ws.send(message)

    def send_data(self, bytes_msg):
        if self.is_running and self.ws:
            self.buffer.extend(bytes_msg)
            while len(self.buffer) >= self.package_size:
                s_data = self.buffer[:self.package_size]
                self.buffer = self.buffer[self.package_size:]
                self.ws.send(s_data, opcode=websocket.ABNF.OPCODE_BINARY)

    def start_asr(self, sample_rate):
        self.sample_rate = sample_rate
        chunk_size = 60 * ASR_CHUNK_SIZE[1] / ASR_CHUNK_INTERVAL
        self.package_size = int(sample_rate / 1000 * chunk_size)
        message = json.dumps({
            "mode": ASR_MODE,
            "chunk_size": ASR_CHUNK_SIZE,
            "chunk_interval": ASR_CHUNK_INTERVAL,
            "audio_fs": self.sample_rate,
            "wav_name": ASR_WAV,
            "wav_format": "pcm",
            "is_speaking": True,
        })
        self.ws.send(message)
        self.text_print = ""
        self.text_print_2pass_online = ""
        self.text_print_2pass_offline = ""

    def end_asr(self):
        if len(self.buffer):
            s_data = self.buffer
            self.buffer = bytearray()
            self.ws.send(s_data, opcode=websocket.ABNF.OPCODE_BINARY)
        message = json.dumps({"is_speaking": False})
        self.ws.send(message)


    def close(self):
        if self.is_running and self.ws:
            self.ws.close()
