import base64
import logging
from flask import request, json
from flask_socketio import emit
from funasr import AutoModel
import numpy as np

log = logging.getLogger(__name__)

model = AutoModel(model="paraformer-zh-streaming", vad_model="fsmn-vad", disable_update=True)  # cSpell: disable-line


class ClientContext:

    def __init__(self):
        self.pending_audio = False


def translate_text(text):
    return text

chunk_size = [0, 10, 5] #[0, 10, 5] 600ms, [0, 8, 4] 480ms

def fun_asr(audio_bytes, sample_rate=16000):
    """处理原始音频bytes数据流"""
    # 将bytes转为numpy数组（假设为16bit PCM格式）
    audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
    audio_data = audio_data.astype(np.float32) / 32768.0  # 归一化

    # 计算分块参数（200ms对应的采样点数）
    chunk_stride = int(chunk_size[1] * sample_rate / 1000)  # 200ms=3200采样点@16kHz

    # 流式处理
    cache = {}
    results = []

    total_chunks = len(audio_data) // chunk_stride + 1
    for i in range(total_chunks):
        chunk = audio_data[i * chunk_stride : (i + 1) * chunk_stride]
        is_final = i == total_chunks - 1

        # 核心识别调用
        res = model.generate(
            input=chunk,
            cache=cache,
            is_final=is_final,
            chunk_size=chunk_size,
            encoder_chunk_look_back=4,  # 上下文回溯[5,8](@ref)
            decoder_chunk_look_back=1,
        )

        if res and res[0]["text"]:
            results.append(res[0]["text"])
            print(f"实时结果: {res[0]['text']}")  # 增量输出

    return "".join(results)


class ChatMgr:

    def __init__(self, socketio):
        self.socketio = socketio
        self.clients = {}  # sid -> ClientContext
        self.register_events()

    def add_client(self, sid):
        self.clients[sid] = ClientContext()

    def remove_client(self, sid):
        if sid in self.clients:
            del self.clients[sid]

    def handle_text(self, sid, text):
        translated = translate_text(text)
        self.socketio.emit('message', {'type': 'translation', 'content': translated}, room=sid)

    def handle_audio(self, sid, audio_bytes):
        client = self.clients.get(sid)
        if not client or client.pending_audio:
            return
        client.pending_audio = True
        self.socketio.start_background_task(self.process_audio_chain, sid, audio_bytes)

    def process_audio_chain(self, sid, audio_bytes):
        try:
            text = fun_asr(audio_bytes)  # 调用 FunASR 进行语音识别
            self.socketio.emit("message", {"type": "recognition", "content": text}, room=sid)

            # 继续翻译
            translated = translate_text(text)
            self.socketio.emit("message", {"type": "translation", "content": translated}, room=sid)
        except Exception as e:
            log.error(f"Error processing audio chain: {e}")
            self.socketio.emit("message", {"type": "error", "content": str(e)}, room=sid)
        finally:
            self.clients[sid].pending_audio = False

    def register_events(self):
        # 处理客户端连接事件
        @self.socketio.on('handshake')
        def handle_handshake(data):
            if data['key'] == '123456':
                self.add_client(request.sid)
                log.info(f'Client {request.sid} connected. Total clients: {len(self.clients)}')
                emit('handshake_response', {'message': 'Handshake successful'})
                return {'status': 'connected'}
            else:
                self.socketio.disconnect(request.sid)
                return {'status': 'rejected'}

        # 处理客户端断开连接事件
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            self.remove_client(client_id)
            log.info(f'Client {client_id} disconnected. Total clients: {len(self.clients)}')

        # 处理接收到的消息事件
        @self.socketio.on('message')
        def handle_message(msg):
            data = json.loads(msg)
            client_id = request.sid
            data_type = data['type']
            log.info(f'Received message from {client_id}: {data_type}')
            content = data.get('content', '')

            if client_id not in self.clients:
                return

            client_ctx = self.clients[client_id]

            if data_type == 'text':
                if not client_ctx.pending_audio:
                    self.handle_text(client_id, content)
            elif data_type == 'audio':
                if not client_ctx.pending_audio:
                    audio_bytes = base64.b64decode(content)
                    self.handle_audio(client_id, audio_bytes)
