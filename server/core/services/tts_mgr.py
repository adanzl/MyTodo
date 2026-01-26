"""TTS 任务管理服务

提供文本转语音（TTS）的任务管理功能：
- 创建 TTS 任务（文本 -> 语音）
- 启动任务异步生成音频文件
- 任务查询、更新、删除
- OCR 图片文字识别（将结果追加到任务文本末尾）
- 生成的音频文件保存在：{DEFAULT_BASE_DIR}/tasks/tts/{task_id}/output.mp3
- 通过 API 提供文件下载功能
"""

import os
import shutil
import threading
import time
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

from core.config import (
    DEFAULT_BASE_DIR,
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_PROCESSING,
    TASK_STATUS_SUCCESS,
    app_logger,
)
from core.services.base_task_mgr import BaseTaskMgr, TaskBase
from core.tools.async_util import run_in_background
from core.tts.tts_ali import TTSClient
from core.utils import cleanup_temp_files, ensure_directory, get_media_duration

# 延迟导入 OCR 客户端，避免循环依赖
_ocr_client = None


def _get_ocr_client():
    """获取 OCR 客户端实例（延迟导入）。"""
    global _ocr_client
    if _ocr_client is None:
        from core.ai.ocr_ali import OCRAli
        _ocr_client = OCRAli()
    return _ocr_client

log = app_logger

# TTS 任务文件存储基础目录（任务存档和最终文件保存在 base 目录）
TTS_BASE_DIR = os.path.join(DEFAULT_BASE_DIR, 'tasks', 'tts')

# 输出音频文件名
OUTPUT_FILENAME = 'output.mp3'

# WebSocket 任务完成等待超时时间（秒）
TASK_COMPLETION_TIMEOUT = 600


def count_text_chars(text: str) -> int:
    """统计文本字数。
    
    统计规则：
    - 汉字（包括简/繁体汉字、日文汉字和韩文汉字）按2个字符计算
    - 其他所有字符（如标点符号、字母、数字、日韩文假名/谚文等）均按1个字符计算
    
    Args:
        text: 待统计的文本
        
    Returns:
        统计后的字符数
    """
    if not text:
        return 0

    count = 0
    # 汉字Unicode范围：
    # \u4e00-\u9fff: CJK统一汉字（中文、日文、韩文常用汉字）
    # \u3400-\u4dbf: CJK扩展A（更多汉字）
    # \uac00-\ud7a3: 韩文音节（包含韩文汉字）
    # \uf900-\ufaff: CJK兼容汉字
    # 使用正则表达式匹配汉字
    hanzi_pattern = re.compile(
        r'[\u4e00-\u9fff\u3400-\u4dbf\uac00-\ud7a3\uf900-\ufaff]')

    for char in text:
        if hanzi_pattern.match(char):
            count += 2  # 汉字按2个字符计算
        else:
            count += 1  # 其他字符按1个字符计算

    return count


@dataclass
class TTSTask(TaskBase):
    """TTS 任务数据模型。

    Attributes:
        text: 待合成的文本内容
        role: 发音人/音色（可选）
        speed: 语速，默认 0.8
        vol: 音量，默认 50
        work_dir: 任务工作目录路径，格式：{BASE_TMP_DIR}/tts/{task_id}
        output_file: 生成的音频文件路径，格式：{work_dir}/output.mp3
        generated_chars: 已生成字数（实时更新）
        total_chars: 文本总字数（按统计规则计算）
        duration: 音频时长（秒），任务完成后写入
    """

    text: str = ''
    role: Optional[str] = None
    speed: float = 0.8
    vol: int = 50

    # 工作目录：{BASE_TMP_DIR}/tts/{task_id}
    work_dir: Optional[str] = None

    # 输出音频文件路径（由任务执行生成）
    output_file: Optional[str] = None

    # 已生成字数统计（实时更新）
    generated_chars: int = 0

    # 文本总字数（按统计规则计算：汉字2个字符，其他1个字符）
    total_chars: int = 0

    # 音频时长（秒），任务完成后写入
    duration: Optional[float] = None


