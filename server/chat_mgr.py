import base64
import logging
from flask import request, json
from flask_socketio import send, emit

log = logging.getLogger(__name__)


class ClientContext:

    def __init__(self):
        self.pending_audio = False


def translate_text(text):
    return text


def fun_asr(audio_data):
    return 'size: ' + str(len(audio_data))


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

    def handle_audio(self, sid, audio_data):
        if self.clients.get(sid).pending_audio:
            return
        self.clients[sid].pending_audio = True

        # 异步处理语音识别
        self.socketio.start_background_task(self.process_audio_chain, sid, audio_data)

    def process_audio_chain(self, sid, audio_data):
        try:
            text = fun_asr(audio_data)  # 需实现FunASR的具体调用
            self.socketio.emit('message', {'type': 'recognition', 'content': text}, room=sid)

            # 继续翻译
            translated = translate_text(text)
            self.socketio.emit('message', {'type': 'translation', 'content': translated}, room=sid)
        except Exception as e:
            log.error(f'Error processing audio chain: {e}')
            self.socketio.emit('message', {'type': 'error', 'content': str(e)}, room=sid)
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
