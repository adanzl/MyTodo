import base64
import time

from core.ai.ai_local import AILocal
from core.chat.asr_client import AsrClient
from core.tts.tts_client import TTSClient
from core.log_config import root_logger
from flask import json, request
import core.db.rds_mgr as rds_mgr

log = root_logger

MSG_TYPE_ERROR = "error"

EVENT_MESSAGE = "message"


class ClientContext:

    def __init__(self, sid, socketio):
        self.sid = sid
        self.pending_audio = False
        self.ai = AILocal(self.on_ai_msg, self.on_err)
        self.asr = AsrClient(self.on_asr_result, self.on_err)  # 语音识别
        self.tts = TTSClient(self.on_tts_msg, self.on_err)  # 语音合成
        self.autoTTS = False
        self.socketio = socketio

    def close(self):
        self.asr.close()

    def on_asr_result(self, text):
        '''
            处理asr的返回消息，收到消息后转发给ai和客户端
        '''
        if text == '':
            return
        msg = {"content": text}
        self.socketio.emit('msgAsr', msg, room=self.sid)
        self.ai.stream_msg(text)

    def on_ai_msg(self, text, id, type=0):
        '''
            处理AI的回复消息
        '''
        # log.info(f"[AI] ON MSG: {text}")
        if type == 0:
            event = 'msgChat'
            if self.autoTTS:
                self.tts.stream_msg(text=text, id=id)
        else:
            event = 'endChat'
            self.tts.stream_complete()

        self.socketio.emit(event, {
            'content': text,
            'aiConversationId': self.ai.aiConversationId,
            'id': id
        },
                           room=self.sid)

    def on_err(self, err: Exception):
        log.error(f"[CHAT] Error: {err}")
        msg = {"type": MSG_TYPE_ERROR, "content": str(err)}
        self.socketio.emit('error', msg, room=self.sid)

    def on_tts_msg(self, data, type=0):
        '''
            处理tts的返回消息，type=0正常的流式返回，type=1表示tts已经结束的消息
        '''
        if type == 0:
            self.socketio.emit('dataAudio', {'type': 'tts', 'data': data}, room=self.sid)
        else:
            self.socketio.emit('endAudio', {'content': data}, room=self.sid)


def translate_text(text):
    return text


class ChatMgr:

    def __init__(self):
        self.clients: dict[str, ClientContext] = {}  # sid -> ClientContext

    def init(self, socketio):
        log.info("[CHAT] ChatMgr init")
        self.socketio = socketio
        self._register_events()

    def add_client(self, sid):
        try:
            self.clients[sid] = ClientContext(sid, self.socketio)
            return self.clients[sid]
        except Exception as e:
            log.error(f"[CHAT] Error adding client {sid}: {e}")

    def remove_client(self, sid):
        if sid in self.clients:
            del self.clients[sid]

    def handle_text(self, sid, data):
        chat_type = data.get('chatType', '')
        content = data.get('content', '')
        if chat_type == 'chat_room':
            room_id = data.get('roomId', '')
            user_id = data.get('userId', '')
            msg_data = {
                'user_id': user_id,
                'content': content,
                'type': 'text',
                'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
                'chat_type': chat_type,
            }
            rds_mgr.rpush("chat:" + room_id, json.dumps(msg_data, ensure_ascii=False))
            for client in self.clients.values():
                if client.sid != sid:
                    log.info(f"[CHAT] Emitting [msgChat] to client {client.sid} msg {content}")
                    self.socketio.emit('msgChat', msg_data, room=client.sid)
            self.socketio.emit('endChat', {}, room=sid)

        else:
            client: ClientContext = self.clients.get(sid)
            client.ai.stream_msg(content)

    def handle_audio(self, sid, sample_rate, audio_bytes, room_id):
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

    def _register_events(self):
        # 处理客户端连接事件
        @self.socketio.on('handshake')
        def handle_handshake(data):
            if data['key'] != '123456':
                self.socketio.disconnect(request.sid)
                return {'status': 'rejected'}
            ctx = self.add_client(request.sid)
            ctx.ai.aiConversationId = data.get('aiConversationId', '')
            ctx.ai.user = data.get('user', 'user')
            ctx.autoTTS = data.get('ttsAuto', False)
            ctx.tts.vol = data.get('ttsVol', 50)
            ctx.tts.speed = data.get('ttsSpeed', 1.0)
            log.info(f'[CHAT] Client {request.sid} connected. Total clients: {len(self.clients)}, {json.dumps(data)}')

            self.socketio.emit('handshakeResponse', {'message': 'Handshake successful'}, room=request.sid)
            return {'message': 'Handshake successful', 'status': 'ok'}

        # 处理客户端断开连接事件
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            self.remove_client(client_id)
            log.info(f'[CHAT] Client {client_id} disconnected. Total clients: {len(self.clients)}')

        # 处理接收到的消息事件
        @self.socketio.on(EVENT_MESSAGE)
        def handle_message(msg):
            data = json.loads(msg)
            client_id = request.sid
            data_type = data['type']
            chat_type = data.get('chatType', '')
            content = data.get('content', '')
            room_id = data.get('roomId', '')

            if client_id not in self.clients:
                return
            ctx = self.clients[client_id]
            if data_type == 'text':
                log.info(f'[CHAT] Received message from {client_id}: {data_type}, {chat_type} {content}')
                self.handle_text(client_id, data)
            elif data_type == 'audio':
                audio_bytes = base64.b64decode(content)
                self.handle_audio(client_id, data['sample'], audio_bytes, room_id)
                cancel = data.get('cancel', False)
                if cancel:
                    ctx.asr.cancel = True
                if data['finish']:
                    ctx.asr.end_asr()
            else:
                log.warning(f'[CHAT] Unknown message type: {data_type}')

        # 处理TTS请求
        @self.socketio.on('tts')
        def handle_tts_request(msg):
            data = json.loads(msg)
            text = data.get('content')
            role = data.get('role', None)
            id = data.get('id', '')
            if not text:
                self.socketio.emit('error', {'error': 'Missing text'}, room=request.sid)
                return

            client_id = request.sid
            key = f"audio:{id}:{role}"
            if rds_mgr.exists(key):
                data = rds_mgr.get(key)
                chunk_size = 3000
                for i in range(0, len(data), chunk_size):
                    chunk = data[i:i + chunk_size]
                    self.socketio.emit('dataAudio', {'type': 'tts', 'data': chunk}, room=client_id)
                self.socketio.emit('endAudio', {'content': data}, room=client_id)
            else:
                self.clients[client_id].tts.stream_msg(text, role, id)
                self.clients[client_id].tts.stream_complete()

        @self.socketio.on('ttsCancel')
        def handle_tts_cancel(msg):
            ctx = self.clients[request.sid]
            ctx.tts.streaming_cancel()

        @self.socketio.on('chatCancel')
        def handle_chat_cancel():
            ctx = self.clients[request.sid]
            ctx.ai.streaming_cancel()

        @self.socketio.on('config')
        def handle_chat_config(data):
            log.info(f'[CHAT] Config: {data}')
            ctx = self.clients[request.sid]
            if 'aiConversationId' in data:
                ctx.ai.aiConversationId = data['aiConversationId']
            if 'user' in data:
                ctx.ai.user = data['user']
            if 'ttsAuto' in data:
                ctx.autoTTS = data['ttsAuto']
            if 'ttsVol' in data:
                ctx.tts.vol = data['ttsVol']
            if 'ttsSpeed' in data:
                ctx.tts.speed = data['ttsSpeed']


chat_mgr = ChatMgr()
