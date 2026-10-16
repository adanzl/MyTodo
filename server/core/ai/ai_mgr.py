"""Doubao（火山引擎）大模型 API 调用封装。

该模块提供最小封装以便在服务端调用豆包 Chat Completions 接口。
配置项来源于 `core.config.config`。

注意：此处为轻量封装，不负责复杂的重试/限流/熔断策略。
"""

import json

import requests

from core.config import app_logger, config

log = app_logger
API_URL = config.DOUBAO_API_URL
DOU_BAO_AK = config.DOUBAO_AK
ENDPOINT = "/api/v3/chat/completions"
DOUBAO_MODEL = config.DOUBAO_MODEL

# 请求超时（连接, 读）秒数。
# 必须显式指定：本服务的 HTTP 处理都在同一个 gevent hub 线程上，requests 默认无超时，
# 一旦方舟那边不返回（或网络半开），这个调用会一直挂着不返回，调用方永远等不到结果。
# 取值理由：
# - 连接 5s：DNS + TCP + TLS 正常在 1s 内完成，5s 足够覆盖抖动，超了基本就是不可达；
# - 读 60s：这里是**非流式**的 Chat Completions，要等整段回答生成完才回包，
#   单次生成给到 60s（与 ai_local 里查历史的 (5, 30) 同口径但更宽松，因为要等生成）。
TIMEOUT = (5, 60)


def init() -> None:
    """预留初始化入口。

    当前模块为纯函数封装，无需显式初始化；保留该函数用于后续扩展。
    """
    return None


def generate_headers() -> dict[str, str]:
    """生成请求豆包 API 所需的 HTTP headers。"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {DOU_BAO_AK}",
    }


def call_doubao_api(prompt: str) -> dict | None:
    """调用 Doubao Chat Completions 接口。

    Args:
        prompt (str): 用户输入的提示词。

    Returns:
        dict | None: 成功时返回接口 JSON；失败时返回 None。
    """
    headers = generate_headers()
    data = {
        "model": DOUBAO_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }
    try:
        response = requests.post(
            API_URL + ENDPOINT,
            data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            timeout=TIMEOUT,
        )
        log.debug(response.text)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log.error(f"[Doubao] request error: {e}")
        return None


if __name__ == "__main__":
    call_doubao_api("你好")
