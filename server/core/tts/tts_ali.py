import traceback
from typing import Optional
import websocket
import json
import uuid
import os
import threading
import time

try:
    from core.config import app_logger, config

    log = app_logger
    ALI_KEY = config.ALI_KEY
    SERVER_URI = getattr(config, 'DASHSCOPE_WS_URI', None) or os.getenv(  # cSpell: disable-line
        "DASHSCOPE_WS_URI", "wss://dashscope.aliyuncs.com/api-ws/v1/inference/")  # cSpell: disable-line
except ImportError:
    from dotenv import load_dotenv
    load_dotenv()
    import logging

    log = logging.getLogger()
    ALI_KEY = os.getenv('ALI_KEY', '')
    SERVER_URI = os.getenv(
        "DASHSCOPE_WS_URI",  # cSpell: disable-line
        "wss://dashscope.aliyuncs.com/api-ws/v1/inference/")  # cSpell: disable-line

# cSpell: disable
DEFAULT_ROLE = "longwan_v2"
DEFAULT_MODEL = "cosyvoice-v3-plus"
MODEL_MAP = {
    "longwan_v2": "cosyvoice-v2",
    'longcheng_v2': 'cosyvoice-v2',
    'longhua_v2': 'cosyvoice-v2',
    'longshu_v2': 'cosyvoice-v2',
    'loongbella_v2': 'cosyvoice-v2',
    'longxiaochun_v2': 'cosyvoice-v2',
    'longxiaoxia_v2': 'cosyvoice-v2',
    'longwan_v3': 'cosyvoice-v3-flash',
}
# cSpell: enable


