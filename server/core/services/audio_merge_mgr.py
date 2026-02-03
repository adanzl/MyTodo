"""
音频合成管理服务
提供音频文件合并等功能
"""
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from core.services.base_task_mgr import BaseTaskMgr, FileInfo, TaskBase

from core.config import app_logger
from core.config import (ALLOWED_AUDIO_EXTENSIONS, MEDIA_BASE_DIR, FFMPEG_PATH, FFMPEG_TIMEOUT, get_media_task_dir,
                         get_media_task_result_dir, TASK_STATUS_PENDING, TASK_STATUS_PROCESSING, TASK_STATUS_SUCCESS,
                         TASK_STATUS_FAILED)

from core.utils import ensure_directory as ensure_directory, get_media_duration, run_subprocess_safe

# 音频合并任务目录（任务存档和最终文件保存在 base 目录）
AUDIO_MERGE_BASE_DIR = os.path.join(MEDIA_BASE_DIR, 'merge')

log = app_logger

AudioFileItem = FileInfo


@dataclass
class AudioMergeTask(TaskBase):
    """音频合成任务"""
    files: List[AudioFileItem]
    result_file: Optional[str] = None  # 结果文件路径
    result_duration: Optional[float] = None  # 结果文件时长（秒）


class AudioMergeMgr(BaseTaskMgr[AudioMergeTask]):
    """音频合成管理器"""

    TASK_META_FILE = 'tasks.json'  # 任务元数据文件名
    MERGED_FILENAME = 'merged.mp3'  # 合并后的文件名
    FFMPEG_DURATION_TIMEOUT = 10  # 获取文件时长的超时时间（秒）

    # 编译正则表达式以提高性能
    _DURATION_PATTERN = re.compile(r'Duration:\s*(\d{2}):(\d{2}):(\d{2})\.(\d{2})')

    def __init__(self) -> None:
        """初始化管理器"""
        super().__init__(base_dir=AUDIO_MERGE_BASE_DIR)

    def _task_from_dict(self, data: dict) -> AudioMergeTask:
        return AudioMergeTask(**data)

    def _validate_task_exists(self, task_id: str) -> Tuple[Optional[AudioMergeTask], Optional[str]]:
        return self._get_task_or_err(task_id)

    def _validate_task_not_processing(self, task: AudioMergeTask, operation: str) -> Optional[str]:
        if task.status == TASK_STATUS_PROCESSING:
            return f"任务正在处理中，无法{operation}"
        return None

    def _read_tasks_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(file_path):
            return None
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def _validate_file(self, file_path: str, filename: str) -> Optional[str]:
        """验证文件是否存在且类型受支持。

        Args:
            file_path (str): 文件的绝对路径。
            filename (str): 文件名，用于检查扩展名。

        Returns:
            Optional[str]: 如果文件无效，返回错误消息，否则返回 None。
        """
        if not os.path.exists(file_path):
            return f"文件不存在: {file_path}"

        _, ext = os.path.splitext(filename)
        if ext.lower() not in ALLOWED_AUDIO_EXTENSIONS:
            return f"不支持的文件类型: {ext}"

        return None

    def _update_file_indices(self, files: List[Dict[str, Any]]) -> None:
        """更新文件列表的索引"""
        for i, file_info in enumerate(files):
            file_info['index'] = i

    def _load_history_tasks(self) -> None:
        """加载历史任务"""
        super()._load_history_tasks()

        with self._task_lock.gen_wlock():
            tasks_to_remove = []
            for task_id, task in self._tasks.items():
                try:
                    task_dir = get_media_task_dir(task_id)
                    if not os.path.exists(task_dir):
                        log.warning(f"[AudioMerge] 任务目录不存在: {task_id}")
                        tasks_to_remove.append(task_id)
                        continue

                    # 重建文件列表（检查文件是否存在）
                    valid_files = []
                    for file_info in task.files:
                        if not file_info.get('path') or not os.path.exists(file_info['path']):
                            continue
                        valid_files.append(file_info)

                    # 更新文件索引
                    for i, file_info in enumerate(valid_files):
                        file_info['index'] = i

                    task.files = valid_files

                    # 检查结果文件是否存在
                    if task.result_file and not os.path.exists(task.result_file):
                        task.result_file = None
                        task.result_duration = None

                except Exception as e:
                    log.error(f"[AudioMerge] 校验任务 {task_id} 文件失败: {e}")
                    tasks_to_remove.append(task_id)

            # 移除无效任务
            for task_id in tasks_to_remove:
                self._tasks.pop(task_id, None)

            if tasks_to_remove:
                self._save_all_tasks()
                log.info(f"[AudioMerge] 清理了 {len(tasks_to_remove)} 个无效任务")

    def _before_create_task(self, task: AudioMergeTask) -> None:
        task_dir = get_media_task_dir(task.task_id)
        result_dir = get_media_task_result_dir(task.task_id)
        os.makedirs(task_dir, exist_ok=True)
        os.makedirs(result_dir, exist_ok=True)

    def create_task(self, name: Optional[str] = None) -> Tuple[int, str, Optional[str]]:
        name = name or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task = AudioMergeTask(task_id='', name=name, files=[])
        return self._create_task_and_save(task)

    def add_file(self, task_id: str, file_path: str, filename: str) -> Tuple[int, str]:
        """向指定任务添加一个音频文件。

        Args:
            task_id (str): 任务 ID。
            file_path (str): 文件的绝对路径。
            filename (str): 文件名。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示成功。
        """
        try:
            task, error_msg = self._get_task_or_err(task_id)
            if error_msg:
                return -1, error_msg

            error_msg = self._ensure_not_processing(task, "添加文件")
            if error_msg:
                return -1, error_msg

            error_msg = self._validate_file(file_path, filename)
            if error_msg:
                return -1, error_msg

            # 获取文件时长
            duration = get_media_duration(file_path)

            # 添加到文件列表
            file_info = {
                'name': filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'duration': duration,  # 时长（秒）
                'index': len(task.files)
            }
            task.files.append(file_info)
            self._save_task_and_update_time(task)

            log.info(f"[AudioMerge] 添加文件到任务 {task_id}: {filename}")
            return 0, "文件添加成功"

        except Exception as e:
            error_msg = f"添加文件失败: {str(e)}"
            log.error(f"[AudioMerge] {error_msg}")
            return -1, error_msg

    def remove_file(self, task_id: str, file_index: int) -> Tuple[int, str]:
        """从指定任务中移除一个音频文件。

        Args:
            task_id (str): 任务 ID。
            file_index (int): 要移除文件的索引。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示成功。
        """
        try:
            task, error_msg = self._get_task_or_err(task_id)
            if error_msg:
                return -1, error_msg

            error_msg = self._ensure_not_processing(task, "删除文件")
            if error_msg:
                return -1, error_msg

            if file_index < 0 or file_index >= len(task.files):
                return -1, "文件索引无效"

            removed_file = task.files.pop(file_index)
            self._update_file_indices(task.files)
            self._save_task_and_update_time(task)

            log.info(f"[AudioMerge] 从任务 {task_id} 移除文件: {removed_file['name']}")
            return 0, "文件移除成功"

        except Exception as e:
            error_msg = f"移除文件失败: {str(e)}"
            log.error(f"[AudioMerge] {error_msg}")
            return -1, error_msg

    def reorder_files(self, task_id: str, file_indices: List[int]) -> Tuple[int, str]:
        """调整任务中文件的顺序。

        Args:
            task_id (str): 任务 ID。
            file_indices (List[int]): 表示新顺序的文件索引列表。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示成功。
        """
        try:
            task, error_msg = self._get_task_or_err(task_id)
            if error_msg:
                return -1, error_msg

            error_msg = self._ensure_not_processing(task, "调整文件顺序")
            if error_msg:
                return -1, error_msg

            if len(file_indices) != len(task.files):
                return -1, f"文件索引数量不匹配，期望 {len(task.files)} 个，实际 {len(file_indices)} 个"

            if set(file_indices) != set(range(len(task.files))):
                return -1, "文件索引无效，必须包含所有文件的索引"

            # 重新排序文件列表
            task.files = [task.files[i] for i in file_indices]
            self._update_file_indices(task.files)
            self._save_task_and_update_time(task)

            log.info(f"[AudioMerge] 调整任务 {task_id} 的文件顺序")
            return 0, "文件顺序调整成功"

        except Exception as e:
            error_msg = f"调整文件顺序失败: {str(e)}"
            log.error(f"[AudioMerge] {error_msg}")
            return -1, error_msg

    def start_task(self, task_id: str) -> Tuple[int, str]:
        """开始音频合并任务。

        此方法会启动一个后台线程来执行 ffmpeg 合并操作。

        Args:
            task_id (str): 任务 ID。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示成功。
        """
        try:
            task, error_msg = self._get_task_or_err(task_id)
            if error_msg:
                return -1, error_msg

            if task.status == TASK_STATUS_PROCESSING:
                return -1, "任务正在处理中"

            if len(task.files) == 0:
                return -1, "任务中没有文件"

            def runner(t: AudioMergeTask) -> None:
                result_file, result_duration = self._merge_audio_files(task_id, t.files)
                if result_file:
                    t.result_file = result_file
                    if result_duration is None:
                        try:
                            result_duration = get_media_duration(result_file)
                        except Exception as e:
                            log.warning(f"[AudioMerge] 任务 {task_id} 获取结果文件时长失败: {e}")
                    t.result_duration = result_duration
                    log.info(f"[AudioMerge] 任务 {task_id} 合成成功: {result_file}, 时长: {t.result_duration}秒")
                else:
                    t.status = TASK_STATUS_FAILED
                    t.error_message = "合成失败"
                    t.result_duration = None
                    log.error(f"[AudioMerge] 任务 {task_id} 合成失败")

            self._run_task_async(task_id, runner)
            return 0, "任务已开始处理"

        except Exception as e:
            error_msg = f"启动任务失败: {str(e)}"
            log.error(f"[AudioMerge] {error_msg}")
            return -1, error_msg

    def _parse_duration_from_ffmpeg_output(self, output: str) -> Optional[float]:
        """
        从 ffmpeg 输出中解析时长
        
        :param output: ffmpeg 的输出文本
        :return: 时长（秒），解析失败返回 None
        """
        match = self._DURATION_PATTERN.search(output)
        if match:
            hours, minutes, seconds, centiseconds = map(int, match.groups())
            return hours * 3600 + minutes * 60 + seconds + centiseconds / 100.0
        return None

    def _get_file_duration_with_ffmpeg(self, file_path: str) -> Optional[float]:
        """
        使用 ffmpeg 快速获取文件时长
        
        :param file_path: 文件路径
        :return: 时长（秒），失败返回 None
        """
        try:
            cmds = [FFMPEG_PATH, '-loglevel', 'error', '-i', file_path, '-f', 'null', '-']
            # 使用公共方法安全地运行 subprocess，避免 gevent 与 asyncio 冲突
            try:
                _, _, stderr = run_subprocess_safe(cmds, timeout=self.FFMPEG_DURATION_TIMEOUT)
            except (TimeoutError, FileNotFoundError, Exception):
                return None
            # ffmpeg 会将信息输出到 stderr
            return self._parse_duration_from_ffmpeg_output(stderr)
        except Exception as e:
            log.warning(f"[AudioMerge] 使用 ffmpeg 获取文件时长失败 {file_path}: {e}")
            return None

    def _get_result_duration(self, result_file: str, fallback_duration: Optional[float] = None) -> Optional[float]:
        """
        获取结果文件时长，优先使用后备时长，否则使用 ffmpeg 获取
        
        :param result_file: 结果文件路径
        :param fallback_duration: 后备时长（如果提供则直接返回）
        :return: 时长（秒），失败返回 None
        """
        if fallback_duration is not None:
            return fallback_duration
        return self._get_file_duration_with_ffmpeg(result_file)

    def _merge_audio_files(self, task_id: str, files: List[AudioFileItem]) -> Tuple[Optional[str], Optional[float]]:
        """使用 ffmpeg 合并音频文件。

        如果只有一个文件，则直接复制。否则，使用 ffmpeg 的 concat demuxer 合并。

        Args:
            task_id (str): 任务 ID。
            files (List[AudioFileItem]): 待合并的文件列表。

        Returns:
            Tuple[Optional[str], Optional[float]]: (结果文件路径, 时长秒)，失败则返回 (None, None)。
        """
        if not files:
            return None, None

        try:
            result_dir = get_media_task_result_dir(task_id)
            result_file = os.path.join(result_dir, self.MERGED_FILENAME)

            # 如果只有一个文件，直接复制
            if len(files) == 1:
                shutil.copy2(files[0]['path'], result_file)
                duration = self._get_result_duration(result_file, files[0].get('duration'))
                return result_file, duration

            # 创建文件列表文件（用于 ffmpeg concat）
            file_list_path = os.path.join(get_media_task_dir(task_id), 'file_list.txt')
            with open(file_list_path, 'w', encoding='utf-8') as f:
                for file_info in files:
                    file_path = file_info['path'].replace("'", "'\\''")
                    f.write(f"file '{file_path}'\n")

            # 使用 ffmpeg 合并
            cmds = [
                FFMPEG_PATH, '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', file_list_path, '-c', 'copy',
                '-y', result_file
            ]

            log.info(f"[AudioMerge] 执行 ffmpeg 命令: {' '.join(cmds)}")
            # 使用公共方法安全地运行 subprocess，避免 gevent 与 asyncio 冲突
            try:
                returncode, _, stderr = run_subprocess_safe(cmds, timeout=FFMPEG_TIMEOUT)
            except TimeoutError:
                log.error(f"[AudioMerge] ffmpeg 执行超时")
                return None, None
            except Exception as e:
                log.error(f"[AudioMerge] ffmpeg 执行失败: {e}")
                return None, None

            if returncode == 0 and os.path.exists(result_file):
                # 从 ffmpeg 输出中解析时长，如果失败则使用 ffmpeg 快速获取
                duration = self._parse_duration_from_ffmpeg_output(stderr)
                duration = self._get_result_duration(result_file, duration)
                return result_file, duration

            error_msg = stderr if returncode != 0 else '文件不存在'
            log.error(f"[AudioMerge] ffmpeg 执行失败: {error_msg}")
            return None, None

        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            log.error(f"[AudioMerge] ffmpeg 执行失败: {e}")
            return None, None
        except Exception as e:
            log.error(f"[AudioMerge] 合并音频文件失败: {e}")
            return None, None

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取指定任务的详细信息。

        Args:
            task_id (str): 任务 ID。

        Returns:
            Optional[Dict[str, Any]]: 任务信息字典，如果任务不存在则返回 None。
        """
        task = self._get_task(task_id)
        if not task:
            return None

        # 如果有结果文件但没有时长，则补全时长
        if task.result_file and task.result_duration is None and os.path.exists(task.result_file):
            try:
                task.result_duration = self._get_result_duration(task.result_file)
                if task.result_duration is not None:
                    self._save_task_and_update_time(task)
                    log.info(f"[AudioMerge] 任务 {task_id} 补全结果文件时长: {task.result_duration}秒")
            except Exception as e:
                log.warning(f"[AudioMerge] 任务 {task_id} 补全结果文件时长失败: {e}")

        return asdict(task)

    def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有音频合并任务。

        Returns:
            List[Dict[str, Any]]: 任务信息字典的列表，按创建时间倒序排列。
        """
        tasks = [asdict(task) for task in self._tasks.values()]
        # 按创建时间倒序排序，最新的在上面
        tasks.sort(key=lambda x: x.get('create_time', 0), reverse=True)
        return tasks

    def _before_delete_task(self, task: AudioMergeTask) -> None:
        task_dir = get_media_task_dir(task.task_id)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)


# 创建全局实例
audio_merge_mgr = AudioMergeMgr()
