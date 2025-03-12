import logging
import requests
import json

API_URL = "http://192.168.50.171:9098/v1"
API_KEY = "app-Iji9pr366YfTcOewZmOhLh8h"
log = logging.getLogger(__name__)


class AILocal:

    def __init__(self, on_msg=None):
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
        self.conversation_id = ""
        self.on_msg = on_msg

    def stream_msg(self, query: str, user: str = "", inputs: dict = None, timeout: int = 30):
        payload = {
            "inputs": inputs or {},
            "query": query,
            "conversation_id": self.conversation_id,
            "response_mode": "streaming",  # 启用流式模式
            "user": user,
        }

        try:
            with requests.post(
                    f"{API_URL}/chat-messages",
                    headers=self.headers,
                    json=payload,
                    stream=True,
                    timeout=timeout,
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode("utf-8")[6:])
                        self.conversation_id = chunk["conversation_id"]
                        if "answer" in chunk:
                            if self.on_msg:
                                self.on_msg(chunk["answer"])
                        elif "error" in chunk:
                            raise RuntimeError(chunk["error"])

        except requests.exceptions.RequestException as e:
            print(f"请求失败: {str(e)}")
        except Exception as ee:
            print("响应数据解析错误 " + line.decode("utf-8"))


if __name__ == "__main__":

    def f(msg):
        print(msg, end="")

    ai = AILocal(f)
    while True:
        print('ready')
        msg = input('>?')
        ai.stream_msg(msg)
