import logging
import traceback

import dashscope

log = logging.getLogger(__name__)
FASTAPI_URL = "http://192.168.50.171:9099/inference_zero_shot"  # FastAPI 服务器地址
from dashscope.audio.tts_v2 import *

ROLE_MAP = {
    # cSpell: disable-next-line
    "太乙": "/mnt/data/CosyVoice/pretrained_models/prompt/zh_taiyi_prompt.wav",
    "default": "/mnt/data/CosyVoice/pretrained_models/prompt/zero_shot_prompt.wav",
    "中文女": "/mnt/data/CosyVoice/pretrained_models/prompt/zh_woman_prompt.wav",
}

# cSpell: disable
DEFAULT_ROLE = "longwan_v2"
DEFAULT_MODEL = "cosyvoice-v1"
MODEL_MAP = {
    "longwan_v2": "cosyvoice-v2",
    'longcheng_v2': 'cosyvoice-v2',
    'longhua_v2': 'cosyvoice-v2',
    'longshu_v2': 'cosyvoice-v2',
    'loongbella_v2': 'cosyvoice-v2',
    'longxiaochun_v2': 'cosyvoice-v2',
    'longxiaoxia_v2': 'cosyvoice-v2',
}
# cSpell: enable


class TTSClient(ResultCallback):

    def __init__(self, on_msg=None, on_err=None):
        self.on_msg = on_msg or (lambda x, y: None)
        self.on_err = on_err or (lambda x: None)
        dashscope.api_key = "sk-b7b302bad3b3410a9e21ca2294de4a08"
        self.synthesizer = None
        self.role = DEFAULT_ROLE
        self.speed = 1.0
        self.vol = 50

    def process_msg(self, text: str, role: str = None):
        try:
            # 发起请求到 FastAPI 服务器，并处理流式响应
            # payload = {
            #     "tts_text": text,
            #     "prompt_text": "希望你以后能够做的比我还好呦。",
            # }
            # prompt_wav = ROLE_MAP.get(user, ROLE_MAP["default"])
            # files = [
            #     (
            #         "prompt_wav",
            #         ("prompt_wav", open(prompt_wav, "rb"), "application/octet-stream"),
            #     )
            # ]
            # log.info(f"[TTS REQ] {json.dumps(payload,ensure_ascii=False)}")
            # rsp = requests.request(
            #     "GET", FASTAPI_URL, data=payload, files=files, stream=True
            # )
            # log.info(f"[TTS RSP]:  {rsp.status_code}, {rsp.reason}")
            # if rsp.status_code != 200:
            #     self.on_err(Exception(f"Error: {rsp.status_code}, {rsp.text}"))
            #     return
            # # 使用 Socket.IO 的分片消息发送音频数据
            # for chunk in rsp.iter_content(chunk_size=16000):
            #     if chunk:
            #         # 使用二进制消息发送音频数据
            #         self.on_msg(chunk)
            # log.info("[TTS COMPLETE] ")
            # self.on_msg("Completed", 1)
            if role is None:
                role = self.role
            synthesizer = SpeechSynthesizer(
                model=MODEL_MAP.get(role, DEFAULT_MODEL),
                voice=role,
                volume=self.vol,
                speech_rate=self.speed,
                callback=self,
            )
            synthesizer.call(text)

        except Exception as e:
            log.error(e)
            traceback.print_stack()
            self.on_err(e)

    def stream_msg(self, text: str, role: str = None):
        try:
            if role is None:
                role = self.role
            if self.synthesizer is None:
                self.synthesizer = SpeechSynthesizer(
                    model=MODEL_MAP.get(role, DEFAULT_MODEL),
                    voice=role,
                    volume=self.vol,
                    speech_rate=self.speed,
                    callback=self,
                )
            self.synthesizer.streaming_call(text)
        except Exception as e:
            log.error(e)
            traceback.print_stack()
            self.on_err(e)

    def stream_complete(self):
        if self.synthesizer is None:
            return
        self.synthesizer.streaming_complete()

    def on_open(self):
        # log.info("[TTS] open")
        ...

    def on_complete(self):
        # log.info("[TTS] finished")
        self.on_msg("Completed", 1)

    def on_error(self, message: str):
        log.error(f"[TTS] failed, {message}")

    def on_close(self):
        log.info(f"[TTS] closed")
        self.synthesizer = None

    def on_event(self, message):
        pass

    def on_data(self, data: bytes) -> None:
        # log.info("[TTS] result length: " + str(len(data)))
        self.on_msg(data)


if __name__ == "__main__":
    # cSpell: disable-next-line
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    std_handler = logging.StreamHandler()
    std_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[std_handler])

    def f(data, type=0):
        if type == 0:
            log.info(f"Data: {len(data)}")
        else:
            log.info("Message END")

    tts = TTSClient(on_msg=f)
    tts.process_msg("你好不好啊，我很好，真是个美妙的开始呢")
