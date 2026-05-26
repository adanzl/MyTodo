"""
音频转码管理服务
提供目录或上传文件转码为 MP3 格式的功能
"""
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, cast

from werkzeug.utils import secure_filename

from core.config import (
    FFMPEG_PATH,
    FFMPEG_TIMEOUT,
    MEDIA_BASE_DIR,
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_PROCESSING,
    TASK_STATUS_SUCCESS,
    app_logger,
    config,
)
from core.services.base_task_mgr import BaseTaskMgr, FileInfo, TaskBase, TaskProgress
from core.utils import get_file_type_by_magic_number, get_media_duration, get_unique_filepath, run_subprocess_safe

log = app_logger

FileProgress = TaskProgress
FileStatus = FileInfo

AUDIO_CONVERT_SOURCE_DIRECTORY = 'directory'
AUDIO_CONVERT_SOURCE_UPLOAD = 'upload'

AUDIO_CONVERT_BASE_DIR = os.path.join(MEDIA_BASE_DIR, 'convert')
MEDIA_EXTENSIONS = frozenset({
    '.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
    '.m4v', '.3gp', '.asf', '.vob', '.ts', '.mts', '.m2ts'
})
FILE_STATUS_PENDING = 'pending'
FILE_STATUS_PROCESSING = 'processing'
FILE_STATUS_SUCCESS = 'success'
FILE_STATUS_FAILED = 'failed'
VALID_SOURCE_TYPES = frozenset({AUDIO_CONVERT_SOURCE_DIRECTORY, AUDIO_CONVERT_SOURCE_UPLOAD})
TASK_UPLOAD_DIRNAME = 'upload'
TASK_RESULT_DIRNAME = 'result'
DEFAULT_OUTPUT_DIR = 'mp3'
MAX_UPLOAD_MB = config.MAX_UPLOAD_FILE_SIZE // 1024 // 1024


def _spawn(func: Callable[[], None]) -> Any:
    from gevent import spawn
    return spawn(func)


def _is_media_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in MEDIA_EXTENSIONS


@dataclass
class AudioConvertTask(TaskBase):
    """音频转码任务"""
    source_type: str = AUDIO_CONVERT_SOURCE_DIRECTORY
    directory: Optional[str] = None
    output_dir: str = DEFAULT_OUTPUT_DIR
    resolved_output_dir: Optional[str] = None
    overwrite: bool = True
    total_files: Optional[int] = None
    progress: Optional[FileProgress] = None
    file_status: Optional[Dict[str, FileStatus]] = None


