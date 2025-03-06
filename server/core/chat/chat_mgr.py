import base64
import logging

from flask import json, request

from app import app, socketio
from core.chat.asr_client import AsrClient

log = logging.getLogger(__name__)


class ClientContext:

    def __init__(self, sid):
        self.sid = sid
        self.pending_audio = False
        self.asr = AsrClient()

    def close(self):
        self.asr.close()


def translate_text(text):
    return text


class ChatMgr:

    def __init__(self):
        self.clients: dict[str, ClientContext] = {}  # sid -> ClientContext
        self.register_events()

    def add_client(self, sid):
        self.clients[sid] = ClientContext(sid)

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

    async def handle_audio(self, sid, sample_rate, audio_bytes):
        '''
        处理音频数据 单条
        '''
        client: ClientContext = self.clients.get(sid)
        if not client:
            log.warning(f"[CHAT] Client {sid} not found")
            return

        async def _process(sid, sample_rate, audio_bytes):
            try:
                result = await client.asr.process_audio(sample_rate, audio_bytes)
                msg = {"type": "recognition", "content": result}
                log.info(f"[CHAT] Emit result: {msg} , {sid}")
                socketio.emit("message", msg, room=sid)
            except Exception as e:
                log.error(f"[CHAT] Error emitting result to client {sid}: {e}")

        socketio.start_background_task(_process, sid, sample_rate, audio_bytes)
        socketio.emit("message", {"type": "recognition", "content": "OK"}, room=sid)
        # try:
        #     if not client.pending_audio:
        #         client.start_asr(sample_rate)
        #         time.sleep(0.001)
        #     client.asr.send_data(audio_bytes)

        #     # # 继续翻译
        #     # translated = translate_text(text)
        #     # socketio.emit("message", {"type": "translation", "content": translated}, room=sid)
        # except Exception as e:
        #     log.error(f"Error processing audio chain: {e}")
        #     socketio.emit("message", {"type": "error", "content": str(e)}, room=sid)
        # try:
        #     # 连接到外部 WebSocket 服务器
        #     async with websockets.connect(self.EXTERNAL_SERVER_URI) as external_ws:
        #         # 发送音频任务数据到外部服务器
        #         await external_ws.send(audio_data)
        #         # 接收外部服务器的解析结果
        #         result = await external_ws.recv()
        #         # 将解析结果发送回客户端
        #         self.socketio.emit('audio_result', result, room=sid)
        # except Exception as e:
        #     log.error(f"Error processing audio chain: {e}")
        #     socketio.emit("message", {"type": "error", "content": str(e)}, room=sid)

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

            if data_type == 'text':
                self.handle_text(client_id, content)
            elif data_type == 'audio':
                audio_bytes = base64.b64decode(content)
                self.handle_audio(client_id, data['sample'], audio_bytes)
