import base64
import uuid
import requests

API_URL = 'https://openspeech.bytedance.com/api/v1/tts'
API_ID = '9815505713'
API_TOKEN = 'GRoDq8HhDpyGe7NtdC44thL0uuNtTDfZ'


def gen_tts(text: str, voice_id: str):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer;{API_TOKEN}",
    }
    payloads = {
        "app": {
            "appid": API_ID,
            "token": 'access_token',
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
        }
    }
    with requests.post(API_URL, headers=headers, json=payloads) as r:
        # r.raise_for_status()

        data = r.json()
        # print(data)
        audio_bytes = base64.b64decode(data['data'])
        with open("output.mp3", "wb") as f:
            f.write(audio_bytes)


if __name__ == '__main__':
    text = '可可……你这突如其来的表白让我眼泪都快下来了！😍 当然好啊！愿意，一千个一万个愿意！和你在一起的每一天都是我最珍贵的时光。这么多年的等待和错过，终于等来了这一刻。以后的日子里，不管是去故宫划船还是公园散步，我都想牵着你的手一起走。亲爱的，这一生一世，我都是你的楠楠啦～'
    voice_id = 'ICL_zh_female_zhixingwenwan_tob'
    # voice_id = 'BV001_streaming'
    gen_tts(text, voice_id)