import base64
import logging
import time

from flask import json, request

from app import app, socketio
from core.chat.asr_client import AsrClient

log = logging.getLogger(__name__)


class ClientContext:

    def __init__(self, sid, on_result):
        self.sid = sid
        self.pending_audio = False
        self.asr = AsrClient(self.on_asr_result)
        self.asr.connect()
        self.on_result = on_result

    def on_asr_result(self, result):
        log.info(f"ASR result: {result}")
        self.pending_audio = False
        self.on_result(self.sid, result)

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

    def close(self):
        self.asr.close()


def translate_text(text):
    return text


class ChatMgr:

    def __init__(self):
        self.clients: dict[str, ClientContext] = {}  # sid -> ClientContext
        self.register_events()

    def add_client(self, sid):
        self.clients[sid] = ClientContext(sid, self.handle_ars_result)

    def handle_ars_result(self, sid, result):
        with app.app_context():
            try:
                msg = {"type": "recognition", "content": result}
                log.info(f"[CHAT] Emit result: {msg} , {sid}")
                socketio.emit("message", msg, room=sid)
            except Exception as e:
                log.error(f"[CHAT] Error emitting result to client {sid}: {e}")

    def remove_client(self, sid):
        if sid in self.clients:
            del self.clients[sid]

    def handle_text(self, sid, text):
        translated = translate_text(text)
        socketio.emit('message', {'type': 'translation', 'content': translated}, room=sid)

    def handle_audio(self, sid, sample_rate, audio_bytes):
        client = self.clients.get(sid)
        if not client:
            return

        # socketio.start_background_task(self.process_audio_chain, sid, sample, audio_bytes)
        try:
            if not client.pending_audio:
                client.start_asr(sample_rate)
                time.sleep(0.001)
            client.asr.send_data(audio_bytes)
            socketio.emit("message", {"type": "recognition", "content": "OK"}, room=sid)

            # # 继续翻译
            # translated = translate_text(text)
            # socketio.emit("message", {"type": "translation", "content": translated}, room=sid)
        except Exception as e:
            log.error(f"Error processing audio chain: {e}")
            socketio.emit("message", {"type": "error", "content": str(e)}, room=sid)

    def register_events(self):
        # 处理客户端连接事件
        @socketio.on('handshake')
        def handle_handshake(data):
            if data['key'] == '123456':
                self.add_client(request.sid)
                log.info(f'Client {request.sid} connected. Total clients: {len(self.clients)}')
                socketio.emit('handshake_response', {'message': 'Handshake successful'})
                return {'status': 'connected'}
            else:
                socketio.disconnect(request.sid)
                return {'status': 'rejected'}

        # 处理客户端断开连接事件
        @socketio.on('disconnect')
        def handle_disconnect():
            log.info('[CHAT] disconnected')
            client_id = request.sid
            self.remove_client(client_id)
            log.info(f'Client {client_id} disconnected. Total clients: {len(self.clients)}')

        # 处理接收到的消息事件
        @socketio.on('message')
        def handle_message(msg):
            data = json.loads(msg)
            client_id = request.sid
            data_type = data['type']
            log.info(f'[CHAT] Received message from {client_id}: {data_type}')
            content = data.get('content', '')

            if client_id not in self.clients:
                return

            client = self.clients[client_id]

            if data_type == 'text':
                self.handle_text(client_id, content)
            elif data_type == 'audio':
                audio_bytes = base64.b64decode(content)
                self.handle_audio(client_id, data['simple'], audio_bytes)
                if data['finish']:
                    client.end_asr()
