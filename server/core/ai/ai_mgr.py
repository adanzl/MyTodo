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
        )
        log.debug(response.text)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log.error(f"[Doubao] request error: {e}")
        return None


if __name__ == "__main__":
    call_doubao_api("你好")
