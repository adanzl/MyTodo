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

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
                    log.info(f">>[VOICE_CLONE] Start File: {os.path.abspath(f.name)}")
                f.write(data)
            else:
                log.info(f">>[VOICE_CLONE] Data: {data}")
        else:
            # type=1 表示完成消息
            log.info(f">>[VOICE_CLONE] Message END: {data}")
            if f is not None:
                log.info(f">>[VOICE_CLONE] End File: {os.path.abspath(f.name)}")
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
    text = '古时候，晋国的王子期驾驭马车的技术非常高超，许多人都向他学习。\n ' + \
        '有一天，赵襄王也向王子期学习驾驭马车。刚学了不久，能掌握基本的技巧后，他就很着急地要求与王子期进行驾车比赛，看谁驾车跑得快。\n' + \
        '结果，一连比了三场，赵襄王连输三场，而且还远远地落后于王子期的马车。赵襄王有点不高兴了，他心有不甘，埋怨王子期道："你是不是没有把驾车的技术全部传授给我？我完全按照你教的要点去做，为什么你会远远地领先呢？难不成你还留了一手？"\n' + \
        '王子期听后，不慌不忙地回答道："大王先不要生气，驾车的方法、步骤和技巧，我已经全部传授给您了，大王掌握得也很好。"赵襄王接话道："是啊！但为什么我奋力地王子期对于追赶，还是追不上你呢？"\n' + \
        '王子期微微笑着说："问题就在于大王的真正原因。运用技巧的错误。驾车时最重要的是使马在车辕里松紧适度、自在舒适，而驾车人的注意力则要集山大只的身上，让人与马的动作配合协调，这样才可以他本政得以，政得远。可是刚才您在与我比赛时稍微落后了，您的心里就着急，就使劲鞭打奔马，拼命要超过我；而一旦跑到了我的前面，又时常回头观望，生怕我再赶上愁。"\n' + \
        '赵襄王听王子期一条一条地分析着比赛，若有所思，似乎明白了许多，时不时地点点头表示赞同。\n' + \
        '其实，在比赛中有时领先，有时落后，都是很正常的。而您不论是领先还是落后，心情始终十分紧张。您的注如果只想着意力几乎全都集中在比赛的胜负上了，又怎比赛的胜负，不么可能去赶好马、驾好车呢？这就是您三次比赛、三次落后的根本原因啊！\n' + \
        '王子期最后画龙点睛地总结说。\n' + \
        '赵襄王恍然大悟，不禁哈哈大笑起来，要求再与王子期加赛三场。\n'
    voice_clone.process_msg(text=text, voice_id=voice_id)
