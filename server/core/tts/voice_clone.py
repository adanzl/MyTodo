"""DashScope Voice Enrollment（声音克隆/音色注册）封装。

该模块通过 DashScope 的 `VoiceEnrollmentService` 注册音色，并轮询音色部署状态。
主要用于 TTS 的自定义 voice_id 准备阶段。

注意：本文件当前更偏向于脚本/实验性质用法，若要用于服务端长期运行建议：
- 将 `VOICE_PREFIX`、`TARGET_MODEL` 配置化；
- 增加更明确的异常类型与重试策略；
- 明确回调 `on_msg/on_err` 的协议。
"""

import json
import time

import dashscope
from dashscope.audio.tts_v2 import *

try:
    from core.config import app_logger, config

    log = app_logger
    ALI_KEY = config.ALI_KEY
except ImportError:
    from dotenv import load_dotenv
    import os

    load_dotenv()
    import logging

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    log = logging.getLogger()
    ALI_KEY = os.getenv('ALI_KEY', '')
    print("use default log")

TARGET_MODEL = "cosyvoice-v3-plus"
VOICE_PREFIX = "leo"  # 仅允许数字和小写字母，小于十个字符

service = VoiceEnrollmentService()


class VoiceClone(ResultCallback):
    """Voice enrollment 封装。"""

    def __init__(self, on_msg=None, on_err=None):
        """创建 VoiceClone。

        Args:
            on_data: 预留回调。
            on_err: 错误回调。
        """
        self.on_data = on_msg or (lambda x, y: None)
        self.on_err = on_err or (lambda x: None)
        dashscope.api_key = ALI_KEY
        self.voice_id = None

    def clone_voice(self, audio_url: str):
        try:
            self.voice_id = service.create_voice(target_model=TARGET_MODEL,
                                                 prefix=VOICE_PREFIX,
                                                 url=audio_url)
            log.info(
                f"Voice enrollment submitted successfully. Request ID: {service.get_last_request_id()}"
            )
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
                    raise RuntimeError(
                        f"Voice processing failed with status: {status}")
                # 对于 "DEPLOYING" 等中间状态，继续等待
                time.sleep(poll_interval)
            except Exception as e:
                log.error(f"Error during status polling: {e}")
                time.sleep(poll_interval)
        return False

    def on_open(self):
        log.info(f">>[VOICE_CLONE] open")

    def on_error(self, message: str):
        log.error(f">>[VOICE_CLONE] failed, {message}")

    def on_close(self):
        log.info(f">>[VOICE_CLONE] closed")

    def on_event(self, message):
        try:
            msg = json.loads(message)
            usage = msg.get("payload", {}).get("usage")
            if usage is not None:
                log.debug(f">>[VOICE_CLONE] usage: {usage}")
        except Exception as e:
            log.error(f">>[VOICE_CLONE] event error: {e}")

    def process_msg(self, text: str, voice_id: str):
        try:
            synthesizer = SpeechSynthesizer(
                model=TARGET_MODEL,
                voice=voice_id,
                callback=self,
            )
            synthesizer.call(text)

        except Exception as e:
            log.error(f">>[TTS] {e}")
            self.on_err(e)


if __name__ == "__main__":
    # load_dotenv(dotenv_path='.env')
    log.info(f">>[VOICE_CLONE] ALI_KEY: {os.getenv('ALI_KEY')}")
    log.info(f">>[VOICE_CLONE] VOICE_PREFIX: {VOICE_PREFIX}")
    log.info(f">>[VOICE_CLONE] TARGET_MODEL: {TARGET_MODEL}")
    f = None

    def on_data(data, type=0):
        global f
        if type == 0:
            # type=0 表示音频数据
            if isinstance(data, bytes):
                # log.info(f">>[VOICE_CLONE] Data: {len(data)} bytes")
                if f is None:
                    f = open("output.mp3", "wb")
                    log.info(
                        f">>[VOICE_CLONE] Start File: {os.path.abspath(f.name)}"
                    )
                f.write(data)
            else:
                log.info(f">>[VOICE_CLONE] Data: {data}")
        else:
            # type=1 表示完成消息
            log.info(f">>[VOICE_CLONE] Message END: {data}")
            if f is not None:
                log.info(
                    f">>[VOICE_CLONE] End File: {os.path.abspath(f.name)}")
                f.close()
                f = None

    # audio_url = "https://funaudiollm.github.io/cosyvoice2/audios/1.ZeroShot/ZH_2_prompt.wav"
    audio_url = "https://leo-zhao.natapp4.cc/api/media/files/mnt/ext_base/audio/cancan.mp3"
    voice_clone = VoiceClone(on_msg=on_data)
    # voice_id = voice_clone.clone_voice(audio_url=audio_url)
    voice_id = "cosyvoice-v3-plus-leo-34ba9eaebae44039a4a9426af6389dcd"
    # bReady = voice_clone.wait_for_voice_id()
    # if not bReady:
    #     log.error(f">>[VOICE_CLONE] Voice clone failed")
    #     exit(1)
    log.info(f">>[VOICE_CLONE] Voice clone success, voice_id: {voice_id}")
    text = '你好，我是小爱同学，很高兴认识你。'
    voice_clone.process_msg(text=text, voice_id=voice_id)
