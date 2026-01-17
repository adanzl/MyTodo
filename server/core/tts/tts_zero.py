import os
import dashscope
from dashscope.audio.tts_v2 import VoiceEnrollmentService, SpeechSynthesizer
# cSpell: disable

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

dashscope.api_key = os.getenv('ALI_KEY', '')
target_model = "cosyvoice-v1"
# cSpell: enable
# 创建语音注册服务实例
service = VoiceEnrollmentService()

# 调用create_voice方法复刻声音，并生成voice_id
# voice_id = service.create_voice(target_model=target_model, prefix=w1['prefix'], url=w1['url'])
# print("requestId: ", service.get_last_request_id())
# print(f"your voice id is {voice_id}")
voice_id = service.create_voice(target_model=target_model, prefix=w2['prefix'], url=w2['url'])
print("requestId: ", service.get_last_request_id())
print(f"your voice id is {voice_id}")
