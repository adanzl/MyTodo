"""Alibaba Cloud Model Studio streaming ASR client.

The public interface intentionally matches the existing local ``AsrClient`` so
chat_mgr can switch providers without changing the browser protocol.  Only a
completed cloud task emits ``on_result``; intermediate/final-per-sentence
results are accumulated and never trigger the LLM early.
"""

import json
import threading
import uuid

import websocket

from core.chat.asr_client import AsrClient, _AsrSession
from core.config import app_logger, config

log = app_logger


class AliyunAsrClient(AsrClient):
    """Qwen-Audio/Fun-ASR realtime client over DashScope WebSocket."""

    def __init__(self, on_result=None, on_err=None):
        super().__init__(on_result, on_err)
        self._audio_lock = threading.Lock()
        self._task_id = ''
        self._finish_requested = False
        self._finish_sent = False
        self._final_sentences: dict[int, str] = {}

    @staticmethod
    def _language_hints() -> list[str]:
        raw = config.ASR_ALIYUN_LANGUAGE_HINTS or ''
        return [item.strip() for item in raw.split(',') if item.strip()][:4]

    @staticmethod
    def _vocabulary() -> dict[str, int]:
        raw = (config.ASR_ALIYUN_VOCABULARY or '').strip()
        if not raw or raw == '{}':
            return {}
        try:
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError('vocabulary must be a JSON object')
            result: dict[str, int] = {}
            for word, weight in value.items():
                weight = int(weight)
                if weight not in {1, 2, 3, 4, 5, 50}:
                    raise ValueError(f'invalid hotword weight for {word!r}: {weight}')
                result[str(word)] = weight
            return result
        except Exception as exc:
            log.warning('[ASR-ALIYUN] ignore invalid ASR_ALIYUN_VOCABULARY: %s', exc)
            return {}

    def _run_task_message(self) -> str:
        parameters: dict = {
            'format': 'pcm',
            'sample_rate': self.sample_rate,
        }
        if config.ASR_ALIYUN_VAD_MODEL:
            parameters['vad_model'] = config.ASR_ALIYUN_VAD_MODEL
        language_hints = self._language_hints()
        if language_hints:
            parameters['language_hints'] = language_hints
        vocabulary = self._vocabulary()
        if vocabulary:
            parameters['vocabulary'] = vocabulary

        input_obj: dict = {}
        context = (config.ASR_ALIYUN_CONTEXT or '').strip()
        if context:
            input_obj['context'] = [
                {
                    'role': 'user',
                    'content': [{'type': 'input_text', 'text': context}],
                }
            ]

        return json.dumps(
            {
                'header': {
                    'action': 'run-task',
                    'task_id': self._task_id,
                    'streaming': 'duplex',
                },
                'payload': {
                    'task_group': 'audio',
                    'task': 'asr',
                    'function': 'recognition',
                    'model': config.ASR_ALIYUN_MODEL,
                    'parameters': parameters,
                    'input': input_obj,
                },
            },
            ensure_ascii=False,
        )

    def _finish_task_message(self) -> str:
        return json.dumps(
            {
                'header': {
                    'action': 'finish-task',
                    'task_id': self._task_id,
                    'streaming': 'duplex',
                },
                'payload': {'input': {}},
            },
            ensure_ascii=False,
        )

    def _flush_audio_buffer(self) -> None:
        if not self.is_running or self.ws is None:
            return
        with self._audio_lock:
            if not self.buffer:
                return
            data = bytes(self.buffer)
            self.buffer.clear()
        self.ws.send_bytes(data)

    def _send_finish_task(self) -> None:
        if self._finish_sent or not self.is_running or self.ws is None:
            return
        self._finish_sent = True
        self.ws.send(self._finish_task_message())
        log.info('>>[ASR-ALIYUN] finish-task %s', self._task_id)

    def end_asr(self):
        self._finish_requested = True
        self._flush_audio_buffer()
        self._send_finish_task()

    def _make_on_open(self, ws_generation: int):
        def on_open(ws):
            if ws_generation != self._ws_generation:
                log.info('>>[ASR-ALIYUN] ignore stale ws open')
                return
            session = self._sessions_by_generation.get(ws_generation)
            if session is None or session.cancelled:
                return
            try:
                ws.send(self._run_task_message())
                log.info(
                    '>>[ASR-ALIYUN] run-task model=%s sample_rate=%s request=%s',
                    config.ASR_ALIYUN_MODEL,
                    self.sample_rate,
                    session.request_id,
                )
            except Exception as exc:
                log.error('>>[ASR-ALIYUN] open error: %s', exc)
                self.on_err(exc)

        return on_open

    def _make_on_message(self, ws_generation: int):
        def on_message(ws, msg):
            if ws_generation != self._ws_generation:
                log.info('>>[ASR-ALIYUN] ignore stale ws message')
                return
            session = self._sessions_by_generation.get(ws_generation)
            if session is None or session.cancelled or session.ws_generation != ws_generation:
                log.info('>>[ASR-ALIYUN] ignore result for cancelled or stale session')
                return
            try:
                data = json.loads(msg)
                header = data.get('header') or {}
                event = header.get('event') or ''
                task_id = header.get('task_id') or ''
                if task_id and task_id != self._task_id:
                    log.info('>>[ASR-ALIYUN] ignore stale task %s', task_id)
                    return

                if event == 'task-started':
                    self.is_running = True
                    self._flush_audio_buffer()
                    if self._finish_requested:
                        self._send_finish_task()
                    return

                if event == 'result-generated':
                    sentence = (((data.get('payload') or {}).get('output') or {}).get('sentence') or {})
                    if sentence.get('heartbeat'):
                        return
                    if sentence.get('sentence_end'):
                        text = (sentence.get('text') or '').strip()
                        if text:
                            sentence_id = int(sentence.get('sentence_id') or 0)
                            self._final_sentences[sentence_id] = text
                    return

                if event == 'task-finished':
                    self.is_running = False
                    text = ''.join(
                        self._final_sentences[key]
                        for key in sorted(self._final_sentences)
                    ).strip()
                    log.info('>>[ASR-ALIYUN] task-finished request=%s text=%s', session.request_id, text)
                    if text:
                        self.on_result(text, session.request_id)
                    self.close()
                    return

                if event == 'task-failed':
                    self.is_running = False
                    code = header.get('error_code') or 'UNKNOWN'
                    message = header.get('error_message') or 'ASR task failed'
                    self.on_err(RuntimeError(f'Aliyun ASR {code}: {message}'))
                    return
            except Exception as exc:
                log.error('[ASR-ALIYUN] message error: %s', exc)
                self.on_err(exc)

        return on_message

    def _make_on_error(self, ws_generation: int):
        def on_error(ws, error):
            if ws_generation != self._ws_generation:
                return
            log.error('>>[ASR-ALIYUN] websocket error: %s', error)
            self.on_err(error if isinstance(error, Exception) else RuntimeError(str(error)))

        return on_error

    def _make_on_close(self, ws_generation: int):
        def on_close(ws, close_status_code, close_msg):
            if ws_generation != self._ws_generation:
                return
            log.info('>>[ASR-ALIYUN] close %s %s', close_status_code, close_msg)
            with self._audio_lock:
                self.buffer.clear()
            self.ws = None
            self.is_running = False

        return on_close

    def connect(self, sid, sample_rate):
        self.sid = sid
        self.sample_rate = sample_rate
        self._ws_generation += 1
        ws_generation = self._ws_generation
        rid = self._next_session_request_id
        if not rid and self._session and not self._session.cancelled:
            rid = self._session.request_id
        self._next_session_request_id = ''
        session = _AsrSession(request_id=rid or '', ws_generation=ws_generation)
        self._session = session
        self._sessions_by_generation[ws_generation] = session

        self._task_id = str(uuid.uuid4())
        self._finish_requested = False
        self._finish_sent = False
        self._final_sentences = {}

        api_key = (config.ASR_ALIYUN_API_KEY or '').strip()
        if not api_key:
            self.on_err(RuntimeError('ASR_PROVIDER=aliyun but ASR_ALIYUN_API_KEY/ALI_KEY is empty'))
            return

        headers = [
            f'Authorization: Bearer {api_key}',
            'User-Agent: my-todo-asr/1.0',
        ]
        workspace_id = (config.ASR_ALIYUN_WORKSPACE_ID or '').strip()
        if workspace_id:
            headers.append(f'X-DashScope-WorkSpace: {workspace_id}')

        self.ws = websocket.WebSocketApp(
            config.ASR_ALIYUN_SERVER,
            header=headers,
            on_open=self._make_on_open(ws_generation),
            on_message=self._make_on_message(ws_generation),
            on_error=self._make_on_error(ws_generation),
            on_close=self._make_on_close(ws_generation),
        )
        thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        thread.start()

    def process_audio(self, sample_rate, audio_data, sid):
        with self._audio_lock:
            self.buffer.extend(audio_data)
        if self.ws is None:
            self.connect(sid, sample_rate)
        self._flush_audio_buffer()
