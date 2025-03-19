import base64
import logging

from flask import json, request

from app import socketio
from core.chat.asr_client import AsrClient
from core.ai.ai_local import AILocal
from core.chat.tts_client import TTSClient

log = logging.getLogger(__name__)

MSG_TYPE_ERROR = "error"

EVENT_MESSAGE = "message"


class ClientContext:

    def __init__(self, sid):
        self.sid = sid
        self.pending_audio = False
        self.ai = AILocal(self.on_ai_msg, self.on_err)
        self.asr = AsrClient(self.on_asr_result, self.on_err)
        self.tts = TTSClient(self.on_tts_msg, self.on_err)
        self.autoTTS = False

    def close(self):
        self.asr.close()

    def on_asr_result(self, text):
        if text == '':
            return
        msg = {"content": text}
        socketio.emit('msgAsr', msg, room=self.sid)
        self.ai.stream_msg(text)

    def on_ai_msg(self, text, type=0):
        # log.info(f"[AI] ON MSG: {text}")
        if type == 0:
            event = 'msgChat'
            if self.autoTTS:
                self.tts.stream_msg(text)
        else:
            event = 'endChat'
            self.tts.stream_complete()

        socketio.emit(event, {'content': text, 'aiConversationId': self.ai.aiConversationId}, room=self.sid)

    def on_err(self, err: Exception):
        log.error(f"[CHAT] Error: {err}")
        msg = {"type": MSG_TYPE_ERROR, "content": str(err)}
        socketio.emit('error', msg, room=self.sid)

    def on_tts_msg(self, data, type=0):
        if type == 0:
            socketio.emit('dataAudio', {'type': 'tts', 'data': data}, room=self.sid)
        else:
            socketio.emit('endAudio', {'content': data}, room=self.sid)


def translate_text(text):
    return text


class ChatMgr:

    def __init__(self):
        self.clients: dict[str, ClientContext] = {}  # sid -> ClientContext
        self.register_events()

    def add_client(self, sid):
        try:
            self.clients[sid] = ClientContext(sid)
            return self.clients[sid]
        except Exception as e:
            log.error(f"[CHAT] Error adding client {sid}: {e}")

    def remove_client(self, sid):
        if sid in self.clients:
            del self.clients[sid]

    def handle_text(self, sid, text):
        # translated = translate_text(text)
        client: ClientContext = self.clients.get(sid)
        client.ai.stream_msg(text)

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
            if data['key'] != '123456':
                socketio.disconnect(request.sid)
                return {'status': 'rejected'}
            ctx = self.add_client(request.sid)
            ctx.ai.aiConversationId = data.get('aiConversationId', '')
            ctx.ai.user = data.get('user', 'user')
            ctx.autoTTS = data.get('ttsAuto', False)
            ctx.tts.vol = data.get('ttsVol', 50)
            ctx.tts.speed = data.get('ttsSpeed', 1.0)
            log.info(f'[Chat] Client {request.sid} connected. Total clients: {len(self.clients)}, {json.dumps(data)}')

            socketio.emit('handshakeResponse', {'message': 'Handshake successful'}, room=request.sid)
            return {'status': 'connected'}

        # 处理客户端断开连接事件
        @socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            self.remove_client(client_id)
            log.info(f'[CHAT] Client {client_id} disconnected. Total clients: {len(self.clients)}')

        # 处理接收到的消息事件
        @socketio.on(EVENT_MESSAGE)
        def handle_message(msg):
            data = json.loads(msg)
            client_id = request.sid
            data_type = data['type']
            content = data.get('content', '')

            if client_id not in self.clients:
                return
            ctx = self.clients[client_id]
            if data_type == 'text':
                log.info(f'[CHAT] Received message from {client_id}: {data_type}')
                self.handle_text(client_id, content)
            elif data_type == 'audio':
                audio_bytes = base64.b64decode(content)
                self.handle_audio(client_id, data['sample'], audio_bytes)
                cancel = data.get('cancel', False)
                if cancel:
                    ctx.asr.cancel = True
                if data['finish']:
                    ctx.asr.end_asr()

        @socketio.on('tts')
        def handle_tts_request(msg):
            data = json.loads(msg)
            text = data.get('content')
            role = data.get('role', None)
            if not text:
                socketio.emit('error', {'error': 'Missing text'}, room=request.sid)
                return

            client_id = request.sid
            self.clients[client_id].tts.stream_msg(text, role)
            self.clients[client_id].tts.stream_complete()

        @socketio.on('ttsCancel')
        def handle_tts_cancel(msg):
            ctx = self.clients[request.sid]
            ctx.tts.streaming_cancel()
