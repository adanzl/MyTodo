"""TTS 任务管理服务

提供文本转语音（TTS）的任务管理功能：
- 创建 TTS 任务（文本 -> 语音）
- 启动任务异步生成音频文件
- 任务查询、更新、删除
- 生成的音频文件保存在临时目录：{BASE_TMP_DIR}/tts/{task_id}/output.mp3
- 通过 API 提供文件下载功能
"""

import os
import shutil
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

from core.config import (
    BASE_TMP_DIR,
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_PROCESSING,
    TASK_STATUS_SUCCESS,
    app_logger,
)
from core.services.base_task_mgr import BaseTaskMgr, TaskBase
from core.tts.tts_ali import TTSClient
from core.utils import ensure_directory

log = app_logger

# TTS 任务文件存储基础目录
TTS_BASE_DIR = os.path.join(BASE_TMP_DIR, 'tts')

# 输出音频文件名
OUTPUT_FILENAME = 'output.mp3'

# WebSocket 任务完成等待超时时间（秒）
TASK_COMPLETION_TIMEOUT = 60


@dataclass
class TTSTask(TaskBase):
    """TTS 任务数据模型。

    Attributes:
        text: 待合成的文本内容
        role: 发音人/音色（可选）
        speed: 语速，默认 1.0
        vol: 音量，默认 50
        work_dir: 任务工作目录路径，格式：{BASE_TMP_DIR}/tts/{task_id}
        output_file: 生成的音频文件路径，格式：{work_dir}/output.mp3
    """

    text: str = ''
    role: Optional[str] = None
    speed: float = 1.0
    vol: int = 50

    # 工作目录：{BASE_TMP_DIR}/tts/{task_id}
    work_dir: Optional[str] = None

    # 输出音频文件路径（由任务执行生成）
    output_file: Optional[str] = None


