import requests

FASTAPI_URL = "http://localhost:8000/stream-tts"  # FastAPI 服务器地址

class TTSClient:
    def __init__(self, on_msg=None, on_err=None):
        self.on_msg = on_msg or (lambda x, y: None)
        self.on_err = on_err or (lambda x: None)

    def stream_msg(self, text: str, user: str = "user",  timeout: int = 30):

        try:
            # 发起请求到 FastAPI 服务器，并处理流式响应
            with requests.post(FASTAPI_URL, json={"text": text}, stream=True) as resp:
                if resp.status_code != 200:
                    self.on_err(Exception(f"Error: {resp.status_code}, {resp.text}"))
                    return

                # 使用 Socket.IO 的分片消息发送音频数据
                for chunk in resp.iter_content(chunk_size=1024):
                    if chunk:
                        # 使用二进制消息发送音频数据
                        self.on_msg(chunk)
                        # socketio.emit('tts_audio_stream', {'data': chunk.hex()}, json=False, namespace='/tts')

            # emit('tts_response', {'status': 'Completed'})
            self.on_msg("Completed", 1)

        except Exception as e:
            self.on_err(e)
