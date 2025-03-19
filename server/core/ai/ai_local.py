import json

import requests
from core.log_config import root_logger

log = root_logger()
API_URL = "http://192.168.50.171:9098/v1"
# cSpell: disable-next-line
API_KEY = "app-dLf0axfqNnVHwWjFqs0EVo8H"


class AILocal:

    def __init__(self, on_msg=None, on_err=None):
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
        self.aiConversationId = ""
        self.user = 'user'
        self.on_msg = on_msg or (lambda x, y: None)
        self.on_err = on_err or (lambda x: None)
        self.last_task_id = -1

    def stream_msg(self, query: str, inputs: dict = None, timeout: int = 30, try_times=0):
        payload = {
            "inputs": inputs or {},
            "query": query,
            "conversation_id": self.aiConversationId,
            "response_mode": "streaming",  # 启用流式模式
            "user": self.user,
        }
        log.info(f">>[AI] Query: {query}")

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
                    if line and line.startswith(b"data:"):
                        chunk = json.loads(line.decode("utf-8")[6:])
                        self.aiConversationId = chunk["conversation_id"]
                        if 'task_id' in chunk:
                            self.last_task_id = chunk['task_id']
                        if "answer" in chunk:
                            self.on_msg(chunk["answer"], 0)
                        elif "error" in chunk:
                            raise RuntimeError(chunk["error"])
                        elif chunk['event'] == 'message_end':
                            log.info(chunk['metadata'])
                            self.on_msg(chunk["metadata"], 1)

        except requests.exceptions.RequestException as e:
            log.error(f">>[AI] 请求失败: {str(e)}")
            if try_times < 1:
                self.aiConversationId = ""
                self.stream_msg(query, inputs, timeout, try_times + 1)
            else:
                self.on_err(e)
        except Exception as ee:
            log.error(">>[AI] 响应数据解析错误 " + line.decode("utf-8"))
            self.on_err(ee)

    def streaming_cancel(self):
        payload = {"user": self.user}
        log.info(">>[AI] cancel streaming")
        try:
            with requests.post(f"{API_URL}/chat-messages/:{self.last_task_id}/stop", headers=self.headers,
                               json=payload) as response:
                response.raise_for_status()

        except Exception as ee:
            log.error(f">>[AI] 响应数据解析错误 {ee}")
            self.on_err(ee)


if __name__ == "__main__":

    def f(msg):
        print(msg, end="")

    ai = AILocal(f)
    ai.user = 'leo'
    while True:
        log.info('ready')
        msg = input('>?')
        ai.stream_msg(msg)
