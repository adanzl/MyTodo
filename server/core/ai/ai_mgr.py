import json
import logging
import traceback

import requests

log = logging.getLogger(__name__)
API_URL = "https://ark.cn-beijing.volces.com"
DOU_BAO_AK = '91cd8756-4fd8-4235-a2bd-777949576205'
# 这里需要根据实际的 API 路径进行修改
ENDPOINT = "/api/v3/chat/completions"
DOUBAO_MODEL = "ep-20250205111100-zhcpq"  # cSpell:disable-line


def init():
    ...


# 生成请求头
def generate_headers():
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {DOU_BAO_AK}",
    }
    return headers


# 调用火山引擎大模型 API
def call_doubao_api(prompt):
    headers = generate_headers()
    data = {
        "model": DOUBAO_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            },
        ]
    }
    try:
        response = requests.post(
            API_URL + ENDPOINT,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers=headers,
        )
        print(response.text)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"请求出错: {e}")
        return None


if __name__ == '__main__':
    call_doubao_api("你好")