class TTSMgr(BaseTaskMgr[TTSTask]):
    """TTS 任务管理器

    负责文本转语音（TTS）任务的完整生命周期管理：
    1. 创建任务：接收文本和参数，创建任务记录
    2. 执行任务：异步调用 TTS 服务生成音频文件
    3. 文件存储：音频文件保存在临时目录 {BASE_TMP_DIR}/tts/{task_id}/output.mp3
    4. 任务管理：提供查询、更新、删除等功能
    """

    TASK_META_FILE = 'tasks.json'

    def __init__(self) -> None:
        """初始化 TTS 任务管理器。"""
        super().__init__(base_dir=TTS_BASE_DIR)
        # 保存正在运行的 TTS 客户端引用，用于停止任务时取消操作
        self._active_clients: Dict[str, TTSClient] = {}

    def _task_from_dict(self, task_data: Dict[str, Any]) -> TTSTask:
        """从字典创建 TTSTask 对象。"""
        return TTSTask(**task_data)

    def _get_task_dir(self, task_id: str) -> str:
        """获取任务工作目录路径。

        Args:
            task_id: 任务 ID

        Returns:
            任务目录路径：{BASE_TMP_DIR}/tts/{task_id}
        """
        return os.path.join(TTS_BASE_DIR, task_id)

    def _get_output_file_path(self, task_id: str) -> str:
        """获取输出音频文件路径。

        Args:
            task_id: 任务 ID

        Returns:
            音频文件路径：{BASE_TMP_DIR}/tts/{task_id}/output.mp3
        """
        return os.path.join(self._get_task_dir(task_id), OUTPUT_FILENAME)

    def _before_create_task(self, task: TTSTask) -> None:
        """任务创建前的准备工作（由基类调用）。

        注意：此时 task_id 可能还未确定，会在 _create_task_and_save 中最终确定。
        """
        pass

    def create_task(self,
                    text: str,
                    name: Optional[str] = None,
                    role: Optional[str] = None,
                    speed: Optional[float] = None,
                    vol: Optional[int] = None) -> Tuple[int, str, Optional[str]]:
        """创建 TTS 任务。

        创建任务记录并初始化工作目录，不会立即开始生成音频。
        需要调用 start_task() 来启动实际的 TTS 生成过程。

        Args:
            text: 待合成的文本内容（必填）
            name: 任务名称；为空时使用当前时间字符串
            role: 发音人/音色；透传给 TTSClient
            speed: 语速，默认 1.0；透传给 TTSClient
            vol: 音量，默认 50；透传给 TTSClient

        Returns:
            (code, msg, task_id)
            - code: 0 表示成功，-1 表示失败
            - msg: 描述信息
            - task_id: 成功时返回任务 ID，失败时为 None
        """
        # 设置默认任务名称
        name = (name or datetime.now().strftime('%Y-%m-%d %H:%M:%S')).strip()

        # 创建任务对象（允许空文本，可以在创建后编辑）
        task = TTSTask(
            task_id='',  # 将在 _create_task_and_save 中生成
            name=name,
            status=TASK_STATUS_PENDING,
            text=str(text) if text is not None else '',
            role=role,
            speed=float(speed) if speed is not None else 1.0,
            vol=int(vol) if vol is not None else 50,
        )

        # 保存任务并获取 task_id
        code, msg, task_id = self._create_task_and_save(task)
        if code != 0 or not task_id:
            return code, msg, task_id

        # 创建任务工作目录并更新 work_dir
        with self._task_lock:
            task = self._get_task(task_id)
            if task:
                task.work_dir = self._get_task_dir(task_id)
                ensure_directory(task.work_dir)
                self._save_task_and_update_time(task)

        return 0, '任务创建成功', task_id

    def update_task(self,
                    task_id: str,
                    name: Optional[str] = None,
                    text: Optional[str] = None,
                    role: Optional[str] = None,
                    speed: Optional[float] = None,
                    vol: Optional[int] = None) -> Tuple[int, str]:
        """更新 TTS 任务配置。

        注意：任务处于 processing 状态时不允许更新，避免生成过程中配置发生变化。

        Args:
            task_id: 任务 ID
            name: 新任务名称
            text: 新文本内容
            role: 新音色
            speed: 新语速
            vol: 新音量

        Returns:
            (code, msg)
            - code: 0 表示成功，-1 表示失败
            - msg: 描述信息
        """
        # 获取任务
        task, err = self._get_task_or_err(task_id)
        if err:
            return -1, err

        # 检查任务状态
        err = self._ensure_not_processing(task, '更新任务')
        if err:
            return -1, err

        # 更新字段
        updated = False
        if name is not None:
            name = str(name).strip()
            if not name:
                return -1, '任务名称不能为空'
            task.name = name
            updated = True

        if text is not None:
            # 允许文本为空，可以在创建后编辑
            task.text = str(text).strip() if text else ''
            updated = True

        if role is not None:
            task.role = role
            updated = True

        if speed is not None:
            task.speed = float(speed)
            updated = True

        if vol is not None:
            task.vol = int(vol)
            updated = True

        if not updated:
            return -1, '没有提供要更新的字段'

        # 保存更新
        self._save_task_and_update_time(task)
        return 0, '任务更新成功'

    def start_task(self, task_id: str, *args: Any, **kwargs: Any) -> Tuple[int, str]:
        """启动 TTS 任务（异步执行）。

        在后台线程中调用 TTS 服务生成音频文件，保存到任务目录下的 output.mp3。

        Args:
            task_id: 任务 ID

        Returns:
            (code, msg)
            - code: 0 表示成功，-1 表示失败
            - msg: 描述信息
        """
        # 获取任务
        task, err = self._get_task_or_err(task_id)
        if err:
            return -1, err

        # 检查任务状态
        if task.status == TASK_STATUS_PROCESSING:
            return -1, '任务正在处理中'

        # 验证文本内容
        if not task.text or not str(task.text).strip():
            return -1, '文本为空'

        # 异步执行任务（在新线程中运行）
        self._run_task_async(task_id, self._run_tts_task)
        return 0, 'TTS 任务已启动'

    def _update_task_status(self, task_id: str, status: str, error_message: Optional[str] = None) -> None:
        """更新任务状态。
        
        Args:
            task_id: 任务 ID
            status: 新状态
            error_message: 错误消息（可选）
        """
        with self._task_lock:
            task = self._get_task(task_id)
            if task:
                task.status = status
                task.error_message = error_message
                self._save_task_and_update_time(task)

    def _run_task_async(self, task_id: str, runner: Callable[[TTSTask], None]) -> None:
        """在新线程中运行任务。

        Args:
            task_id: 任务 ID
            runner: 任务执行函数
        """

        def wrapped() -> None:
            try:
                # 更新任务状态为处理中
                self._update_task_status(task_id, TASK_STATUS_PROCESSING, None)

                # 获取任务并执行
                with self._task_lock:
                    task = self._get_task(task_id)
                    if not task:
                        return

                runner(task)

                # 任务成功完成（如果状态仍为 processing，则更新为 success）
                with self._task_lock:
                    task = self._get_task(task_id)
                    if task and task.status == TASK_STATUS_PROCESSING:
                        self._update_task_status(task_id, TASK_STATUS_SUCCESS, None)

            except Exception as e:
                log.error(f"[{self.__class__.__name__}] 任务 {task_id} 执行异常: {e}")
                self._update_task_status(task_id, TASK_STATUS_FAILED, str(e))
            finally:
                # 清理停止标志和客户端引用
                self._clear_stop_flag(task_id)
                with self._task_lock:
                    self._active_clients.pop(task_id, None)

        threading.Thread(target=wrapped, daemon=True).start()

    def _run_tts_task(self, task: TTSTask) -> None:
        """执行 TTS 任务的核心逻辑。

        流程：
        1. 确保任务工作目录存在
        2. 设置输出文件路径
        3. 调用 TTSClient 流式生成音频
        4. 将音频数据写入文件
        5. 更新任务状态

        Args:
            task: TTS 任务对象
        """
        # 确保工作目录存在
        if not task.work_dir:
            task.work_dir = self._get_task_dir(task.task_id)
        ensure_directory(task.work_dir)

        # 设置输出文件路径
        output_file = self._get_output_file_path(task.task_id)
        task.output_file = output_file

        # 保存任务信息（包含 output_file 路径）
        with self._task_lock:
            self._save_task_and_update_time(task)

        # 文件句柄（在回调中打开和关闭）
        file_handle = None
        # 任务完成事件（用于等待 WebSocket 任务完成）
        task_completed = threading.Event()

        def on_data(data: Any, data_type: int = 0) -> None:
            """TTS 数据回调：接收音频流数据并写入文件。

            Args:
                data: 音频数据（bytes）或结束标记
                data_type: 0=数据块, 1=结束
            """
            nonlocal file_handle

            # 检查是否被停止（停止是正常操作，静默返回）
            if self._should_stop(task.task_id):
                # 如果收到结束标记，设置完成事件以便主线程退出等待
                if data_type == 1:
                    task_completed.set()
                return

            # 处理数据块
            if data_type == 0:
                if isinstance(data, (bytes, bytearray)):
                    if file_handle is None:
                        file_handle = open(output_file, 'wb')
                    file_handle.write(data)
                return

            # 处理结束标记
            if data_type == 1:
                if file_handle is not None:
                    file_handle.close()
                    file_handle = None
                # 设置任务完成事件（即使没有音频数据也要设置）
                task_completed.set()

        def on_err(err: Exception) -> None:
            """TTS 错误回调：抛出异常以终止任务。"""
            raise err

        # 在执行前检查是否已被停止
        if self._should_stop(task.task_id):
            log.info(f"[TTSMgr] 任务 {task.task_id} 已被停止，跳过执行")
            # 抛出异常以便外层处理任务状态更新
            raise RuntimeError('任务已被停止')

        client = None
        try:
            # 创建 TTS 客户端并设置参数
            # 注意：tts_ali 使用 WebSocket 连接，不依赖 dashscope SDK
            client = TTSClient(on_msg=on_data, on_err=on_err)
            client.speed = task.speed
            client.vol = task.vol

            # 保存客户端引用，以便停止时可以取消
            with self._task_lock:
                self._active_clients[task.task_id] = client

            # 再次检查是否已被停止（在保存引用后）
            if self._should_stop(task.task_id):
                log.info(f"[TTSMgr] 任务 {task.task_id} 已被停止，取消执行")
                raise RuntimeError('任务已被停止')

            # 执行流式合成
            client.stream_msg(text=task.text, role=task.role, id=task.task_id)

            # 在执行 stream_complete 前再次检查停止标志
            if self._should_stop(task.task_id):
                log.info(f"[TTSMgr] 任务 {task.task_id} 已被停止，取消完成操作")
                raise RuntimeError('任务已被停止')

            client.stream_complete()

            # 等待任务完成（WebSocket 会异步返回 task-finished 事件）
            if not task_completed.wait(timeout=TASK_COMPLETION_TIMEOUT):
                log.warning(f"[TTSMgr] 任务 {task.task_id} 等待完成超时（{TASK_COMPLETION_TIMEOUT}秒）")
            else:
                log.debug(f"[TTSMgr] 任务 {task.task_id} 已完成")

            # 更新任务状态为成功
            self._update_task_status(task.task_id, TASK_STATUS_SUCCESS, None)

        except Exception as e:
            # 判断是否为停止操作导致的异常
            is_stopped = self._should_stop(task.task_id) or '停止' in str(e)

            if is_stopped:
                # 停止是正常操作，记录为信息而不是错误
                log.info(f"[TTSMgr] 任务 {task.task_id} 已被停止")
                # 更新任务状态为停止
                with self._task_lock:
                    task = self._get_task(task.task_id)
                    if task:
                        # 如果任务已经被 stop_task 设置为停止状态，则不再更新
                        if task.status == TASK_STATUS_FAILED and task.error_message == '任务已被用户停止':
                            log.debug(f"[TTSMgr] 任务 {task.task_id} 状态已由 stop_task 更新，跳过重复更新")
                        else:
                            # 任务被停止，标记为失败但错误信息明确说明是停止
                            self._update_task_status(task.task_id, TASK_STATUS_FAILED, '任务已被用户停止')
                # 停止操作不重新抛出异常，避免外层再次处理
                return
            else:
                # 其他错误才记录为错误并重新抛出
                log.error(f"[TTSMgr] 任务 {task.task_id} 执行失败: {e}")
                # 更新任务状态
                self._update_task_status(task.task_id, TASK_STATUS_FAILED, str(e))
                raise

        finally:
            # 清理客户端引用
            with self._task_lock:
                self._active_clients.pop(task.task_id, None)

            # 确保文件句柄关闭
            if file_handle is not None:
                try:
                    file_handle.close()
                except Exception:
                    pass

    def stop_task(self, task_id: str) -> Tuple[int, str]:
        """停止正在处理的 TTS 任务。

        该方法会：
        1. 设置停止标志
        2. 调用 TTS 客户端的 streaming_cancel() 方法实际中断操作
        3. 更新任务状态

        Args:
            task_id: 任务 ID

        Returns:
            (code, msg)
            - code: 0 表示成功，-1 表示失败
            - msg: 描述信息
        """
        with self._task_lock:
            task, err = self._get_task_or_err(task_id)
            if err:
                return -1, err
            if task.status != TASK_STATUS_PROCESSING:
                return -1, '任务未在处理中'

            # 设置停止标志
            self._stop_flags[task_id] = True

            # 获取并取消正在运行的 TTS 客户端
            client = self._active_clients.get(task_id)
            if client:
                try:
                    log.info(f"[TTSMgr] 取消任务 {task_id} 的 TTS 流式合成")
                    client.streaming_cancel()
                except Exception as e:
                    log.error(f"[TTSMgr] 取消 TTS 客户端失败 {task_id}: {e}")

            # 立即更新任务状态为失败（已停止）
            task.status = TASK_STATUS_FAILED
            task.error_message = '任务已被用户停止'
            self._save_task_and_update_time(task)

            return 0, '任务已停止'

    def _should_request_stop_before_delete(self, _task: TTSTask) -> bool:
        """删除处理中的任务时，是否先请求停止。

        Returns:
            True：删除前先请求停止任务
        """
        return True

    def _after_delete_task(self, task_id: str) -> None:
        """任务删除后的清理工作：删除任务工作目录及其所有文件。

        Args:
            task_id: 任务 ID
        """
        task_dir = self._get_task_dir(task_id)
        if not os.path.isdir(task_dir):
            return

        try:
            shutil.rmtree(task_dir)
            log.debug(f"[TTSMgr] 已删除任务目录: {task_dir}")
        except Exception as e:
            log.warning(f"[TTSMgr] 删除任务目录失败 {task_id}: {e}")

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息。

        Args:
            task_id: 任务 ID

        Returns:
            任务字典（包含所有任务字段）；任务不存在时返回 None
        """
        task = self._get_task(task_id)
        return asdict(task) if task else None

    def get_output_file_path(self, task_id: str) -> Optional[str]:
        """获取任务的输出音频文件路径。

        Args:
            task_id: 任务 ID

        Returns:
            音频文件路径；任务不存在或文件不存在时返回 None
        """
        task = self._get_task(task_id)
        if not task:
            return None

        # 优先使用任务中保存的路径
        if task.output_file and os.path.exists(task.output_file):
            return task.output_file

        # 否则尝试默认路径
        default_path = self._get_output_file_path(task_id)
        if os.path.exists(default_path):
            return default_path

        return None


tts_mgr = TTSMgr()
