import base64
import logging
import time

from core.chat.asr_client import AsrClient
from flask import json, request
from flask_socketio import emit

log = logging.getLogger(__name__)


class ClientContext:

    def __init__(self, sid):
        self.sid = sid
        self.pending_audio = False
        self.asr = AsrClient(self.on_asr_result)
        self.asr.connect()

    def on_asr_result(self, result):
        log.info(f"ASR result: {result}")
        if result and result["text"]:
            emit("message", {"type": "recognition", "content": result["text"]})

    def start_asr(self, sample_rate):
        try:
            self.asr.start_asr(sample_rate)
            self.pending_audio = True
        except Exception as e:
            log.error(f"Error starting ASR: {e}")

    def end_asr(self):
        try:
            self.asr.end_asr()
        except Exception as e:
            log.error(f"Error closing ASR: {e}")
        self.pending_audio = False

    def close(self):
        self.asr.close()


def translate_text(text):
    return text


class ChatMgr:

    def __init__(self, socketio):
        self.socketio = socketio
        self.clients: dict[str, ClientContext] = {}  # sid -> ClientContext
        self.register_events()

    def add_client(self, sid):
        self.clients[sid] = ClientContext(sid)

    def remove_client(self, sid):
        if sid in self.clients:
            del self.clients[sid]

    def handle_text(self, sid, text):
        translated = translate_text(text)
        self.socketio.emit('message', {'type': 'translation', 'content': translated}, room=sid)

    def handle_audio(self, sid, sample, audio_bytes):
        client = self.clients.get(sid)
        if not client or client.pending_audio:
            return
        client.pending_audio = True
        self.socketio.start_background_task(self.process_audio_chain, sid, sample, audio_bytes)

    def process_audio_chain(self, sid, sample, audio_bytes):
        try:
            self.fun_asr(sid, audio_bytes, sample)  # 调用 FunASR 进行语音识别
            # self.socketio.emit("message", {"type": "recognition", "content": text}, room=sid)

            # # 继续翻译
            # translated = translate_text(text)
            # self.socketio.emit("message", {"type": "translation", "content": translated}, room=sid)
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
                    self.handle_audio(client_id, data['sample'], audio_bytes)

    def fun_asr(self, sid, audio_bytes, sample_rate):
        ctx = self.clients[sid]
        if not ctx: return 
        if not ctx.pending_audio:
            ctx.start_asr(sample_rate)
            time.sleep(0.5)
        ctx.asr.send_data(audio_bytes)    
        
