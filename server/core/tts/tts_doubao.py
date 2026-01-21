"""Doubao TTS（火山引擎语音合成）调用示例。

该模块提供一个最小函数 `gen_tts` 用于调用 Doubao TTS 接口生成语音。

注意：
- 需要在配置中提供 `DOUBAO_TTS_API_URL/DOUBAO_TTS_API_ID/DOUBAO_TTS_API_TOKEN`；
- 本文件当前更偏向于“脚本/示例”，如需在服务端正式使用建议补充错误处理与返回值规范化。
"""

import base64
import uuid

import requests

from core.config import config

API_URL = config.DOUBAO_TTS_API_URL
API_ID = config.DOUBAO_TTS_API_ID
API_TOKEN = config.DOUBAO_TTS_API_TOKEN


def gen_tts(text: str, voice_id: str) -> bytes:
    """生成 TTS 音频。

    Args:
        text (str): 待合成文本。
        voice_id (str): 声音 ID（voice_type）。

    Returns:
        bytes: 合成得到的 MP3 音频 bytes。

    Raises:
        requests.RequestException: HTTP 请求失败。
        KeyError: 响应 JSON 缺少预期字段。
        ValueError: Base64 解码失败。
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer;{API_TOKEN}",
    }
    payloads = {
        "app": {
            "appid": API_ID,
            "token": "access_token",
            "cluster": "volcano_tts",
        },
        "user": {
            "uid": "uid123"
        },
        "audio": {
            "voice_type": voice_id,
            "encoding": "mp3",
            "speed_ratio": 1.0,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "operation": "query",
        },
    }
    with requests.post(API_URL, headers=headers, json=payloads) as r:
        data = r.json()
        audio_bytes = base64.b64decode(data["data"])
        return audio_bytes


if __name__ == "__main__":
    text = "你好"
    voice_id = "ICL_zh_female_zhixingwenwan_tob"
    audio_bytes = gen_tts(text, voice_id)
    with open("output.mp3", "wb") as f:
        f.write(audio_bytes)
