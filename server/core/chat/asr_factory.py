"""ASR provider factory.

Keep the original local FunASR client available while allowing cloud ASR to be
selected through configuration.
"""

from core.chat.asr_client import AsrClient
from core.chat.aliyun_asr_client import AliyunAsrClient
from core.config import config


def create_asr_client(on_result=None, on_err=None):
    provider = (config.ASR_PROVIDER or 'aliyun').strip().lower()
    if provider in {'aliyun', 'dashscope', 'qwen'}:
        return AliyunAsrClient(on_result, on_err)
    if provider in {'funasr', 'local'}:
        return AsrClient(on_result, on_err)
    raise ValueError(f'Unsupported ASR_PROVIDER: {provider}')
