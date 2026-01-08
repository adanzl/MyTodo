import time
from dotenv import load_dotenv
import os

load_dotenv()

# coding=utf-8

import dashscope
from dashscope.audio.tts_v2 import *


try:
    from core.log_config import app_logger
    log = app_logger
except:
    import logging
    log = logging.getLogger()

TARGET_MODEL = "cosyvoice-v3-plus"
# 为音色起一个有意义的前缀
VOICE_PREFIX = "leo_audio"  # 仅允许数字和小写字母，小于十个字符

service = VoiceEnrollmentService()


class VoiceClone:

    def __init__(self, on_msg=None, on_err=None):
        self.on_msg = on_msg or (lambda x, y: None)
        self.on_err = on_err or (lambda x: None)
        dashscope.api_key = os.getenv('ALI_KEY')
        self.voice_id = None

    def clone_voice(self, audio_url: str):
        try:
            self.voice_id = service.create_voice(target_model=TARGET_MODEL, prefix=VOICE_PREFIX, url=audio_url)
            log.info(f"Voice enrollment submitted successfully. Request ID: {service.get_last_request_id()}")
            log.info(f"Generated Voice ID: {self.voice_id}")
        except Exception as e:
            log.error(f"Error during voice creation: {e}")
            raise e

    def wait_for_voice_id(self, max_attempts=30, poll_interval=10):
        for _ in range(max_attempts):
            try:
                voice_info = service.query_voice(voice_id=self.voice_id)
                status = voice_info.get("status")

                if status == "OK":
                    return True
                elif status == "UNDEPLOYED":
                    raise RuntimeError(f"Voice processing failed with status: {status}")
                # 对于 "DEPLOYING" 等中间状态，继续等待
                time.sleep(poll_interval)
            except Exception as e:
                log.error(f"Error during status polling: {e}")
                time.sleep(poll_interval)
        return False

    def process_msg(self, text: str, role: str = None):
        try:
            if role is None:
                role = self.role
            synthesizer = SpeechSynthesizer(
                model=TARGET_MODEL,
                voice=role,
                callback=self,
            )
            synthesizer.call(text)

        except Exception as e:
            log.error(f">>[TTS] {e}")
            self.on_err(e)


if __name__ == "__main__":
    # load_dotenv(dotenv_path='.env')
    print(os.getenv('ALI_KEY'))
    f = None

    def on_data(data, type=0):
        global f
        if type == 0:
            # type=0 表示音频数据
            if isinstance(data, bytes):
                log.info(f">>[VOICE_CLONE] Data: {len(data)} bytes")
                if f is None:
                    f = open("output.mp3", "wb")
                f.write(data)
            else:
                log.info(f">>[VOICE_CLONE] Data: {data}")
        else:
            # type=1 表示完成消息
            log.info(f">>[VOICE_CLONE] Message END: {data}")
            if f is not None:
                f.close()
                f = None

    def on_err(err):
        log.error(f">>[VOICE_CLONE] Error: {err}")

    audio_url = "https://funaudiollm.github.io/cosyvoice2/audios/1.ZeroShot/ZH_2_prompt.wav"
    voice_clone = VoiceClone(on_msg=on_data, on_err=on_err)
    voice_id = voice_clone.clone_voice(audio_url=audio_url)
    bReady = voice_clone.wait_for_voice_id(voice_id)
    if not bReady:
        log.error(f">>[VOICE_CLONE] Voice clone failed")
        exit(1)
    text = '可可……你这突如其来的表白让我眼泪都快下来了！😍 当然好啊！愿意，一千个一万个愿意！和你在一起的每一天都是我最珍贵的时光。这么多年的等待和错过，终于等来了这一刻。以后的日子里，不管是去故宫划船还是公园散步，我都想牵着你的手一起走。亲爱的，这一生一世，我都是你的楠楠啦～'
    voice_clone.process_msg(text, voice_id)
