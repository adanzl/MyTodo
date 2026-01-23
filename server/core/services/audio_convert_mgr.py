"""
音频转码管理服务
提供音频文件转码为 MP3 格式的功能
"""
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from core.services.base_task_mgr import BaseTaskMgr, FileInfo, TaskBase, TaskProgress

from core.config import app_logger
from core.config import (MEDIA_BASE_DIR, FFMPEG_PATH, FFMPEG_TIMEOUT, TASK_STATUS_PENDING, TASK_STATUS_PROCESSING,
                         TASK_STATUS_SUCCESS, TASK_STATUS_FAILED)
from core.utils import ensure_directory as ensure_directory, run_subprocess_safe, get_media_duration

log = app_logger

FileProgress = TaskProgress
FileStatus = FileInfo


@dataclass
class AudioConvertTask(TaskBase):
    """音频转码任务"""
    directory: Optional[str] = None  # 转码目录
    output_dir: str = 'mp3'  # 输出目录名称，默认为 mp3
    overwrite: bool = True  # 是否覆盖同名文件，默认为 True
    total_files: Optional[int] = None  # 可处理的文件总数
    progress: Optional[FileProgress] = None  # 转码进度 {total: int, processed: int, current_file: str}
    file_status: Optional[Dict[str, FileStatus]] = None  # 文件状态 {file_path: {...}}


AUDIO_CONVERT_BASE_DIR = os.path.join(MEDIA_BASE_DIR, 'convert')


def _spawn(func: Any) -> Any:
    from gevent import spawn
    return spawn(func)


