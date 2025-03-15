import logging
import requests
import json

API_URL = "http://192.168.50.171:9098/v1"
# cSpell: disable-next-line
API_KEY = "app-dLf0axfqNnVHwWjFqs0EVo8H"
log = logging.getLogger(__name__)


class AILocal:

    def __init__(self, on_msg=None, on_err=None):
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
        self.aiConversationId = ""
        self.on_msg = on_msg or (lambda x, y: None)
        self.on_err = on_err or (lambda x: None)

    def stream_msg(self, query: str, user: str = "user", inputs: dict = None, timeout: int = 30):
        payload = {
            "inputs": inputs or {},
            "query": query,
            "conversation_id": self.aiConversationId,
            "response_mode": "streaming",  # 启用流式模式
            "user": user,
        }
        log.info(f"[AI] Query: {query}")

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
                        self.aiConversationId = chunk["conversation_id"]
                        if "answer" in chunk:
                            self.on_msg(chunk["answer"], 0)
                        elif "error" in chunk:
                            raise RuntimeError(chunk["error"])
                        elif chunk['event'] == 'message_end':
                            log.info(chunk['metadata'])
                            self.on_msg(chunk["metadata"], 1)

        except requests.exceptions.RequestException as e:
            log.error(f"请求失败: {str(e)}")
            self.on_err(e)
        except Exception as ee:
            log.error("响应数据解析错误 " + line.decode("utf-8"))
            self.on_err(ee)


if __name__ == "__main__":
    # cSpell: disable-next-line
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    std_handler = logging.StreamHandler()
    std_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[std_handler])

    def f(msg):
        print(msg, end="")

    ai = AILocal(f)
    while True:
        log.info('ready')
        msg = input('>?')
        ai.stream_msg(msg, 'leo')
