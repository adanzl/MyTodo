import base64
import logging

from flask import json, request

from app import socketio
from core.chat.asr_client import AsrClient
from core.ai.ai_local import AILocal

log = logging.getLogger(__name__)


class ClientContext:

    def __init__(self, sid):
        self.sid = sid
        self.pending_audio = False
        self.ai = AILocal(self.on_ai_msg)
        self.asr = AsrClient(self.on_asr_result)

    def close(self):
        self.asr.close()

    def on_asr_result(self, text):
        self.ai.stream_msg(text)

    def on_ai_msg(self, text):
        log.info(f"[AI] ON MSG: {text}")
        msg = {"type": "translation", "content": text}
        socketio.emit('message', msg, room=self.sid)


def translate_text(text):
    return text


class ChatMgr:

    def __init__(self):
        self.clients: dict[str, ClientContext] = {}  # sid -> ClientContext
        self.register_events()

    def add_client(self, sid):
        self.clients[sid] = ClientContext(sid)

    def remove_client(self, sid):
        if sid in self.clients:
            del self.clients[sid]

    def handle_text(self, sid, text):
        # translated = translate_text(text)
        client: ClientContext = self.clients.get(sid)
        client.ai.stream_msg(text, 'user')
        # socketio.emit('message', {'type': 'translation', 'content': translated}, room=sid)

    def handle_audio(self, sid, sample_rate, audio_bytes):
        '''
        处理音频数据
        '''
        # log.info(f"[CHAT] Handle_audio: {len(audio_bytes)} bytes")
        client: ClientContext = self.clients.get(sid)
        if not client:
            log.warning(f"[CHAT] Client {sid} not found")
            return
        try:
            client.asr.process_audio(sample_rate, audio_bytes, sid)
        except Exception as e:
            log.error(f"[CHAT] Error emitting result to client {sid}: {e}")

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
            content = data.get('content', '')

            if client_id not in self.clients:
                return

            if data_type == 'text':
                log.info(f'[CHAT] Received message from {client_id}: {data_type}')
                self.handle_text(client_id, content)
            elif data_type == 'audio':
                audio_bytes = base64.b64decode(content)
                self.handle_audio(client_id, data['sample'], audio_bytes)
                if data['finish']:
                    self.clients[client_id].asr.end_asr()