class AudioConvertMgr(BaseTaskMgr[AudioConvertTask]):
    """音频转码管理器"""

    TASK_META_FILE = 'tasks.json'

    def __init__(self) -> None:
        super().__init__(base_dir=AUDIO_CONVERT_BASE_DIR)

    def _task_from_dict(self, data: dict) -> AudioConvertTask:
        return AudioConvertTask(**data)

    def _load_history_tasks(self) -> None:
        super()._load_history_tasks()

        changed = False
        for task in self._tasks.values():
            if task.source_type not in VALID_SOURCE_TYPES:
                task.source_type = AUDIO_CONVERT_SOURCE_DIRECTORY
                changed = True
            changed = self._update_resolved_output_dir(task) or changed

        if changed:
            self._save_all_tasks()

    def _update_task_status(self,
                            task: AudioConvertTask,
                            status: Optional[str] = None,
                            error_message: Optional[str] = None,
                            progress: Optional[FileProgress] = None) -> None:
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
                    overwrite: Optional[bool] = None,
                    source_type: Optional[str] = None) -> Tuple[int, str, Optional[str]]:
        name = name or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        output_dir = (output_dir or DEFAULT_OUTPUT_DIR).strip()
        if not output_dir:
            return -1, "输出目录名称不能为空", None

        normalized_source_type, error_msg = self._normalize_source_type(source_type)
        if error_msg:
            return -1, error_msg, None

        task = AudioConvertTask(task_id='',
                                name=name,
                                source_type=normalized_source_type,
                                output_dir=output_dir,
                                overwrite=overwrite if overwrite is not None else True)
        return self._create_task_and_save(task)

    def _before_create_task(self, task: AudioConvertTask) -> None:
        os.makedirs(self._get_task_upload_dir(task.task_id), exist_ok=True)
        os.makedirs(self._get_task_result_root_dir(task.task_id), exist_ok=True)
        self._update_resolved_output_dir(task)

    def _before_delete_task(self, task: AudioConvertTask) -> None:
        task_dir = self._get_task_dir(task.task_id)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)

    def update_task(self,
                    task_id: str,
                    name: Optional[str] = None,
                    directory: Optional[str] = None,
                    output_dir: Optional[str] = None,
                    overwrite: Optional[bool] = None,
                    source_type: Optional[str] = None) -> Tuple[int, str]:
        task, err = self._get_task_or_err(task_id)
        if err:
            return -1, err
        assert task is not None

        err2 = self._ensure_not_processing(task, "更新任务")
        if err2:
            return -1, err2

        try:
            updated = False
            re_scan_required = False

            if name is not None:
                if not name.strip():
                    return -1, "任务名称不能为空"
                task.name = name.strip()
                updated = True

            if directory is not None:
                dir_err = self._validate_directory(directory)
                if dir_err:
                    return -1, dir_err
                task.directory = directory
                re_scan_required = True
                updated = True

            if output_dir is not None:
                if not output_dir.strip():
                    return -1, "输出目录名称不能为空"
                task.output_dir = output_dir.strip()
                re_scan_required = True
                updated = True

            if source_type is not None:
                normalized_source_type, error_msg = self._normalize_source_type(source_type)
                if error_msg:
                    return -1, error_msg
                task.source_type = normalized_source_type
                re_scan_required = True
                updated = True

            if overwrite is not None:
                task.overwrite = bool(overwrite)
                updated = True

            if not updated:
                return -1, "没有提供要更新的字段"

            if re_scan_required:
                self._refresh_task_media_files(task)
            else:
                self._update_resolved_output_dir(task)

            self._save_task_and_update_time(task)
            return 0, "任务更新成功"
        except Exception as e:
            log.error(f"[AudioConvert] 更新任务失败: {e}")
            return -1, f"更新任务失败: {str(e)}"

    def upload_files(self, task_id: str, files: List[Any]) -> Tuple[int, str]:
        task, err = self._get_task_or_err(task_id)
        if err:
            return -1, err
        assert task is not None

        err2 = self._ensure_not_processing(task, "上传文件")
        if err2:
            return -1, err2

        code, msg, saved_paths = self._save_uploaded_files(task, files)
        if code != 0:
            return code, msg

        return self._apply_uploaded_paths(task, saved_paths)

    def start_task(self, task_id: str) -> Tuple[int, str]:
        task, err = self._get_task_or_err(task_id)
        if err:
            return -1, err
        assert task is not None

        if task.status == TASK_STATUS_PROCESSING:
            return -1, "任务正在处理中"

        ready_err = self._validate_task_ready(task)
        if ready_err:
            return -1, ready_err

        self._run_task_async(task_id, self._run_convert)
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

    def _update_file_duration_async(self, task_id: str, file_path: str) -> None:
        """兼容单文件时长更新调用。"""
        try:
            duration = get_media_duration(file_path)
            if duration is None:
                return

            task = self._get_task(task_id)
            if not task or not task.file_status or file_path not in task.file_status:
                return

            task.file_status[file_path]['duration'] = duration
            self._save_task_and_update_time(task)
        except Exception as e:
            log.warning(f"[AudioConvert] 异步获取文件时长失败 {file_path}: {e}")

    def _reset_task_progress(self, task: AudioConvertTask) -> FileProgress:
        progress: FileProgress = {'total': 0, 'processed': 0, 'current_file': ''}
        task.progress = progress
        return progress

    def _clear_current_file(self, task: AudioConvertTask) -> FileProgress:
        progress = task.progress or self._reset_task_progress(task)
        progress['current_file'] = ''
        return progress

    def _get_task_dir(self, task_id: str) -> str:
        return os.path.join(self._base_dir, task_id)

    def _get_task_upload_dir(self, task_id: str) -> str:
        return os.path.join(self._get_task_dir(task_id), TASK_UPLOAD_DIRNAME)

    def _get_task_result_root_dir(self, task_id: str) -> str:
        return os.path.join(self._get_task_dir(task_id), TASK_RESULT_DIRNAME)

    def _normalize_source_type(self, source_type: Optional[str]) -> Tuple[str, Optional[str]]:
        normalized = (source_type or AUDIO_CONVERT_SOURCE_DIRECTORY).strip().lower()
        if normalized not in VALID_SOURCE_TYPES:
            return AUDIO_CONVERT_SOURCE_DIRECTORY, f"不支持的转码来源类型: {source_type}"
        return normalized, None

    def _validate_directory(self, directory: str) -> Optional[str]:
        if not os.path.exists(directory):
            return "目录不存在"
        if not os.path.isdir(directory):
            return "路径不是目录"
        return None

    def _validate_task_ready(self, task: AudioConvertTask) -> Optional[str]:
        if task.source_type == AUDIO_CONVERT_SOURCE_DIRECTORY:
            return self._validate_directory(task.directory) if task.directory else "请先设置转码目录"
        if task.source_type == AUDIO_CONVERT_SOURCE_UPLOAD:
            return None if self._get_task_media_files(task) else "请先上传待转码文件"
        return f"不支持的转码来源类型: {task.source_type}"

    def _resolve_output_dir(self, task: AudioConvertTask) -> Optional[str]:
        if task.source_type == AUDIO_CONVERT_SOURCE_UPLOAD:
            return os.path.join(self._get_task_result_root_dir(task.task_id), task.output_dir)
        if not task.directory:
            return None
        return os.path.join(task.directory, task.output_dir)

    def _update_resolved_output_dir(self, task: AudioConvertTask) -> bool:
        resolved_output_dir = self._resolve_output_dir(task)
        if task.resolved_output_dir == resolved_output_dir:
            return False
        task.resolved_output_dir = resolved_output_dir
        return True

    def _get_task_media_files(self, task: AudioConvertTask) -> List[str]:
        self._update_resolved_output_dir(task)
        if task.source_type == AUDIO_CONVERT_SOURCE_UPLOAD:
            upload_dir = self._get_task_upload_dir(task.task_id)
            return self._scan_media_files(upload_dir) if os.path.isdir(upload_dir) else []
        if not task.directory:
            return []
        return self._scan_media_files(task.directory, exclude_dir_name=task.output_dir)

    def _refresh_task_media_files(self, task: AudioConvertTask) -> List[str]:
        media_files = self._get_task_media_files(task)
        if not media_files:
            task.total_files = 0
            task.file_status = {}
            return []

        task.total_files = len(media_files)
        self._initialize_file_status(task, media_files)
        return media_files

    def _apply_uploaded_paths(self, task: AudioConvertTask, file_paths: List[str]) -> Tuple[int, str]:
        for file_path in file_paths:
            if not os.path.exists(file_path):
                return -1, f"文件不存在: {file_path}"
            if not _is_media_file(file_path):
                return -1, f"不支持的文件类型: {os.path.basename(file_path)}"

        task.source_type = AUDIO_CONVERT_SOURCE_UPLOAD
        self._refresh_task_media_files(task)
        self._save_task_and_update_time(task)
        return 0, "文件上传成功"

    def _cleanup_files(self, file_paths: List[str]) -> None:
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    def _validate_upload_file(self, file: Any, filename: str) -> Optional[str]:
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > config.MAX_UPLOAD_FILE_SIZE:
            return f"文件大小超过限制 ({MAX_UPLOAD_MB}MB)"

        ext = os.path.splitext(secure_filename(filename))[1].lower()
        if ext not in MEDIA_EXTENSIONS:
            return f"不支持的文件类型: {filename}"

        file_type = get_file_type_by_magic_number(file)
        if file_type is not None and f".{file_type}" not in MEDIA_EXTENSIONS:
            return f"不支持的文件内容类型: {filename}"
        return None

    def _save_uploaded_files(self, task: AudioConvertTask, files: List[Any]) -> Tuple[int, str, List[str]]:
        if not files:
            return -1, "未找到上传的文件", []

        saved_paths: List[str] = []
        upload_dir = self._get_task_upload_dir(task.task_id)
        os.makedirs(upload_dir, exist_ok=True)

        try:
            for index, file in enumerate(files):
                filename = getattr(file, 'filename', None)
                if not filename:
                    continue

                validation_err = self._validate_upload_file(file, filename)
                if validation_err:
                    return -1, validation_err, []

                safe_filename = secure_filename(filename)
                ext = os.path.splitext(safe_filename)[1].lower()
                base_name = os.path.splitext(safe_filename)[0] or f"upload_{index + 1}"
                file_path = get_unique_filepath(upload_dir, base_name, ext)
                file.save(file_path)
                saved_paths.append(file_path)

            if not saved_paths:
                return -1, "没有可保存的有效文件", []
            return 0, "文件上传成功", saved_paths
        except Exception as e:
            self._cleanup_files(saved_paths)
            return -1, f"保存上传文件失败: {str(e)}", []

    def _get_file_info(self, file_path: str) -> FileStatus:
        file_info: FileStatus = {}
        try:
            if os.path.exists(file_path):
                file_info['size'] = os.path.getsize(file_path)
        except Exception as e:
            log.warning(f"[AudioConvert] 获取文件大小失败 {file_path}: {e}")
        return file_info

    def _build_file_status(self, media_file: str, old_status: Optional[FileStatus], preserve_completed: bool) -> FileStatus:
        if old_status is None:
            return cast(FileStatus, {'status': FILE_STATUS_PENDING, **self._get_file_info(media_file)})

        merged_status = cast(FileStatus, dict(old_status))
        if preserve_completed:
            return merged_status

        merged_status['status'] = FILE_STATUS_PENDING
        merged_status.pop('error', None)
        return merged_status

    def _initialize_file_status(self, task: AudioConvertTask, media_files: List[str]) -> None:
        existing_status = task.file_status or {}
        preserve_completed_status = task.status in (TASK_STATUS_SUCCESS, TASK_STATUS_FAILED)
        new_file_status: Dict[str, FileStatus] = {}
        files_missing_duration: List[str] = []

        for media_file in media_files:
            new_file_status[media_file] = self._build_file_status(
                media_file,
                existing_status.get(media_file),
                preserve_completed_status,
            )
            if new_file_status[media_file].get('duration') is None:
                files_missing_duration.append(media_file)

        task.file_status = new_file_status
        if files_missing_duration:
            self._start_async_duration_update(task.task_id, files_missing_duration)

    def _ensure_output_directory(self, output_dir_path: str) -> Tuple[bool, Optional[str]]:
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
        if task.file_status is None:
            task.file_status = {}

        new_status = cast(FileStatus, dict(task.file_status.get(file_path, {})))
        new_status['status'] = status
        if error is not None:
            new_status['error'] = error
        else:
            new_status.pop('error', None)
        task.file_status[file_path] = new_status

    def _start_async_duration_update(self, task_id: str, file_paths: List[str]) -> None:
        if not file_paths:
            return

        def update_durations() -> None:
            task = self._get_task(task_id)
            if not task or not task.file_status:
                return

            updated_count = 0
            for file_path in file_paths:
                try:
                    file_status = task.file_status.get(file_path)
                    if not file_status or file_status.get('duration') is not None:
                        continue

                    duration = get_media_duration(file_path)
                    if duration is None:
                        continue

                    file_status['duration'] = duration
                    updated_count += 1
                except Exception as e:
                    log.warning(f"[AudioConvert] 异步更新文件时长异常 {file_path}: {e}")

            if updated_count:
                self._save_task_and_update_time(task)
                log.debug(f"[AudioConvert] 批量更新 {updated_count} 个文件时长")

        _spawn(update_durations)

    def _scan_media_files(self, directory: str, exclude_dir_name: Optional[str] = None) -> List[str]:
        media_files: List[str] = []
        for root, dirs, files in os.walk(directory):
            if exclude_dir_name:
                dirs[:] = [dir_name for dir_name in dirs if dir_name != exclude_dir_name]
            for filename in files:
                if _is_media_file(filename):
                    media_files.append(os.path.join(root, filename))
        return media_files

    def _convert_file_to_mp3(self, input_file: str, output_file: str) -> Tuple[bool, Optional[str]]:
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

    def _format_failure_summary(self, failed_files: List[str]) -> str:
        preview = ', '.join(failed_files[:5])
        suffix = f" 等共 {len(failed_files)} 个文件" if len(failed_files) > 5 else ""
        return f"部分文件转换失败: {preview}{suffix}"

    def _run_convert(self, task: AudioConvertTask) -> None:
        try:
            progress = self._reset_task_progress(task)
            self._save_task_and_update_time(task)

            if task.source_type == AUDIO_CONVERT_SOURCE_DIRECTORY:
                dir_err = self._validate_directory(task.directory) if task.directory else "目录不存在"
                if dir_err:
                    self._update_task_status(task, TASK_STATUS_FAILED, dir_err)
                    return

            media_files = self._refresh_task_media_files(task)
            total = len(media_files)
            progress['total'] = total
            self._save_task_and_update_time(task)

            if total == 0:
                progress['processed'] = 0
                empty_msg = "没有可转码的媒体文件" if task.source_type == AUDIO_CONVERT_SOURCE_UPLOAD else "目录中没有媒体文件"
                self._update_task_status(task, TASK_STATUS_SUCCESS, None, progress)
                log.info(f"[AudioConvert] 任务 {task.task_id} 完成：{empty_msg}")
                return

            output_dir_path = task.resolved_output_dir or self._resolve_output_dir(task)
            if not output_dir_path:
                self._update_task_status(task, TASK_STATUS_FAILED, "输出目录无效")
                return

            success, error_msg = self._ensure_output_directory(output_dir_path)
            if not success:
                self._update_task_status(task, TASK_STATUS_FAILED, error_msg)
                return

            processed = 0
            failed_files: List[str] = []

            for media_file in media_files:
                if self._should_stop(task.task_id):
                    self._update_task_status(task, TASK_STATUS_FAILED, "任务已被停止", self._clear_current_file(task))
                    log.info(f"[AudioConvert] 任务 {task.task_id} 被停止")
                    return

                progress['current_file'] = os.path.basename(media_file)
                self._update_file_status(task, media_file, FILE_STATUS_PROCESSING)
                self._save_task_and_update_time(task)

                output_file = os.path.join(output_dir_path, f"{os.path.splitext(os.path.basename(media_file))[0]}.mp3")
                if os.path.exists(output_file) and not task.overwrite:
                    processed += 1
                    progress['processed'] = processed
                    self._update_file_status(task, media_file, FILE_STATUS_SUCCESS)
                    self._save_task_and_update_time(task)
                    continue

                success, error = self._convert_file_to_mp3(media_file, output_file)
                processed += 1
                progress['processed'] = processed

                if success:
                    self._update_file_status(task, media_file, FILE_STATUS_SUCCESS)
                else:
                    self._update_file_status(task, media_file, FILE_STATUS_FAILED, error)
                    failed_files.append(f"{os.path.basename(media_file)}: {error}")
                self._save_task_and_update_time(task)

            if self._should_stop(task.task_id):
                self._update_task_status(task, TASK_STATUS_FAILED, "任务已被停止", self._clear_current_file(task))
                return

            status = TASK_STATUS_FAILED if failed_files else TASK_STATUS_SUCCESS
            error_msg = self._format_failure_summary(failed_files) if failed_files else None
            progress['current_file'] = ''
            self._update_task_status(task, status, error_msg, progress)

            success_count = processed - len(failed_files)
            log.info(f"[AudioConvert] 任务 {task.task_id} 完成: 成功 {success_count}/{total}")

        except Exception as e:
            log.error(f"[AudioConvert] 转码过程出错: {e}")
            self._update_task_status(task, TASK_STATUS_FAILED, f"转码过程出错: {str(e)}")


audio_convert_mgr = AudioConvertMgr()
