"""
音频合成管理服务
提供音频文件合并等功能
"""
import json
import os
import random
import re
import shutil
import string
import subprocess
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.config import app_logger
from core.config import (ALLOWED_AUDIO_EXTENSIONS, MEDIA_BASE_DIR, FFMPEG_PATH, FFMPEG_TIMEOUT,
                               get_media_task_dir, get_media_task_result_dir, TASK_STATUS_PENDING,
                               TASK_STATUS_PROCESSING, TASK_STATUS_SUCCESS, TASK_STATUS_FAILED)
from core.utils import get_media_duration, ensure_directory, run_subprocess_safe

log = app_logger


@dataclass
class AudioMergeTask:
    """音频合成任务"""
    task_id: str
    name: str
    status: str  # pending, processing, success, failed
    files: List[Dict]  # 文件列表，每个文件包含 name, path, size 等信息
    result_file: Optional[str] = None  # 结果文件路径
    result_duration: Optional[float] = None  # 结果文件时长（秒）
    error_message: Optional[str] = None  # 错误信息
    create_time: float = 0  # 创建时间戳
    update_time: float = 0  # 更新时间戳


class AudioMergeMgr:
    """音频合成管理器"""

    TASK_META_FILE = 'task.json'  # 任务元数据文件名
    MERGED_FILENAME = 'merged.mp3'  # 合并后的文件名
    FFMPEG_DURATION_TIMEOUT = 10  # 获取文件时长的超时时间（秒）

    # 编译正则表达式以提高性能
    _DURATION_PATTERN = re.compile(r'Duration:\s*(\d{2}):(\d{2}):(\d{2})\.(\d{2})')

    def __init__(self):
        """初始化管理器"""
        # 确保媒体任务目录存在
        ensure_directory(MEDIA_BASE_DIR)
        self._tasks: Dict[str, AudioMergeTask] = {}
        self._load_history_tasks()

    def _get_task(self, task_id: str) -> Optional[AudioMergeTask]:
        """获取任务对象，不存在返回 None"""
        return self._tasks.get(task_id)

    def _validate_task_exists(self, task_id: str) -> Tuple[Optional[AudioMergeTask], Optional[str]]:
        """
        验证任务是否存在
        
        :return: (任务对象, 错误消息)，如果任务不存在则返回 (None, 错误消息)
        """
        task = self._get_task(task_id)
        if not task:
            return None, "任务不存在"
        return task, None

    def _validate_task_not_processing(self, task: AudioMergeTask, operation: str) -> Optional[str]:
        """
        验证任务是否不在处理中
        
        :param task: 任务对象
        :param operation: 操作名称
        :return: 错误消息，如果验证通过返回 None
        """
        if task.status == TASK_STATUS_PROCESSING:
            return f"任务正在处理中，无法{operation}"
        return None

    def _validate_file(self, file_path: str, filename: str) -> Optional[str]:
        """
        验证文件
        
        :param file_path: 文件路径
        :param filename: 文件名
        :return: 错误消息，如果验证通过返回 None
        """
        if not os.path.exists(file_path):
            return f"文件不存在: {file_path}"

        _, ext = os.path.splitext(filename)
        if ext.lower() not in ALLOWED_AUDIO_EXTENSIONS:
            return f"不支持的文件类型: {ext}"

        return None

    def _update_file_indices(self, files: List[Dict]):
        """更新文件列表的索引"""
        for i, file_info in enumerate(files):
            file_info['index'] = i

    def _update_task_time(self, task: AudioMergeTask):
        """更新任务的更新时间"""
        task.update_time = datetime.now().timestamp()

    def _save_task_and_update_time(self, task: AudioMergeTask):
        """更新任务时间并保存"""
        self._update_task_time(task)
        self._save_all_tasks()

    def _load_history_tasks(self):
        """加载历史任务"""
        try:
            if not os.path.exists(MEDIA_BASE_DIR):
                return

            task_meta_file = os.path.join(MEDIA_BASE_DIR, self.TASK_META_FILE)
            if not os.path.exists(task_meta_file):
                return

            with open(task_meta_file, 'r', encoding='utf-8') as f:
                all_tasks_data = json.load(f)

            if not isinstance(all_tasks_data, dict):
                log.warning("[AudioMerge] task.json 格式错误，应为字典格式")
                return

            loaded_count = 0
            for task_id, task_data in all_tasks_data.items():
                try:
                    task_dir = get_media_task_dir(task_id)
                    if not os.path.exists(task_dir):
                        log.warning(f"[AudioMerge] 任务目录不存在: {task_id}")
                        continue

                    # 重建文件列表（检查文件是否存在）
                    files = [
                        file_info for file_info in task_data.get('files', [])
                        if file_info.get('path') and os.path.exists(file_info.get('path'))
                    ]

                    # 检查结果文件是否存在
                    result_file = task_data.get('result_file')
                    if result_file and not os.path.exists(result_file):
                        result_file = None

                    # 创建任务对象
                    task = AudioMergeTask(task_id=task_id,
                                          name=task_data.get('name', '未命名任务'),
                                          status=task_data.get('status', TASK_STATUS_PENDING),
                                          files=files,
                                          result_file=result_file,
                                          result_duration=task_data.get('result_duration'),
                                          error_message=task_data.get('error_message'),
                                          create_time=task_data.get('create_time', 0),
                                          update_time=task_data.get('update_time', 0))

                    self._tasks[task_id] = task
                    loaded_count += 1

                except Exception as e:
                    log.error(f"[AudioMerge] 加载任务失败 {task_id}: {e}")
                    continue

            log.info(f"[AudioMerge] 共加载 {loaded_count} 个历史任务")

        except json.JSONDecodeError as e:
            log.error(f"[AudioMerge] 解析 task.json 失败: {e}")
        except Exception as e:
            log.error(f"[AudioMerge] 加载历史任务失败: {e}")

    def _save_all_tasks(self):
        """保存所有任务到统一的 task.json 文件"""
        try:
            task_meta_file = os.path.join(MEDIA_BASE_DIR, self.TASK_META_FILE)
            os.makedirs(MEDIA_BASE_DIR, exist_ok=True)

            all_tasks_data = {task_id: asdict(task) for task_id, task in self._tasks.items()}

            with open(task_meta_file, 'w', encoding='utf-8') as f:
                json.dump(all_tasks_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            log.error(f"[AudioMerge] 保存所有任务失败: {e}")

    def _generate_task_id(self) -> str:
        """生成短任务ID"""
        timestamp = int(datetime.now().timestamp())
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"{timestamp}{random_str}"

    def create_task(self, name: Optional[str] = None) -> Tuple[int, str, Optional[str]]:
        """
        创建音频合成任务
        
        :param name: 任务名称，如果为 None 则使用默认日期时间
        :return: (错误码, 消息, 任务ID)，0 表示成功
        """
        try:
            # 如果没有提供名称，使用当前日期时间作为默认名称
            if not name:
                name = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # 生成唯一任务ID
            task_id = self._generate_task_id()
            while task_id in self._tasks:
                task_id = self._generate_task_id()

            # 创建任务目录
            task_dir = get_media_task_dir(task_id)
            result_dir = get_media_task_result_dir(task_id)
            os.makedirs(task_dir, exist_ok=True)
            os.makedirs(result_dir, exist_ok=True)

            # 创建任务对象
            task = AudioMergeTask(task_id=task_id,
                                  name=name,
                                  status=TASK_STATUS_PENDING,
                                  files=[],
                                  create_time=datetime.now().timestamp(),
                                  update_time=datetime.now().timestamp())

            self._tasks[task_id] = task
            self._save_all_tasks()

            log.info(f"[AudioMerge] 创建音频合成任务: {task_id}, 名称: {name}")
            return 0, "任务创建成功", task_id

        except Exception as e:
            error_msg = f"创建任务失败: {str(e)}"
            log.error(f"[AudioMerge] {error_msg}")
            return -1, error_msg, None

    def add_file(self, task_id: str, file_path: str, filename: str) -> Tuple[int, str]:
        """
        添加文件到任务
        
        :param task_id: 任务ID
        :param file_path: 文件路径
        :param filename: 文件名
        :return: (错误码, 消息)
        """
        try:
            task, error_msg = self._validate_task_exists(task_id)
            if error_msg:
                return -1, error_msg

            error_msg = self._validate_task_not_processing(task, "添加文件")
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
        """
        从任务中移除文件
        
        :param task_id: 任务ID
        :param file_index: 文件索引
        :return: (错误码, 消息)
        """
        try:
            task, error_msg = self._validate_task_exists(task_id)
            if error_msg:
                return -1, error_msg

            error_msg = self._validate_task_not_processing(task, "删除文件")
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
        """
        调整文件顺序
        
        :param task_id: 任务ID
        :param file_indices: 新的文件索引顺序列表，例如 [2, 0, 1] 表示将索引2的文件移到第一位
        :return: (错误码, 消息)
        """
        try:
            task, error_msg = self._validate_task_exists(task_id)
            if error_msg:
                return -1, error_msg

            error_msg = self._validate_task_not_processing(task, "调整文件顺序")
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
        """
        开始音频合成任务
        
        :param task_id: 任务ID
        :return: (错误码, 消息)
        """
        try:
            task, error_msg = self._validate_task_exists(task_id)
            if error_msg:
                return -1, error_msg

            if task.status == TASK_STATUS_PROCESSING:
                return -1, "任务正在处理中"

            if len(task.files) == 0:
                return -1, "任务中没有文件"

            # 更新状态为处理中
            task.status = TASK_STATUS_PROCESSING
            self._save_task_and_update_time(task)

            # 在后台线程中执行合成
            def merge_thread():
                try:
                    result_file, result_duration = self._merge_audio_files(task_id, task.files)
                    if result_file:
                        task.status = TASK_STATUS_SUCCESS
                        task.result_file = result_file
                        # 如果 ffmpeg 无法解析时长，使用 get_media_duration 作为后备
                        if result_duration is None:
                            try:
                                result_duration = get_media_duration(result_file)
                            except Exception as e:
                                log.warning(f"[AudioMerge] 任务 {task_id} 获取结果文件时长失败: {e}")
                        task.result_duration = result_duration
                        log.info(f"[AudioMerge] 任务 {task_id} 合成成功: {result_file}, 时长: {task.result_duration}秒")
                    else:
                        task.status = TASK_STATUS_FAILED
                        task.error_message = "合成失败"
                        task.result_duration = None
                        log.error(f"[AudioMerge] 任务 {task_id} 合成失败")
                except Exception as e:
                    task.status = TASK_STATUS_FAILED
                    task.error_message = str(e)
                    task.result_duration = None
                    log.error(f"[AudioMerge] 任务 {task_id} 合成异常: {e}")
                finally:
                    self._save_task_and_update_time(task)

            threading.Thread(target=merge_thread, daemon=True).start()

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
                returncode, stdout, stderr = run_subprocess_safe(cmds, timeout=self.FFMPEG_DURATION_TIMEOUT)
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

    def _merge_audio_files(self, task_id: str, files: List[Dict]) -> Tuple[Optional[str], Optional[float]]:
        """
        使用 ffmpeg 合并音频文件
        
        :param task_id: 任务ID
        :param files: 文件列表
        :return: (结果文件路径, 时长（秒）)，失败返回 (None, None)
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
            cmds = [FFMPEG_PATH, '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', file_list_path, '-c', 'copy', '-y', result_file]

            log.info(f"[AudioMerge] 执行 ffmpeg 命令: {' '.join(cmds)}")
            # 使用公共方法安全地运行 subprocess，避免 gevent 与 asyncio 冲突
            try:
                returncode, stdout, stderr = run_subprocess_safe(cmds, timeout=FFMPEG_TIMEOUT)
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

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        获取任务信息
        
        :param task_id: 任务ID
        :return: 任务字典，不存在返回 None
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

    def list_tasks(self) -> List[Dict]:
        """
        列出所有任务，按创建时间倒序排列（最新的在上面）
        
        :return: 任务列表
        """
        tasks = [asdict(task) for task in self._tasks.values()]
        # 按创建时间倒序排序，最新的在上面
        tasks.sort(key=lambda x: x.get('create_time', 0), reverse=True)
        return tasks

    def delete_task(self, task_id: str) -> Tuple[int, str]:
        """
        删除任务
        
        :param task_id: 任务ID
        :return: (错误码, 消息)
        """
        try:
            task, error_msg = self._validate_task_exists(task_id)
            if error_msg:
                return -1, error_msg

            if task.status == TASK_STATUS_PROCESSING:
                return -1, "任务正在处理中，无法删除"

            # 删除任务目录
            task_dir = get_media_task_dir(task_id)
            if os.path.exists(task_dir):
                shutil.rmtree(task_dir)

            # 从内存中删除
            del self._tasks[task_id]
            self._save_all_tasks()  # 更新 task.json

            log.info(f"[AudioMerge] 删除任务: {task_id}")
            return 0, "任务删除成功"

        except Exception as e:
            error_msg = f"删除任务失败: {str(e)}"
            log.error(f"[AudioMerge] {error_msg}")
            return -1, error_msg


# 创建全局实例
audio_merge_mgr = AudioMergeMgr()