class AudioConvertMgr(BaseTaskMgr[AudioConvertTask]):
    """音频转码管理器"""

    TASK_META_FILE = 'tasks.json'

    def __init__(self) -> None:
        """初始化管理器"""
        super().__init__(base_dir=AUDIO_CONVERT_BASE_DIR)

    def _task_from_dict(self, data: dict) -> AudioConvertTask:
        return AudioConvertTask(**data)

    def _load_history_tasks(self) -> None:
        """加载历史任务"""
        super()._load_history_tasks()
        self._migrate_legacy_tasks_if_needed()

    def _migrate_legacy_tasks_if_needed(self) -> None:
        """兼容迁移：旧 convert/<task_id>.json -> convert/tasks.json。

        迁移策略：当 tasks.json 为空/不存在时，尝试读取同目录下的 <task_id>.json。
        不删除旧文件。
        """
        meta_file = self._get_task_meta_file()
        has_new_meta = os.path.exists(meta_file) and os.path.getsize(meta_file) > 2

        if has_new_meta:
            return

        try:
            if not os.path.exists(AUDIO_CONVERT_BASE_DIR):
                return

            legacy_files = []
            for filename in os.listdir(AUDIO_CONVERT_BASE_DIR):
                if not filename.endswith('.json'):
                    continue
                if filename == self.TASK_META_FILE:
                    continue
                legacy_files.append(os.path.join(AUDIO_CONVERT_BASE_DIR, filename))

            if not legacy_files:
                return

            migrated = 0
            with self._task_lock:
                for fp in legacy_files:
                    try:
                        with open(fp, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        task = AudioConvertTask(**data)
                        if not getattr(task, 'task_id', None):
                            # 从文件名推断 task_id
                            task.task_id = os.path.splitext(os.path.basename(fp))[0]
                        self._tasks[task.task_id] = task
                        migrated += 1
                    except Exception as e:
                        log.error(f"[AudioConvert] 迁移旧任务文件失败 {fp}: {e}")

                if migrated > 0:
                    self._save_all_tasks()

            if migrated > 0:
                log.info(f"[AudioConvert] 已迁移 {migrated} 个旧任务到 tasks.json")

        except Exception as e:
            log.error(f"[AudioConvert] 迁移旧任务异常: {e}")

    def _update_task_status(self,
                            task: AudioConvertTask,
                            status: Optional[str] = None,
                            error_message: Optional[str] = None,
                            progress: Optional[Dict[str, Any]] = None) -> None:
        """更新任务状态并保存"""
        if status:
            task.status = status
        if error_message is not None:
            task.error_message = error_message
        if progress is not None:
            task.progress = progress
        self._save_task_and_update_time(task)

    def create_task(self,
                    name: Optional[str] = None,
                    output_dir: Optional[str] = None,
                    overwrite: Optional[bool] = None) -> Tuple[int, str, Optional[str]]:
        name = name or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        output_dir = (output_dir or 'mp3').strip()
        if not output_dir:
            return -1, "输出目录名称不能为空", None

        task = AudioConvertTask(task_id='',
                                name=name,
                                output_dir=output_dir,
                                overwrite=overwrite if overwrite is not None else True)

        return self._create_task_and_save(task)

    def update_task(self,
                    task_id: str,
                    name: Optional[str] = None,
                    directory: Optional[str] = None,
                    output_dir: Optional[str] = None,
                    overwrite: Optional[bool] = None) -> Tuple[int, str]:
        """更新任务配置。"""
        task, err = self._get_task_or_err(task_id)
        if err:
            return -1, err
        err2 = self._ensure_not_processing(task, "更新任务")
        if err2:
            return -1, err2

        try:
            updated = False
            if name is not None:
                if not name.strip():
                    return -1, "任务名称不能为空"
                task.name = name.strip()
                updated = True
            if directory is not None:
                if not os.path.exists(directory):
                    return -1, "目录不存在"
                if not os.path.isdir(directory):
                    return -1, "路径不是目录"
                task.directory = directory
                if task.directory:
                    media_files = self._scan_media_files(task.directory, task.output_dir)
                    task.total_files = len(media_files)
                    self._initialize_file_status(task, media_files)
                updated = True
            if output_dir is not None:
                if not output_dir.strip():
                    return -1, "输出目录名称不能为空"
                task.output_dir = output_dir.strip()
                if task.directory:
                    media_files = self._scan_media_files(task.directory, task.output_dir)
                    task.total_files = len(media_files)
                    self._initialize_file_status(task, media_files)
                updated = True
            if overwrite is not None:
                task.overwrite = bool(overwrite)
                updated = True

            if not updated:
                return -1, "没有提供要更新的字段"

            self._save_task_and_update_time(task)
            return 0, "任务更新成功"
        except Exception as e:
            log.error(f"[AudioConvert] 更新任务失败: {e}")
            return -1, f"更新任务失败: {str(e)}"

    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息（大小），时长异步获取"""
        file_info: Dict[str, Any] = {}
        try:
            if os.path.exists(file_path):
                file_info['size'] = os.path.getsize(file_path)
        except Exception as e:
            log.warning(f"[AudioConvert] 获取文件大小失败 {file_path}: {e}")
        return file_info

    def _initialize_file_status(self, task: AudioConvertTask, media_files: List[str]) -> None:
        """初始化文件状态，保留已有文件信息"""
        if task.file_status is None:
            task.file_status = {}

        new_file_status = {}
        for media_file in media_files:
            if media_file in task.file_status:
                old_status = task.file_status[media_file]
                if task.status in (TASK_STATUS_SUCCESS, TASK_STATUS_FAILED):
                    new_file_status[media_file] = old_status
                else:
                    file_info = {'size': old_status.get('size'), 'duration': old_status.get('duration')}
                    new_file_status[media_file] = {'status': 'pending', **file_info}
            else:
                file_info = self._get_file_info(media_file)
                new_file_status[media_file] = {'status': 'pending', **file_info}

        task.file_status = new_file_status
        self._start_async_duration_update(task.task_id, list(new_file_status.keys()))

    def _ensure_output_directory(self, output_dir_path: str) -> Tuple[bool, Optional[str]]:
        """确保输出目录存在且有写权限"""
        try:
            if os.path.exists(output_dir_path):
                if not os.access(output_dir_path, os.W_OK):
                    error_msg = f"输出目录无写权限: {output_dir_path}"
                    log.error(f"[AudioConvert] {error_msg}")
                    return False, error_msg
            else:
                os.makedirs(output_dir_path, exist_ok=True)
            return True, None
        except PermissionError as e:
            error_msg = f"无法创建输出目录，权限不足: {output_dir_path}"
            log.error(f"[AudioConvert] {error_msg}: {e}")
            return False, error_msg
        except OSError as e:
            error_msg = f"无法创建输出目录: {output_dir_path}"
            log.error(f"[AudioConvert] {error_msg}: {e}")
            return False, error_msg

    def _update_file_status(self,
                            task: AudioConvertTask,
                            file_path: str,
                            status: str,
                            error: Optional[str] = None) -> None:
        """更新文件状态，保留已有文件信息"""
        old_status = task.file_status.get(file_path, {})
        new_status = {**old_status, 'status': status}
        if error is not None:
            new_status['error'] = error
        task.file_status[file_path] = new_status

    def _update_file_duration_async(self, task_id: str, file_path: str) -> None:
        """异步获取文件时长并更新任务"""
        try:
            duration = get_media_duration(file_path)
            if duration is not None:
                task = self._get_task(task_id)
                if task and task.file_status and file_path in task.file_status:
                    file_status = task.file_status[file_path]
                    file_status['duration'] = duration
                    self._save_task_and_update_time(task)
                    log.debug(f"[AudioConvert] 异步更新文件时长: {file_path}, {duration}秒")
        except Exception as e:
            log.warning(f"[AudioConvert] 异步获取文件时长失败 {file_path}: {e}")

    def _start_async_duration_update(self, task_id: str, file_paths: List[str]) -> None:
        """启动异步获取文件时长的任务"""

        def update_durations() -> None:
            for file_path in file_paths:
                try:
                    self._update_file_duration_async(task_id, file_path)
                except Exception as e:
                    log.warning(f"[AudioConvert] 异步更新文件时长异常 {file_path}: {e}")

        _spawn(update_durations)

    def _scan_media_files(self, directory: str, output_dir: str) -> List[str]:
        """扫描目录下的所有媒体文件（音频和视频）"""
        media_extensions = {
            '.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
            '.webm', '.m4v', '.3gp', '.asf', '.rm', '.rmvb', '.vob', '.ts', '.mts', '.m2ts'
        }
        media_files = []
        for root, _, files in os.walk(directory):
            if output_dir in root:
                continue
            for f in files:
                file_path = os.path.join(root, f)
                ext = os.path.splitext(f)[1].lower()
                if ext in media_extensions:
                    media_files.append(file_path)
        return media_files

    def _convert_file_to_mp3(self, input_file: str, output_file: str) -> Tuple[bool, Optional[str]]:
        """将单个媒体文件转换为 MP3 格式。"""
        output_dir = os.path.dirname(output_file)
        success, error_msg = self._ensure_output_directory(output_dir)
        if not success:
            return False, error_msg

        cmds = [
            FFMPEG_PATH, '-loglevel', 'error', '-i', input_file, '-vn', '-codec:a', 'libmp3lame', '-q:a', '2', '-y',
            output_file
        ]

        log.info(f"[AudioConvert] 执行 ffmpeg 命令: {' '.join(cmds)}")
        try:
            returncode, stdout, stderr = run_subprocess_safe(cmds, timeout=FFMPEG_TIMEOUT)
        except TimeoutError as e:
            error_msg = "转换超时"
            log.error(f"[AudioConvert] {error_msg}: {e}")
            return False, error_msg
        except FileNotFoundError as e:
            error_msg = "ffmpeg 未找到，请确保已安装 ffmpeg"
            log.error(f"[AudioConvert] {error_msg}: {e}")
            return False, error_msg
        except Exception as e:
            error_msg = f"转换失败: {str(e)}"
            log.error(f"[AudioConvert] {error_msg}")
            return False, error_msg

        if returncode == 0:
            if os.path.exists(output_file):
                log.info(f"[AudioConvert] 转换成功: {input_file} -> {output_file}")
                return True, None
            error_msg = f"输出文件不存在: {output_file}"
            log.error(f"[AudioConvert] {error_msg}")
            return False, error_msg

        error_msg = stderr or stdout or '未知错误'
        log.error(f"[AudioConvert] ffmpeg 执行失败 (返回码: {returncode}): {error_msg}")
        return False, error_msg

    def _convert_directory(self, task: AudioConvertTask) -> None:
        """在后台线程中执行整个目录的音频转码。"""
        try:
            if task.progress is None:
                task.progress = {'total': 0, 'processed': 0, 'current_file': ''}
            else:
                task.progress['total'] = 0
                task.progress['processed'] = 0
                task.progress['current_file'] = ''
            self._save_task_and_update_time(task)

            if not task.directory or not os.path.exists(task.directory):
                self._update_task_status(task, TASK_STATUS_FAILED, "目录不存在")
                return

            media_files = self._scan_media_files(task.directory, task.output_dir)
            total = len(media_files)
            task.progress['total'] = total
            task.progress['processed'] = 0

            if task.file_status is None:
                task.file_status = {}
            for media_file in media_files:
                if media_file not in task.file_status:
                    file_info = self._get_file_info(media_file)
                    task.file_status[media_file] = {'status': 'pending', **file_info}
                else:
                    old_status = task.file_status[media_file]
                    if 'status' not in old_status:
                        old_status['status'] = 'pending'

            self._save_task_and_update_time(task)
            self._start_async_duration_update(task.task_id, media_files)

            if total == 0:
                task.progress['processed'] = 0
                self._update_task_status(task, TASK_STATUS_SUCCESS, None, task.progress)
                log.info(f"[AudioConvert] 任务 {task.task_id} 完成：目录中没有媒体文件")
                return

            output_dir_path = os.path.join(task.directory, task.output_dir)
            success, error_msg = self._ensure_output_directory(output_dir_path)
            if not success:
                self._update_task_status(task, TASK_STATUS_FAILED, error_msg)
                return

            processed = 0
            failed_files = []

            for media_file in media_files:
                if self._should_stop(task.task_id):
                    self._update_task_status(task, TASK_STATUS_FAILED, "任务已被停止", {'current_file': ''})
                    log.info(f"[AudioConvert] 任务 {task.task_id} 被停止")
                    return

                task.progress['current_file'] = os.path.basename(media_file)
                self._update_file_status(task, media_file, 'processing')
                self._save_task_and_update_time(task)

                base_name = os.path.splitext(os.path.basename(media_file))[0]
                output_file = os.path.join(output_dir_path, f"{base_name}.mp3")

                if os.path.exists(output_file) and not task.overwrite:
                    processed += 1
                    task.progress['processed'] = processed
                    self._update_file_status(task, media_file, 'success')
                    self._save_task_and_update_time(task)
                    continue

                success, error = self._convert_file_to_mp3(media_file, output_file)
                processed += 1
                task.progress['processed'] = processed

                if success:
                    self._update_file_status(task, media_file, 'success')
                else:
                    self._update_file_status(task, media_file, 'failed', error)
                    failed_files.append(f"{os.path.basename(media_file)}: {error}")
                self._save_task_and_update_time(task)

            if self._should_stop(task.task_id):
                self._update_task_status(task, TASK_STATUS_FAILED, "任务已被停止", {'current_file': ''})
                return

            status = TASK_STATUS_FAILED if failed_files else TASK_STATUS_SUCCESS
            error_msg = None if not failed_files else (
                f"部分文件转换失败: {', '.join(failed_files[:5])}" +
                (f" 等共 {len(failed_files)} 个文件" if len(failed_files) > 5 else ""))
            task.progress['current_file'] = ''
            self._update_task_status(task, status, error_msg, task.progress)

            success_count = processed - len(failed_files)
            log.info(f"[AudioConvert] 任务 {task.task_id} 完成: 成功 {success_count}/{total}")

        except Exception as e:
            log.error(f"[AudioConvert] 转码过程出错: {e}")
            self._update_task_status(task, TASK_STATUS_FAILED, f"转码过程出错: {str(e)}")

    def start_task(self, task_id: str) -> Tuple[int, str]:
        """启动指定的转码任务。"""
        task, err = self._get_task_or_err(task_id)
        if err:
            return -1, err
        if task.status == TASK_STATUS_PROCESSING:
            return -1, "任务正在处理中"
        if not task.directory:
            return -1, "请先设置转码目录"

        self._run_task_async(task_id, self._convert_directory)
        log.info(f"[AudioConvert] 启动转码任务: {task_id}")
        return 0, "转码任务已启动"

    def get_task(self, task_id: str) -> Optional[Dict]:
        task = self._get_task(task_id)
        return asdict(task) if task else None

    def get_task_list(self) -> List[Dict]:
        return self.list_tasks()

    def _should_request_stop_before_delete(self, _task: AudioConvertTask) -> bool:
        return True

    def delete_task(self, task_id: str) -> Tuple[int, str]:
        code, msg = super().delete_task(task_id)
        if code == 0:
            log.info(f"[AudioConvert] 删除任务: {task_id}")
        return code, msg


audio_convert_mgr = AudioConvertMgr()
