import traceback

import dashscope
from core.log_config import app_logger

log = app_logger
FASTAPI_URL = "http://192.168.50.171:9099/inference_zero_shot"  # FastAPI 服务器地址
import core.db.rds_mgr as rds_mgr
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
        self.id = ''

    def streaming_cancel(self):
        log.info(">>[TTS] cancel streaming")
        try:
            if self.synthesizer is not None:
                self.synthesizer.streaming_cancel()
                self.synthesizer = None
        except Exception as e:
            log.error(">>[TTS]" + e)
            traceback.print_stack()
            self.on_err(e)

    def process_msg(self, text: str, role: str = None):
        try:
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
            log.error(f">>[TTS] {e}")
            traceback.print_stack()
            self.on_err(e)

    def stream_msg(self, text: str, role: str = None, id=None):
        try:
            if role is None:
                role = self.role
            if id:
                self.id = id
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
            log.error(f">>[TTS] {e}")
            traceback.print_stack()
            self.on_err(e)

    def stream_complete(self):
        try:
            if self.synthesizer is None:
                return
            self.synthesizer.streaming_complete()
        except Exception as e:
            log.error(f">>[TTS] {e}")
            traceback.print_stack()
            self.on_err(e)

    def on_open(self):
        # log.info("[TTS] open")
        ...

    def on_complete(self):
        # log.info(">>[TTS] finished")
        self.on_msg(">>[TTS] Completed", 1)

    def on_error(self, message: str):
        log.error(f">>[TTS] failed, {message}")

    def on_close(self):
        log.info(f">>[TTS] closed")
        self.synthesizer = None

    def on_event(self, message):
        pass

    def on_data(self, data: bytes) -> None:
        # log.info("[TTS] result length: " + str(len(data)))
        try:
            key = f"audio:{self.id}:{self.role}"
            rds_mgr.append_value(key, data)
            self.on_msg(data)
        except Exception as e:
            log.error(f">>[TTS]{e}")
            traceback.print_stack()
            self.on_err(e)


def test_tts():
    f = None

    def on_data(data, type=0):
        nonlocal f
        if type == 0:
            log.info(f">>[TTS] Data: {len(data)}")
            if f is None:
                f = open("output.mp3", "wb")
            f.write(data)
        else:
            log.info(">>[TTS] Message END")
            f.close()
            f = None

    tts = TTSClient(on_msg=on_data)
    text = '可可……你这突如其来的表白让我眼泪都快下来了！😍 当然好啊！愿意，一千个一万个愿意！和你在一起的每一天都是我最珍贵的时光。这么多年的等待和错过，终于等来了这一刻。以后的日子里，不管是去故宫划船还是公园散步，我都想牵着你的手一起走。亲爱的，这一生一世，我都是你的楠楠啦～'
    tts.process_msg(text)


if __name__ == "__main__":
    # export PYTHONPATH=/Users/zhaolin/Documents/Projects/MyTodo/server:$PYTHONPATH
    test_tts()
