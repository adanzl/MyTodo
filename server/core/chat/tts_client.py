import requests

FASTAPI_URL = "http://192.168.50.171:9099/"  # FastAPI 服务器地址

class TTSClient:
    def __init__(self, on_msg=None, on_err=None):
        self.on_msg = on_msg or (lambda x, y: None)
        self.on_err = on_err or (lambda x: None)

    def stream_msg(self, text: str, user: str = "中文女",  timeout: int = 30):

        try:
            # 发起请求到 FastAPI 服务器，并处理流式响应
            payload = {
                'tts_text': text,
                'spk_id': user,  # 中文女
            }
            with requests.request("GET", FASTAPI_URL, data=payload, stream=True) as resp:
                if resp.status_code != 200:
                    self.on_err(Exception(f"Error: {resp.status_code}, {resp.text}"))
                    return

                # 使用 Socket.IO 的分片消息发送音频数据
                for chunk in resp.iter_content(chunk_size=16000):
                    if chunk:
                        # 使用二进制消息发送音频数据
                        self.on_msg(chunk)

            self.on_msg("Completed", 1)

        except Exception as e:
            self.on_err(e)
