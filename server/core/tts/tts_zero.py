"""DashScope Voice Enrollment 快速脚本（Zero-shot prompt）。

用于通过 DashScope `VoiceEnrollmentService.create_voice` 注册/复刻音色并输出 voice_id。
该文件为实验脚本：直接运行会进行外部网络请求。
"""

import dashscope
from dashscope.audio.tts_v2 import VoiceEnrollmentService

from core.config import config

# cosyvoice-taiyi-f42ada0a805d4a5cab0272a1d0acc834
w1 = {
    'url': "https://eff-learn-object.oss-cn-beijing.aliyuncs.com/ZH_2_prompt.wav",
    'text': "对，这就是我，万人敬仰的太乙真人，虽然有点婴儿肥，但也掩不住我逼人的帅气",
    'prefix': 'taiyi',
}
# cosyvoice-woman-8a96d641d8d0491984c085d98870b79d
w2 = {
    'url': "https://eff-learn-object.oss-cn-beijing.aliyuncs.com/Zh_7_prompt.wav",
    'text': "今夜的月光如此清亮,不做些什么,真是浪费,随我一同去月下漫步吧,不许拒绝",
    'prefix': 'woman',
}

dashscope.api_key = config.ALI_KEY
target_model = "cosyvoice-v1"

service = VoiceEnrollmentService()

voice_id = service.create_voice(target_model=target_model, prefix=w2['prefix'], url=w2['url'])
print("requestId: ", service.get_last_request_id())
print(f"your voice id is {voice_id}")
