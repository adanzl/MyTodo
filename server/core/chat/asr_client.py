import logging
import asyncio
import websockets
import json

from app import socketio

log = logging.getLogger(__name__)

# ASR_SERVER = "ws://127.0.0.1:9095"
ASR_SERVER = "ws://192.168.50.171:9096"
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

    async def send_data(self, ws, bytes_msg):
        self.buffer.extend(bytes_msg)
        while len(self.buffer) >= self.package_size:
            s_data = self.buffer[:self.package_size]
            self.buffer = self.buffer[self.package_size:]
            await ws.send(s_data)
            await asyncio.sleep(0)
        log.info(f"=> asr send_data {len(bytes_msg)}")

    async def start_asr(self, ws, sample_rate):
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
        await ws.send(message)
        self.text_print = ""
        self.text_print_2pass_online = ""
        self.text_print_2pass_offline = ""

    async def end_asr(self, ws):
        if len(self.buffer):
            s_data = self.buffer
            self.buffer = bytearray()
            await ws.send(s_data)
        message = json.dumps({"is_speaking": False})
        await ws.send(message)
        log.info("=> end asr")

    def close(self):
        if self.is_running and self.ws:
            self.ws.close()

    async def receive_results(self, ws):
        while True:
            try:
                msg = await ws.recv()
                log.info(f"====> handle asr msg {msg}")
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
                if meg['is_final']:
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error receiving result: {e}")
                break
            await asyncio.sleep(0)

    async def process_audio(self, sample_rate, audio_data):
        try:
            async with websockets.connect(ASR_SERVER) as ws:
                await self.start_asr(ws, sample_rate)
                receive_task = asyncio.create_task(self.receive_results(ws))
                await self.send_data(ws, audio_data)
                await receive_task
                await self.end_asr()
            return self.text_print
        except Exception as e:
            print(f"Error processing audio: {e}")
            return None