class TTSMgr(BaseTaskMgr[TTSTask]):
    """TTS 任务管理器

    负责文本转语音（TTS）任务的完整生命周期管理：
    1. 创建任务：接收文本和参数，创建任务记录
    2. 执行任务：异步调用 TTS 服务生成音频文件
    3. 文件存储：音频文件保存在 {DEFAULT_BASE_DIR}/tasks/tts/{task_id}/output.mp3
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
            任务目录路径：{DEFAULT_BASE_DIR}/tasks/tts/{task_id}
        """
        return os.path.join(TTS_BASE_DIR, task_id)

    def _get_output_file_path(self, task_id: str) -> str:
        """获取输出音频文件路径。

        Args:
            task_id: 任务 ID

        Returns:
            音频文件路径：{DEFAULT_BASE_DIR}/tasks/tts/{task_id}/output.mp3
        """
        return os.path.join(self._get_task_dir(task_id), OUTPUT_FILENAME)

    def _before_create_task(self, task: TTSTask) -> None:
        """任务创建前的准备工作（由基类调用）。

        注意：此时 task_id 可能还未确定，会在 _create_task_and_save 中最终确定。
        """
        pass

    def create_task(
            self,
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
            speed: 语速，默认 0.8；透传给 TTSClient
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
            speed=float(speed) if speed is not None else 0.8,
            vol=int(vol) if vol is not None else 50,
        )

        # 计算文本总字数
        task.total_chars = count_text_chars(task.text)

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
            # 更新文本时重新计算总字数
            task.total_chars = count_text_chars(task.text)
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

    def start_task(self, task_id: str, *args: Any,
                   **kwargs: Any) -> Tuple[int, str]:
        """启动 TTS 任务（异步执行）。

        在后台线程中调用 TTS 服务生成音频文件，保存到任务目录下的 output.mp3。

        Args:
            task_id: 任务 ID

        Returns:
            (code, msg)
            - code: 0 表示成功，-1 表示失败
            - msg: 描述信息
        """
        # log.info(f"[TTSMgr] 收到启动任务请求，task_id: {task_id}")

        # 获取任务
        task, err = self._get_task_or_err(task_id)
        if err:
            log.warning(f"[TTSMgr] 启动任务失败，task_id: {task_id}, 错误: {err}")
            return -1, err

        # 检查任务状态
        if task.status == TASK_STATUS_PROCESSING:
            log.warning(f"[TTSMgr] 启动任务失败，task_id: {task_id}, 原因: 任务正在处理中")
            return -1, '任务正在处理中'

        # 验证文本内容
        if not task.text or not str(task.text).strip():
            log.warning(f"[TTSMgr] 启动任务失败，task_id: {task_id}, 原因: 文本为空")
            return -1, '文本为空'

        log.info(
            f"[TTSMgr] 准备启动任务 {task_id}, 任务名称: {task.name}, 文本长度: {len(task.text)} 字符"
        )

        # 清除停止标志（如果存在），允许重新开始
        self._clear_stop_flag(task_id)

        # 清理旧的客户端引用（如果存在）
        with self._task_lock:
            self._active_clients.pop(task_id, None)
            # 重置已生成字数统计
            task.generated_chars = 0
            self._save_task_and_update_time(task)

        # 异步执行任务（在新线程中运行）
        # log.info(f"[TTSMgr] 任务 {task_id} 已提交到后台线程执行")
        self._run_task_async(task_id, self._run_tts_task)
        return 0, 'TTS 任务已启动'

    def _update_task_status(self,
                            task_id: str,
                            status: str,
                            error_message: Optional[str] = None) -> None:
        """更新任务状态。
        
        注意：此方法内部会获取锁，调用者不应在持有锁的情况下调用此方法。
        
        Args:
            task_id: 任务 ID
            status: 新状态
            error_message: 错误消息（可选）
        """
        with self._task_lock:
            task = self._get_task(task_id)
            if task:
                old_status = task.status
                task.status = status
                task.error_message = error_message
                try:
                    self._save_task_and_update_time(task)
                except Exception as e:
                    log.error(f"[TTSMgr] 保存任务状态时出错: {e}", exc_info=True)
                    raise
                if old_status != status:
                    log.info(
                        f"[TTSMgr] 任务 {task_id} 状态更新: {old_status} -> {status}"
                        + (f", 错误: {error_message}" if error_message else ""))
            else:
                log.warning(f"[TTSMgr] _update_task_status 无法找到任务: {task_id}")

    def _run_task_async(self, task_id: str, runner: Callable[[TTSTask],
                                                             None]) -> None:
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

                # 注意：runner 内部已经更新了状态，这里不需要再次更新
                # 只需要检查状态是否正确
                with self._task_lock:
                    task = self._get_task(task_id)
                    if not task:
                        log.warning(f"[TTSMgr] 任务 {task_id} 执行完成但无法找到任务记录")

            except Exception as e:
                log.error(
                    f"[{self.__class__.__name__}] 任务 {task_id} 执行异常: {e}")
                self._update_task_status(task_id, TASK_STATUS_FAILED, str(e))
            finally:
                # 清理停止标志和客户端引用
                self._clear_stop_flag(task_id)
                with self._task_lock:
                    self._active_clients.pop(task_id, None)

        run_in_background(wrapped)

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
        task_start_time = time.time()

        # log.info(f"[TTSMgr] 开始执行 TTS 任务 {task.task_id}, 任务名称: {task.name}")
        log.info(
            f"[TTSMgr] Start {task.name} - 文本长度: {len(task.text)} 字符,  {task.role or '默认'}, 语速: {task.speed}, 音量: {task.vol}"
        )

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
        # 错误信息（用于在回调中传递错误）
        error_info = {'error': None}
        # 已生成字数统计
        generated_chars = 0
        # 音频数据统计
        audio_data_size = 0
        audio_chunk_count = 0
        # 最后一次接收到数据的时间（用于超时检测）
        last_data_time = [time.time()]  # 使用列表以便在回调中修改

        def on_data(data: Any, data_type: int = 0) -> None:
            """TTS 数据回调：接收音频流数据并写入文件。

            Args:
                data: 音频数据（bytes）或结束标记
                data_type: 0=数据块, 1=结束
            """
            nonlocal file_handle, audio_data_size, audio_chunk_count
            # 更新最后一次接收到数据的时间
            last_data_time[0] = time.time()

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
                        # 确保输出文件目录存在
                        output_dir = os.path.dirname(output_file)
                        if output_dir:
                            ensure_directory(output_dir)
                        file_handle = open(output_file, 'wb')
                    file_handle.write(data)
                    audio_data_size += len(data)
                    audio_chunk_count += 1
                else:
                    log.warning(f"[TTSMgr] 收到非字节数据: {type(data)}")
                return

            # 处理结束标记
            if data_type == 1:
                if file_handle is not None:
                    file_handle.close()
                    file_handle = None
                    log.info(
                        f"[TTSMgr] 任务 {task.name} 音频文件写入完成，总大小: {audio_data_size} 字节 ({audio_chunk_count} 个数据块)"
                    )
                # 设置任务完成事件（即使没有音频数据也要设置）
                task_completed.set()

        def on_err(err: Exception) -> None:
            """TTS 错误回调：记录错误并设置完成事件。"""
            # 记录错误信息
            error_info['error'] = err
            log.error(f"[TTSMgr] TTS 客户端错误回调: {err}")
            # 设置任务完成事件，让主线程退出等待
            task_completed.set()

        def on_progress(generated: int, total: int) -> None:
            """TTS 进度回调：更新已生成字数统计。
            
            Args:
                generated: 已生成字数
                total: 总字数（可能为0，表示未知）
            """
            nonlocal generated_chars
            # 更新最后一次接收到数据的时间
            last_data_time[0] = time.time()
            generated_chars = generated
            # log.info(f"[TTSMgr] 任务 {task.task_id} 进度更新: {generated}/{total if total > 0 else '?'} 字")

            # 更新任务中的已生成字数
            try:
                with self._task_lock:
                    current_task = self._get_task(task.task_id)
                    if current_task:
                        current_task.generated_chars = generated
                        # 只更新时间，不保存到文件（避免频繁IO）
                        current_task.update_time = datetime.now().timestamp()
                    else:
                        log.warning(f"[TTSMgr] 进度回调中无法找到任务 {task.task_id}")
            except Exception as e:
                log.error(f"[TTSMgr] 更新任务字数时出错: {e}", exc_info=True)

        # 在执行前检查是否已被停止
        if self._should_stop(task.task_id):
            log.info(f"[TTSMgr] 任务 {task.task_id} 已被停止，跳过执行")
            # 抛出异常以便外层处理任务状态更新
            raise RuntimeError('任务已被停止')

        client = None
        try:
            # 创建 TTS 客户端并设置参数
            # 注意：tts_ali 使用 WebSocket 连接，不依赖 dashscope SDK
            client = TTSClient(on_msg=on_data,
                               on_err=on_err,
                               on_progress=on_progress)
            client.speed = task.speed
            client.vol = task.vol

            # 计算总字数（用于进度显示）
            total_chars = len(task.text)
            client._total_chars = total_chars

            # 保存客户端引用，以便停止时可以取消
            with self._task_lock:
                self._active_clients[task.task_id] = client

            # 再次检查是否已被停止（在保存引用后）
            if self._should_stop(task.task_id):
                log.info(f"[TTSMgr] 任务 {task.task_id} 已被停止，取消执行")
                raise RuntimeError('任务已被停止')

            # 执行流式合成：按行分割文本，逐行发送
            text_lines = task.text.split('\n')
            # 过滤空行
            text_lines = [line.strip() for line in text_lines if line.strip()]

            if not text_lines:
                log.warning(f"[TTSMgr] 任务 {task.task_id} 文本为空，跳过合成")
                return

            # 逐行发送文本
            # log.info(f"[TTSMgr] 任务 {task.task_id} 开始流式发送文本，共 {len(text_lines)} 行")
            for i, line in enumerate(text_lines, 1):
                # 检查是否被停止
                if self._should_stop(task.task_id):
                    log.info(
                        f"[TTSMgr] 任务 {task.task_id} 已被停止，已发送 {i-1}/{len(text_lines)} 行"
                    )
                    raise RuntimeError('任务已被停止')

                try:
                    client.stream_msg(text=line,
                                      role=task.role,
                                      id=task.task_id)
                except Exception as e:
                    log.error(f"[TTSMgr] 发送第 {i} 行时出错: {e}", exc_info=True)
                    raise

            log.info(
                f"[TTSMgr] 任务 {task.task_id} 文本发送完成，共发送 {len(text_lines)} 行")

            # 在执行 stream_complete 前再次检查停止标志
            if self._should_stop(task.task_id):
                log.info(f"[TTSMgr] 任务 {task.task_id} 已被停止，取消完成操作")
                raise RuntimeError('任务已被停止')

            try:
                client.stream_complete()
            except Exception as e:
                log.error(f"[TTSMgr] stream_complete 调用出错: {e}", exc_info=True)
                raise

            # 等待任务完成（WebSocket 会异步返回 task-finished 事件）
            log.info(
                f"[TTSMgr] 任务 {task.name} 开始等待 WebSocket 任务完成（数据接收超时: 10秒）"
            )
            # 初始化最后一次接收到数据的时间（从发送完成时开始计时）
            last_data_time[0] = time.time()
            DATA_TIMEOUT = 10.0  # 10秒没有收到数据则视为超时

            while not task_completed.is_set():
                # 检查是否10秒没有收到数据
                time_since_last_data = time.time() - last_data_time[0]
                if time_since_last_data >= DATA_TIMEOUT:
                    log.warning(
                        f"[TTSMgr] 任务 {task.task_id} 数据接收超时，距离最后一次接收数据已过去: {time_since_last_data:.2f}秒（超时限制: {DATA_TIMEOUT}秒）"
                    )
                    # 超时也视为失败
                    raise TimeoutError(f"任务数据接收超时（{DATA_TIMEOUT}秒未收到数据）")

                # 使用短超时进行轮询，以便定期检查
                task_completed.wait(timeout=1.0)

            # 检查是否有错误发生
            if error_info['error'] is not None:
                # 有错误发生，抛出异常以便外层处理
                raise error_info['error']

            task_elapsed = time.time() - task_start_time
            log.info(
                f"[TTSMgr] 任务 {task.task_id} 执行成功，已生成字数: {generated_chars}/{task.total_chars}, 总耗时: {task_elapsed:.2f}秒"
            )

            # 获取音频文件时长
            audio_duration = None
            if output_file and os.path.exists(output_file):
                try:
                    duration_seconds = get_media_duration(output_file)
                    if duration_seconds is not None:
                        audio_duration = float(duration_seconds)
                        log.info(
                            f"[TTSMgr] 任务 {task.task_id} 音频时长: {audio_duration:.2f}秒"
                        )
                    else:
                        log.warning(f"[TTSMgr] 任务 {task.task_id} 无法获取音频时长")
                except Exception as e:
                    log.warning(f"[TTSMgr] 任务 {task.task_id} 获取音频时长失败: {e}")

            # 更新任务状态为成功，并保存最终字数统计和音频时长
            # 注意：不要在锁内调用 _update_task_status，因为它内部已经有锁了
            final_task = None
            try:
                with self._task_lock:
                    final_task = self._get_task(task.task_id)
                    if final_task:
                        final_task.generated_chars = generated_chars
                        final_task.duration = audio_duration
                        # 直接更新状态和保存，避免嵌套锁
                        final_task.status = TASK_STATUS_SUCCESS
                        final_task.error_message = None
                        self._save_task_and_update_time(final_task)
                    else:
                        log.warning(f"[TTSMgr] 无法找到任务 {task.task_id} 进行最终更新")
            except Exception as e:
                log.error(f"[TTSMgr] 更新任务状态时出错: {e}", exc_info=True)
                raise

        except Exception as e:
            task_elapsed = time.time() - task_start_time
            # 判断是否为停止操作导致的异常
            is_stopped = self._should_stop(task.task_id) or '停止' in str(e)

            if is_stopped:
                # 停止是正常操作，记录为信息而不是错误
                log.info(
                    f"[TTSMgr] 任务 {task.task_id} 已被停止，耗时: {task_elapsed:.2f}秒")
                # 更新任务状态为停止
                with self._task_lock:
                    task = self._get_task(task.task_id)
                    if task:
                        # 如果任务已经被 stop_task 设置为停止状态，则不再更新
                        if task.status == TASK_STATUS_FAILED and task.error_message == '任务已被用户停止':
                            pass  # 状态已更新，跳过
                        else:
                            # 任务被停止，标记为失败但错误信息明确说明是停止
                            self._update_task_status(task.task_id,
                                                     TASK_STATUS_FAILED,
                                                     '任务已被用户停止')
                # 停止操作不重新抛出异常，避免外层再次处理
                return
            else:
                # 其他错误才记录为错误并重新抛出
                log.error(
                    f"[TTSMgr] 任务 {task.task_id} 执行失败，耗时: {task_elapsed:.2f}秒，错误: {e}",
                    exc_info=True)
                # 更新任务状态
                self._update_task_status(task.task_id, TASK_STATUS_FAILED,
                                         str(e))
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
        log.info(f"[TTSMgr] 收到停止任务请求，task_id: {task_id}")

        with self._task_lock:
            task, err = self._get_task_or_err(task_id)
            if err:
                log.warning(f"[TTSMgr] 停止任务失败，task_id: {task_id}, 错误: {err}")
                return -1, err
            if task.status != TASK_STATUS_PROCESSING:
                log.warning(
                    f"[TTSMgr] 停止任务失败，task_id: {task_id}, 原因: 任务未在处理中（当前状态: {task.status}）"
                )
                return -1, '任务未在处理中'

            log.info(
                f"[TTSMgr] 开始停止任务 {task_id}, 任务名称: {task.name}, 已生成字数: {task.generated_chars}/{task.total_chars}"
            )

            # 设置停止标志
            self._stop_flags[task_id] = True

            # 获取并取消正在运行的 TTS 客户端
            client = self._active_clients.get(task_id)
            if client:
                try:
                    log.info(f"[TTSMgr] 取消任务 {task_id} 的 TTS 流式合成")
                    client.streaming_cancel()
                except Exception as e:
                    log.error(f"[TTSMgr] 取消 TTS 客户端失败 {task_id}: {e}",
                              exc_info=True)
            else:
                log.warning(f"[TTSMgr] 任务 {task_id} 没有活动的 TTS 客户端")

            # 立即更新任务状态为失败（已停止）
            task.status = TASK_STATUS_FAILED
            task.error_message = '任务已被用户停止'
            self._save_task_and_update_time(task)

            log.info(f"[TTSMgr] 任务 {task_id} 已成功停止")
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
        if not task:
            return None
        
        # 如果任务状态为成功但没有duration，异步获取并更新
        if task.status == TASK_STATUS_SUCCESS and task.duration is None:
            output_file = self.get_output_file_path(task_id)
            if output_file and os.path.exists(output_file):
                # 异步获取duration并更新存档
                self._update_duration_async(task_id, output_file)
        
        return asdict(task)

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

    def _update_duration_async(self, task_id: str, output_file: str) -> None:
        """异步获取音频文件时长并更新任务存档。

        Args:
            task_id: 任务 ID
            output_file: 音频文件路径
        """
        def update_duration() -> None:
            try:
                duration_seconds = get_media_duration(output_file)
                if duration_seconds is not None:
                    audio_duration = float(duration_seconds)
                    with self._task_lock:
                        task = self._get_task(task_id)
                        if task and task.status == TASK_STATUS_SUCCESS:
                            # 只有在任务仍然是成功状态时才更新
                            task.duration = audio_duration
                            self._save_task_and_update_time(task)
                            log.info(f"[TTSMgr] 异步更新任务 {task_id} 音频时长: {audio_duration:.2f}秒")
                else:
                    log.warning(f"[TTSMgr] 异步获取任务 {task_id} 音频时长失败：无法获取时长")
            except Exception as e:
                log.warning(f"[TTSMgr] 异步获取任务 {task_id} 音频时长失败: {e}")

        # 在后台线程中执行
        run_in_background(update_duration)

    def start_ocr_task(self, task_id: str, image_paths: list[str],
                       temp_dir: str) -> Tuple[int, str]:
        """启动 OCR 任务（异步执行）。
        
        将 OCR 识别结果自动追加到指定 TTS 任务的文本末尾。
        开始 OCR 后，TTS 任务进入处理中状态；OCR 完成后，结果追加到文本末尾，任务状态恢复为待处理。
        
        Args:
            task_id: 任务 ID
            image_paths: 图片路径列表
            temp_dir: 临时文件目录路径（用于清理）
        
        Returns:
            (code, msg)
            - code: 0 表示成功，-1 表示失败
            - msg: 描述信息
        """
        # 验证任务存在
        task, err = self._get_task_or_err(task_id)
        if err:
            log.warning(f"[TTSMgr] 启动 OCR 任务失败，task_id: {task_id}, 错误: {err}")
            return -1, err
        
        # 检查任务状态，如果正在处理中，不允许OCR
        if task.status == TASK_STATUS_PROCESSING:
            log.warning(
                f"[TTSMgr] 启动 OCR 任务失败，task_id: {task_id}, 原因: 任务正在处理中"
            )
            return -1, '任务正在处理中，无法执行 OCR'
        
        if not image_paths:
            return -1, '图片路径列表为空'
        
        log.info(
            f"[TTSMgr] 准备启动 OCR 任务 {task_id}, 任务名称: {task.name}, 图片数量: {len(image_paths)}"
        )
        
        # 创建 OCR 任务执行函数（包装器，符合 _run_task_async 的签名）
        def ocr_runner(task: TTSTask) -> None:
            """OCR 任务执行函数（包装器）。"""
            self._run_ocr_task_logic(task_id, image_paths, temp_dir)
        
        # 使用统一的异步任务执行方法
        self._run_task_async(task_id, ocr_runner)
        
        return 0, 'OCR 任务已启动'

    def _append_text_to_task(self, task_id: str, new_text: str) -> Tuple[int, str]:
        """将文本追加到任务的现有文本末尾。
        
        Args:
            task_id: 任务 ID
            new_text: 要追加的新文本
        
        Returns:
            (code, msg) 更新结果
        """
        with self._task_lock:
            task = self._get_task(task_id)
            if not task:
                return -1, 'TTS 任务不存在'
            
            # 将结果追加到现有文本末尾
            current_text = task.text or ''
            combined_text = f"{current_text}\n\n{new_text}" if current_text else new_text
        
        # 先将状态设置为pending，以便可以更新文本（update_task不允许processing状态下更新）
        self._update_task_status(task_id, TASK_STATUS_PENDING, None)
        
        # 更新任务文本
        return self.update_task(task_id=task_id, text=combined_text)
    
    def _restore_task_to_pending(self, task_id: str, error_msg: str = None) -> None:
        """恢复任务状态为待处理（用于错误恢复）。
        
        Args:
            task_id: 任务 ID
            error_msg: 错误消息（可选，用于日志记录）
        """
        self._update_task_status(task_id, TASK_STATUS_PENDING, None)
        if error_msg:
            log.error(f"[TTSMgr] OCR 任务 {task_id} 失败: {error_msg}")
    
    def _run_ocr_task_logic(self, task_id: str, image_paths: list[str],
                            temp_dir: str) -> None:
        """执行 OCR 任务的核心逻辑。
        
        注意：此方法由 _run_task_async 调用，状态管理由 _run_task_async 处理。
        此方法只负责 OCR 业务逻辑，不负责状态更新（除了将状态恢复为 pending）。
        
        Args:
            task_id: 任务 ID
            image_paths: 图片路径列表
            temp_dir: 临时文件目录路径
        """
        try:
            log.info(
                f"[TTSMgr] 开始 OCR 任务 {task_id}，图片数量: {len(image_paths)}")
            
            # 调用 OCR 服务
            ocr_client = _get_ocr_client()
            status, result = ocr_client.query(image_paths)
            
            if status == "error":
                # OCR 失败，恢复任务状态为待处理（不抛出异常，避免 _run_task_async 设置为失败）
                self._restore_task_to_pending(task_id, result or 'OCR 识别失败')
                return
            
            # OCR 成功，追加文本到任务
            code, msg = self._append_text_to_task(task_id, result)
            if code != 0:
                # 更新失败，恢复任务状态为待处理
                self._restore_task_to_pending(task_id, f"更新文本失败: {msg}")
                return
            
            log.info(
                f"[TTSMgr] OCR 任务 {task_id} 完成，追加文本长度: {len(result)} 字符"
            )
            # 注意：状态已经在 _append_text_to_task 中设置为 pending，不需要再次设置
            
        except Exception as e:
            # 发生异常，恢复任务状态为待处理（不重新抛出，避免 _run_task_async 设置为失败）
            self._restore_task_to_pending(task_id, f"处理异常: {e}")
            log.error(
                f"[TTSMgr] OCR 任务 {task_id} 处理异常: {e}", exc_info=True)
        finally:
            # 清理临时文件
            cleanup_temp_files(temp_dir, image_paths)


tts_mgr = TTSMgr()
