import requests
import logging
import json
import traceback

log = logging.getLogger(__name__)
FASTAPI_URL = "http://192.168.50.171:9099/inference_zero_shot"  # FastAPI 服务器地址

ROLE_MAP = {
    # cSpell: disable-next-line
    "太乙": '/mnt/data/CosyVoice/pretrained_models/prompt/zh_taiyi_prompt.wav',
    "default": '/mnt/data/CosyVoice/pretrained_models/prompt/zero_shot_prompt.wav',
    "中文女": '/mnt/data/CosyVoice/pretrained_models/prompt/zh_woman_prompt.wav',
}


class TTSClient:

    def __init__(self, on_msg=None, on_err=None):
        self.on_msg = on_msg or (lambda x, y: None)
        self.on_err = on_err or (lambda x: None)

    def stream_msg(self, text: str, user: str = ""):

        try:
            # 发起请求到 FastAPI 服务器，并处理流式响应
            payload = {
                "tts_text": text,
                "prompt_text": "希望你以后能够做的比我还好呦。",
            }
            prompt_wav = ROLE_MAP.get(user, ROLE_MAP["default"])
            files = [(
                "prompt_wav",
                ("prompt_wav", open(prompt_wav, "rb"), "application/octet-stream"),
            )]
            log.info(f"[TTS REQ] {json.dumps(payload,ensure_ascii=False)}")
            rsp = requests.request("GET", FASTAPI_URL, data=payload, files=files, stream=True)
            log.info(f"[TTS RSP]:  {rsp.status_code}, {rsp.reason}")
            if rsp.status_code != 200:
                self.on_err(Exception(f"Error: {rsp.status_code}, {rsp.text}"))
                return
            # 使用 Socket.IO 的分片消息发送音频数据
            for chunk in rsp.iter_content(chunk_size=16000):
                if chunk:
                    # 使用二进制消息发送音频数据
                    self.on_msg(chunk)
            log.info("[TTS COMPLETE] ")
            self.on_msg("Completed", 1)

        except Exception as e:
            log.error(e)
            traceback.print_stack()
            self.on_err(e)


if __name__ == "__main__":
    # cSpell: disable-next-line
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    std_handler = logging.StreamHandler()
    std_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[std_handler])

    def f(data, type=0):
        if type == 0:
            log.info(f"Data: {len(data)}")
        else:
            log.info("Message END")

    tts = TTSClient(on_msg=f)
    tts.stream_msg("你好不好啊，我很好，真是个美妙的开始呢")