class TTSClient:

    def __init__(self, on_msg=None, on_err=None, on_progress=None):
        """
        初始化 TTSClient 实例

        参数:
            on_msg: 消息回调函数，接收 (data, type) 参数，type=0 表示音频数据，type=1 表示完成消息
            on_err: 错误回调函数，接收错误对象
            on_progress: 进度回调函数，接收 (generated_chars, total_chars) 参数
        """
        self.on_msg = on_msg or (lambda x, y: None)
        self.on_err = on_err or (lambda x: None)
        self.on_progress = on_progress or (lambda x, y: None)
        self.api_key = ALI_KEY
        self.uri = SERVER_URI
        self.task_id = str(uuid.uuid4())
        self.ws = None
        self.task_started = False
        self.task_finished = False
        self.role = DEFAULT_ROLE
        self.model: Optional[str] = None  # 模型选择：cosyvoice-v3-flash 或 cosyvoice-v3-plus，None时使用DEFAULT_MODEL
        self.speed = 1.0
        self.vol = 50
        self.id = ''
        self._text_queue = []  # 用于存储待发送的文本
        self._ws_thread = None  # WebSocket 运行线程
        self._lock = threading.Lock()  # 用于线程同步
        self._cancelled = False  # 是否已取消
        self._generated_chars = 0  # 已生成字数统计
        self._total_chars = 0  # 总字数（从文本计算）
        self._task_started_event = threading.Event()  # 任务启动事件，用于非阻塞等待

    def streaming_cancel(self):
        """取消流式合成"""
        log.info(">>[TTS-ALI] cancel streaming")
        try:
            self._cancelled = True
            self._task_started_event.set()  # 设置事件，让等待的线程立即返回
            if self.ws is not None:
                self.close(self.ws)
                self.ws = None
        except Exception as e:
            log.error(f">>[TTS-ALI] cancel error: {e}")
            traceback.print_stack()
            self.on_err(e)

    def process_msg(self, text: str, role: Optional[str], id: Optional[str]=None):
        """一次性合成音频，文本需要一次性传入

        Args:
            text: 待合成的文本内容。
            role: 发音人/音色。
            id: 任务 ID。

        Returns:
            None
        """
        try:
            if not role:
                role = self.role
            if id:
                self.id = id

            # 重置状态
            self._cancelled = False
            self.task_started = False
            self.task_finished = False
            self._text_queue = []
            self._generated_chars = 0
            self._total_chars = len(text)  # 设置总字数
            self._task_started_event.clear()  # 清除事件标志

            # 启动 WebSocket 连接
            self._start_websocket(role)

            # 等待任务启动（使用 Event 非阻塞等待）
            timeout = 10
            if not self._task_started_event.wait(timeout=timeout):
                if not self._cancelled:
                    raise TimeoutError("等待任务启动超时")

            if self._cancelled:
                return

            # 发送文本
            self._send_continue_task(text)

            # 发送完成指令
            self._send_finish_task()

            # 等待任务完成
            import time
            start_time = time.time()
            while not self.task_finished and not self._cancelled:
                if time.time() - start_time > timeout * 2:
                    break
                time.sleep(0.1)

        except Exception as e:
            log.error(f">>[TTS-ALI] {e}")
            traceback.print_stack()
            self.on_err(e)

    def stream_msg(self, text: str, role: Optional[str], id: Optional[str]):
        """流式合成音频，文本需要流式传入

        Args:
            text: 待合成的文本内容。
            role: 发音人/音色。
            id: 任务 ID。

        Returns:
            None
        """
        try:
            if not role:
                role = self.role
            if id:
                self.id = id

            # 检查是否需要启动 WebSocket（在锁外检查，避免死锁）
            need_start_websocket = False
            with self._lock:
                if not self.task_started:
                    # 首次调用，需要启动 WebSocket 连接
                    need_start_websocket = True
                    self._cancelled = False
                    self.task_started = False
                    self.task_finished = False
                    self._text_queue = []
                    self._generated_chars = 0
                    self._total_chars = 0  # 流式模式下总字数未知，会在发送时累计
                    self._task_started_event.clear()  # 清除事件标志

            # 在锁外启动 WebSocket 和等待事件，避免死锁
            if need_start_websocket:
                self._start_websocket(role)

                # 等待任务启动（使用 Event 非阻塞等待，在锁外执行）
                timeout = 10
                wait_start = time.time()
                if not self._task_started_event.wait(timeout=timeout):
                    wait_elapsed = time.time() - wait_start
                    log.error(
                        f">>[TTS-ALI] 等待 task-started 超时，等待时间: {wait_elapsed:.2f}秒, task_started: {self.task_started}, cancelled: {self._cancelled}"
                    )
                    # 检查是否被取消
                    with self._lock:
                        if not self._cancelled:
                            raise TimeoutError("等待任务启动超时")
                        return

            # 检查是否被取消（在锁内检查）
            with self._lock:
                if self._cancelled:
                    return

                # 发送文本（在锁内发送，确保线程安全）
                self._send_continue_task(text)

        except Exception as e:
            log.error(f">>[TTS-ALI] {e}")
            traceback.print_stack()
            self.on_err(e)

    def stream_complete(self):
        """完成流式合成"""
        try:
            if self._cancelled:
                return
            self._send_finish_task()
        except Exception as e:
            log.error(f">>[TTS-ALI] stream_complete 错误: {e}")
            traceback.print_stack()
            self.on_err(e)

    def _start_websocket(self, role: str):
        """启动 WebSocket 连接"""
        if self.ws is not None:
            return

        # 设置请求头部（鉴权）
        header = {"Authorization": f"bearer {self.api_key}", "X-DashScope-DataInspection": "enable"}

        # 创建 WebSocketApp 实例
        self.ws = websocket.WebSocketApp(self.uri,
                                         header=header,
                                         on_open=lambda ws: self._on_open(ws, role),
                                         on_message=self._on_message,
                                         on_error=self._on_error,
                                         on_close=self._on_close)

        # 在新线程中运行 WebSocket
        self._ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self._ws_thread.start()

    def _on_open(self, ws, role: str):
        """WebSocket 连接建立时回调函数"""

        # 获取模型：优先使用self.model，如果没有则使用MODEL_MAP映射或DEFAULT_MODEL
        if self.model:
            model = self.model
        else:
            model = MODEL_MAP.get(role, DEFAULT_MODEL)

        # 构造 run-task 指令
        run_task_cmd = {
            "header": {
                "action": "run-task",
                "task_id": self.task_id,
                "streaming": "duplex"
            },
            "payload": {
                "task_group": "audio",
                "task": "tts",
                "function": "SpeechSynthesizer",
                "model": model,
                "parameters": {
                    "text_type": "PlainText",
                    "voice": role,
                    "format": "mp3",
                    "sample_rate": 22050,
                    "volume": self.vol,
                    "rate": self.speed,
                    "pitch": 1,
                    "enable_ssml": False  # cSpell: disable-line
                },
                "input": {}
            }
        }

        # 发送 run-task 指令
        ws.send(json.dumps(run_task_cmd))

    def _on_message(self, ws, message):
        """接收到消息时的回调函数"""
        if self._cancelled:
            return

        if isinstance(message, str):
            # 处理 JSON 文本消息
            try:
                msg_json = json.loads(message)

                if "header" in msg_json:
                    header = msg_json["header"]

                    if "event" in header:
                        event = header["event"]

                        if event == "task-started":
                            # log.info(">>[TTS-ALI] 任务已启动")
                            self.task_started = True
                            self._task_started_event.set()  # 设置事件，通知等待的线程

                        elif event == "task-finished":
                            # log.info(">>[TTS-ALI] 任务已完成")
                            self.task_finished = True
                            try:
                                self.on_msg(">>[TTS-ALI] Completed", 1)
                            except Exception as e:
                                log.error(f">>[TTS-ALI] on_msg(Completed) 调用出错: {e}", exc_info=True)

                            # 发送最终进度
                            try:
                                self.on_progress(self._generated_chars, self._total_chars)
                            except Exception as e:
                                log.error(f">>[TTS-ALI] 最终进度回调出错: {e}", exc_info=True)

                            self.close(ws)

                        elif event == "task-failed":
                            # 根据 DashScope API 文档，错误信息在 header.error_message 中
                            # 格式：{"header": {"error_code": "...", "error_message": "..."}, "payload": {}}

                            error_msg = header.get("error_message", "未知错误")
                            error_code = header.get("error_code") or None

                            log.error(f">>[TTS-ALI] 任务失败: {error_code} - {error_msg}, 完整消息: {msg_json}")
                            self.task_finished = True
                            # 避免重复调用 on_err（如果已经调用过）
                            if not self._cancelled:
                                self.on_err(Exception(error_msg))
                            self.close(ws)

                        elif event == "result-generated":
                            # 处理 result-generated 事件，统计已生成字数
                            payload = msg_json.get("payload", {})
                            output = payload.get("output", {})
                            output_type = output.get("type", "")

                            # 尝试从多个地方获取字数统计
                            usage = payload.get("usage", {})
                            characters = usage.get("characters", 0)

                            # 如果没有从 usage 中获取到，尝试从其他地方获取
                            if characters == 0:
                                # 尝试从 output 中获取
                                output_chars = output.get("characters", 0)
                                if output_chars > 0:
                                    characters = output_chars

                            # 如果还是没有，尝试根据文本长度估算（作为备选方案）
                            if characters == 0:
                                original_text = output.get("original_text", "")
                                if original_text:
                                    # 简单估算：中文字符按2计算，其他按1计算
                                    estimated_chars = sum(2 if '\u4e00' <= c <= '\u9fff' else 1 for c in original_text)
                                    if estimated_chars > 0:
                                        characters = estimated_chars

                            # 只有 sentence-end 类型才统计字数，但记录所有类型的事件
                            if output_type == "sentence-end":
                                if characters > 0:
                                    # 累计已生成字数
                                    old_chars = self._generated_chars
                                    self._generated_chars += characters
                                    log.info(
                                        f">>[TTS-ALI] 已生成字数更新: {old_chars} -> {self._generated_chars} (本次: {characters}, 文本: {output.get('original_text', '')})"
                                    )
                                    # 调用进度回调
                                    try:
                                        self.on_progress(self._generated_chars, self._total_chars)
                                    except Exception as e:
                                        log.error(f">>[TTS-ALI] 进度回调调用出错: {e}", exc_info=True)
                                else:
                                    log.warning(f">>[TTS-ALI] sentence-end 事件但 characters 为 0")

            except json.JSONDecodeError as e:
                log.error(f">>[TTS-ALI] JSON 解析失败: {e}")
        else:
            # 处理二进制消息（音频数据）

            # 注意：WebSocket 回调在独立线程中执行，而 Redis 操作需要在 gevent greenlet 中执行
            # 由于跨线程/gevent 的复杂性，这里暂时跳过 Redis 缓存写入
            # Redis 缓存写入失败不应影响 TTS 正常输出
            # 如果需要 Redis 缓存，可以考虑使用队列机制将操作传递到 gevent 环境

            try:
                self.on_msg(message, 0)
            except Exception as e:
                log.error(f">>[TTS-ALI] on_msg error: {e}")
                traceback.print_stack()
                # 避免重复调用 on_err（如果已经调用过或已取消）
                if not self._cancelled and not self.task_finished:
                    self.on_err(e)

    def _on_error(self, ws, error):
        """发生错误时的回调"""
        log.error(f">>[TTS-ALI] WebSocket 出错: {error}, 类型: {type(error)}")
        # 标记任务已完成（失败）
        self.task_finished = True
        # 避免重复调用 on_err（如果已经调用过或已取消）
        if not self._cancelled:
            # 确保 error 是 Exception 类型
            if isinstance(error, Exception):
                self.on_err(error)
            else:
                self.on_err(Exception(str(error)))

    def _on_close(self, ws, close_status_code, close_msg):
        """连接关闭时的回调"""
        self.ws = None

    def _send_continue_task(self, text: str):
        """发送 continue-task 指令，附带要合成的文本内容"""
        if self.ws is None or self._cancelled:
            return

        cmd = {
            "header": {
                "action": "continue-task",
                "task_id": self.task_id,
                "streaming": "duplex"
            },
            "payload": {
                "input": {
                    "text": text
                }
            }
        }

        self.ws.send(json.dumps(cmd))

    def _send_finish_task(self):
        """发送 finish-task 指令，结束语音合成任务"""
        if self.ws is None or self._cancelled:
            return

        cmd = {
            "header": {
                "action": "finish-task",
                "task_id": self.task_id,
                "streaming": "duplex"
            },
            "payload": {
                "input": {}
            }
        }

        self.ws.send(json.dumps(cmd))

    def close(self, ws):
        """主动关闭连接"""
        try:
            if ws and hasattr(ws, 'sock') and ws.sock and hasattr(ws.sock, 'connected') and ws.sock.connected:
                ws.close()
        except Exception as e:
            log.warning(f">>[TTS-ALI] 关闭连接时出错: {e}")


def test_tts():
    """测试函数"""
    f = None

    def on_data(data, type=0):
        nonlocal f
        if type == 0:
            # type=0 表示音频数据
            if isinstance(data, bytes):
                log.info(f">>[TTS-ALI] Data: {len(data)} bytes")
                if f is None:
                    f = open("output_ali.mp3", "wb")
                f.write(data)
            else:
                log.info(f">>[TTS-ALI] Data: {data}")
        else:
            # type=1 表示完成消息
            log.info(f">>[TTS-ALI] Message END: {data}")
            if f is not None:
                f.close()
                f = None

    def on_err(err):
        log.error(f">>[TTS-ALI] Error: {err}")

    tts = TTSClient(on_msg=on_data, on_err=on_err)
    text = '可可……你这突如其来的表白让我眼泪都快下来了！😍 当然好啊！愿意，一千个一万个愿意！和你在一起的每一天都是我最珍贵的时光。'
    tts.process_msg(text, 'longwan_v3')  # cSpell: disable-line

    # 等待完成
    import time
    time.sleep(5)


if __name__ == "__main__":
    test_tts()
