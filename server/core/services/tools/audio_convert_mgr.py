"""音频转码：目录扫描或上传文件转 MP3。"""
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from werkzeug.utils import secure_filename

from core.config import (
    FFMPEG_PATH,
    FFMPEG_TIMEOUT,
    MEDIA_BASE_DIR,
    TASK_STATUS_FAILED,
    TASK_STATUS_PROCESSING,
    TASK_STATUS_SUCCESS,
    app_logger,
    config,
)
from core.services.base_task_mgr import BaseTaskMgr, FileInfo, TaskBase, TaskProgress
from core.utils import get_media_duration, get_unique_filepath, run_subprocess_safe

log = app_logger

SOURCE_DIRECTORY = 'directory'
SOURCE_UPLOAD = 'upload'
BASE_DIR = os.path.join(MEDIA_BASE_DIR, 'convert')
AUDIO_CONVERT_BASE_DIR = BASE_DIR
MEDIA_EXT = frozenset({
    '.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
    '.m4v', '.3gp', '.asf', '.vob', '.ts', '.mts', '.m2ts',
})


def _spawn(fn: Callable[[], None]) -> Any:
    from gevent import spawn
    return spawn(fn)


def _is_media(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in MEDIA_EXT


def _source_type(value: Optional[str]) -> str:
    normalized = (value or SOURCE_DIRECTORY).strip().lower()
    if normalized in (SOURCE_DIRECTORY, SOURCE_UPLOAD):
        return normalized
    return SOURCE_DIRECTORY


@dataclass
class AudioConvertTask(TaskBase):
    source_type: str = SOURCE_DIRECTORY
    directory: Optional[str] = None
    output_dir: str = 'mp3'
    resolved_output_dir: Optional[str] = None
    overwrite: bool = True
    total_files: Optional[int] = None
    progress: Optional[TaskProgress] = None
    file_status: Optional[Dict[str, FileInfo]] = None


class AudioConvertMgr(BaseTaskMgr[AudioConvertTask]):
    TASK_META_FILE = 'tasks.json'

    def __init__(self) -> None:
        super().__init__(base_dir=BASE_DIR)

    def _task_from_dict(self, data: dict) -> AudioConvertTask:
        return AudioConvertTask(**data)

    def _load_history_tasks(self) -> None:
        super()._load_history_tasks()
        changed = False
        for task in self._tasks.values():
            task.source_type = _source_type(task.source_type)
            if self._sync_output_dir(task):
                changed = True
        if changed:
            self._save_all_tasks()

    def create_task(self,
                    name: Optional[str] = None,
                    output_dir: Optional[str] = None,
                    overwrite: Optional[bool] = None,
                    source_type: Optional[str] = None) -> Tuple[int, str, Optional[str]]:
        task = AudioConvertTask(
            task_id='',
            name=name or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            source_type=_source_type(source_type),
            output_dir=(output_dir or 'mp3').strip() or 'mp3',
            overwrite=overwrite if overwrite is not None else True,
        )
        return self._create_task_and_save(task)

    def update_task(self,
                    task_id: str,
                    name: Optional[str] = None,
                    directory: Optional[str] = None,
                    output_dir: Optional[str] = None,
                    overwrite: Optional[bool] = None,
                    source_type: Optional[str] = None) -> Tuple[int, str]:
        task, err = self._get_task_or_err(task_id)
        if not task:
            return -1, err
        if task.status == TASK_STATUS_PROCESSING:
            return -1, "任务正在处理中，无法更新任务"

        updated = rescan = False
        if name is not None:
            task.name = name.strip() or task.name
            updated = True
        if directory is not None:
            task.directory = directory
            updated = rescan = True
        if output_dir is not None:
            task.output_dir = output_dir.strip() or task.output_dir
            updated = rescan = True
        if source_type is not None:
            task.source_type = _source_type(source_type)
            updated = rescan = True
        if overwrite is not None:
            task.overwrite = bool(overwrite)
            updated = True
        if not updated:
            return -1, "没有提供要更新的字段"

        if rescan:
            self._scan_and_bind_files(task)
        else:
            self._sync_output_dir(task)
        self._save_task_and_update_time(task)
        return 0, "任务更新成功"

    def upload_files(self, task_id: str, files: List[Any]) -> Tuple[int, str]:
        task, err = self._get_task_or_err(task_id)
        if not task:
            return -1, err
        if task.status == TASK_STATUS_PROCESSING:
            return -1, "任务正在处理中，无法上传文件"

        upload_dir = os.path.join(self._task_dir(task_id), 'upload')
        os.makedirs(upload_dir, exist_ok=True)
        saved: List[str] = []
        try:
            for index, upload_file in enumerate(files):
                filename = getattr(upload_file, 'filename', None)
                if not filename:
                    continue
                upload_file.seek(0, 2)
                if upload_file.tell() > config.MAX_UPLOAD_FILE_SIZE:
                    return -1, f"文件大小超过限制 ({config.MAX_UPLOAD_FILE_SIZE // 1024 // 1024}MB)"
                upload_file.seek(0)
                safe_name = secure_filename(filename)
                ext = os.path.splitext(safe_name)[1].lower()
                base_name = os.path.splitext(safe_name)[0] or f"upload_{index + 1}"
                saved_path = get_unique_filepath(upload_dir, base_name, ext)
                upload_file.save(saved_path)
                saved.append(saved_path)
            if not saved:
                return -1, "没有可保存的有效文件"
        except Exception as e:
            for saved_path in saved:
                try:
                    os.remove(saved_path)
                except OSError:
                    pass
            return -1, f"保存上传文件失败: {e}"

        task.source_type = SOURCE_UPLOAD
        self._scan_and_bind_files(task)
        self._save_task_and_update_time(task)
        return 0, "文件上传成功"

    def start_task(self, task_id: str) -> Tuple[int, str]:
        task, err = self._get_task_or_err(task_id)
        if not task:
            return -1, err
        if task.status == TASK_STATUS_PROCESSING:
            return -1, "任务正在处理中"
        if task.source_type == SOURCE_DIRECTORY and not task.directory:
            return -1, "请先设置转码目录"
        if task.source_type == SOURCE_UPLOAD and not self._media_files(task):
            return -1, "请先上传待转码文件"
        self._run_task_async(task_id, self._run_convert)
        log.info(f"[AudioConvert] 启动转码任务: {task_id}")
        return 0, "转码任务已启动"

    def get_task(self, task_id: str) -> Optional[Dict]:
        task = self._get_task(task_id)
        return asdict(task) if task else None

    def get_task_list(self) -> List[Dict]:
        return self.list_tasks()

    def delete_task(self, task_id: str) -> Tuple[int, str]:
        code, msg = super().delete_task(task_id)
        if code == 0:
            log.info(f"[AudioConvert] 删除任务: {task_id}")
        return code, msg

    def get_convert_output_file(self, task_id: str, output_path: str) -> Tuple[Optional[str], Optional[str]]:
        task, err = self._get_task_or_err(task_id)
        if not task:
            return None, err
        if not os.path.isfile(output_path):
            return None, "文件不存在"
        allowed_output_paths = {
            os.path.normpath(resolved_output)
            for file_info in (task.file_status or {}).values()
            if file_info.get('status') == 'success'
            and (resolved_output := file_info.get('output_path'))
        }
        if os.path.normpath(output_path) in allowed_output_paths:
            return output_path, None
        return None, "文件不存在"

    def _before_create_task(self, task: AudioConvertTask) -> None:
        os.makedirs(os.path.join(self._task_dir(task.task_id), 'upload'), exist_ok=True)
        os.makedirs(os.path.join(self._task_dir(task.task_id), 'result'), exist_ok=True)
        self._sync_output_dir(task)

    def _before_delete_task(self, task: AudioConvertTask) -> None:
        path = self._task_dir(task.task_id)
        if os.path.exists(path):
            shutil.rmtree(path)

    def _should_request_stop_before_delete(self, _task: AudioConvertTask) -> bool:
        return True

    def _task_dir(self, task_id: str) -> str:
        return os.path.join(self._base_dir, task_id)

    def _output_dir(self, task: AudioConvertTask) -> Optional[str]:
        if task.source_type == SOURCE_UPLOAD:
            return os.path.join(self._task_dir(task.task_id), 'result', task.output_dir)
        if task.directory:
            return os.path.join(task.directory, task.output_dir)
        return None

    def _sync_output_dir(self, task: AudioConvertTask) -> bool:
        resolved = self._output_dir(task)
        if task.resolved_output_dir == resolved:
            return False
        task.resolved_output_dir = resolved
        return True

    def _mp3_path(self, task: AudioConvertTask, input_path: str) -> Optional[str]:
        out_dir = self._output_dir(task)
        if not out_dir:
            return None
        stem = os.path.splitext(os.path.basename(input_path))[0]
        return os.path.join(out_dir, f"{stem}.mp3")

    def _list_media(self, root: str, exclude_subdir: Optional[str] = None) -> List[str]:
        found: List[str] = []
        for dirpath, dirs, files in os.walk(root):
            if exclude_subdir:
                dirs[:] = [d for d in dirs if d != exclude_subdir]
            for name in files:
                if _is_media(name):
                    found.append(os.path.join(dirpath, name))
        return found

    def _media_files(self, task: AudioConvertTask) -> List[str]:
        self._sync_output_dir(task)
        if task.source_type == SOURCE_UPLOAD:
            upload = os.path.join(self._task_dir(task.task_id), 'upload')
            return self._list_media(upload) if os.path.isdir(upload) else []
        if not task.directory:
            return []
        return self._list_media(task.directory, task.output_dir)

    def _scan_and_bind_files(self, task: AudioConvertTask) -> None:
        files = self._media_files(task)
        task.total_files = len(files)
        file_status_map: Dict[str, FileInfo] = {}
        for file_path in files:
            file_info: FileInfo = {'status': 'pending'}
            try:
                file_info['size'] = os.path.getsize(file_path)
            except OSError:
                pass
            file_status_map[file_path] = file_info
        task.file_status = file_status_map
        paths_without_duration = [
            file_path for file_path in files if not file_status_map[file_path].get('duration')
        ]
        if paths_without_duration:
            self._fill_durations_async(task.task_id, paths_without_duration)

    def _ffmpeg_mp3(self, input_path: str, output_path: str) -> Tuple[bool, Optional[str]]:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        except OSError as e:
            return False, str(e)
        cmd = [
            FFMPEG_PATH, '-loglevel', 'error', '-i', input_path, '-vn', '-codec:a', 'libmp3lame', '-q:a', '2', '-y',
            output_path
        ]
        try:
            return_code, stdout, stderr = run_subprocess_safe(cmd, timeout=FFMPEG_TIMEOUT)
        except TimeoutError:
            return False, "转换超时"
        except FileNotFoundError:
            return False, "ffmpeg 未找到"
        except Exception as e:
            return False, str(e)
        if return_code == 0 and os.path.isfile(output_path):
            return True, None
        return False, stderr or stdout or "转换失败"

    def _set_file(self, task: AudioConvertTask, path: str, status: str,
                  error: Optional[str] = None, output_path: Optional[str] = None) -> None:
        if task.file_status is None:
            task.file_status = {}
        if path not in task.file_status:
            task.file_status[path] = {}
        file_info = task.file_status[path]
        file_info['status'] = status
        if error:
            file_info['error'] = error
        else:
            file_info.pop('error', None)
        if output_path:
            file_info['output_path'] = output_path

    def _run_convert(self, task: AudioConvertTask) -> None:
        try:
            task.progress = {'total': 0, 'processed': 0, 'current_file': ''}
            task.status = TASK_STATUS_PROCESSING
            self._save_task_and_update_time(task)

            self._scan_and_bind_files(task)
            media_files = list((task.file_status or {}).keys())
            progress = task.progress or {'total': 0, 'processed': 0, 'current_file': ''}
            progress['total'] = len(media_files)

            if not media_files:
                task.status = TASK_STATUS_SUCCESS
                task.error_message = None
                self._save_task_and_update_time(task)
                return

            output_dir_path = self._output_dir(task)
            if not output_dir_path:
                task.status = TASK_STATUS_FAILED
                task.error_message = "输出目录无效"
                self._save_task_and_update_time(task)
                return

            failed_files: List[str] = []
            for index, input_path in enumerate(media_files):
                if self._should_stop(task.task_id):
                    task.status = TASK_STATUS_FAILED
                    task.error_message = "任务已被停止"
                    progress['current_file'] = ''
                    self._save_task_and_update_time(task)
                    return

                progress['current_file'] = os.path.basename(input_path)
                self._set_file(task, input_path, 'processing')
                output_mp3_path = self._mp3_path(task, input_path)
                if not output_mp3_path:
                    task.status = TASK_STATUS_FAILED
                    task.error_message = "输出目录无效"
                    self._save_task_and_update_time(task)
                    return

                if os.path.isfile(output_mp3_path) and not task.overwrite:
                    convert_ok, convert_error = True, None
                else:
                    convert_ok, convert_error = self._ffmpeg_mp3(input_path, output_mp3_path)

                progress['processed'] = index + 1
                if convert_ok:
                    self._set_file(task, input_path, 'success', output_path=output_mp3_path)
                else:
                    self._set_file(task, input_path, 'failed', error=convert_error)
                    failed_files.append(f"{os.path.basename(input_path)}: {convert_error}")
                self._save_task_and_update_time(task)

            progress['current_file'] = ''
            task.status = TASK_STATUS_FAILED if failed_files else TASK_STATUS_SUCCESS
            task.error_message = None
            if failed_files:
                preview = ', '.join(failed_files[:5])
                extra = f" 等共 {len(failed_files)} 个" if len(failed_files) > 5 else ""
                task.error_message = f"部分文件转换失败: {preview}{extra}"
            self._save_task_and_update_time(task)
        except Exception as e:
            log.error(f"[AudioConvert] 转码过程出错: {e}")
            task.status = TASK_STATUS_FAILED
            task.error_message = str(e)
            self._save_task_and_update_time(task)

    def _fill_durations_async(self, task_id: str, paths: List[str]) -> None:
        def work() -> None:
            task = self._get_task(task_id)
            if not task or not task.file_status:
                return
            updated_count = 0
            for file_path in paths:
                file_info = task.file_status.get(file_path)
                if not file_info or file_info.get('duration') is not None:
                    continue
                duration = get_media_duration(file_path)
                if duration is not None:
                    file_info['duration'] = duration
                    updated_count += 1
            if updated_count:
                self._save_task_and_update_time(task)

        _spawn(work)

    def _update_file_duration_async(self, task_id: str, file_path: str) -> None:
        task = self._get_task(task_id)
        if not task or not task.file_status or file_path not in task.file_status:
            return
        duration = get_media_duration(file_path)
        if duration is not None:
            task.file_status[file_path]['duration'] = duration
            self._save_task_and_update_time(task)

    def _ensure_output_directory(self, path: str) -> Tuple[bool, Optional[str]]:
        try:
            os.makedirs(path, exist_ok=True)
            return True, None
        except OSError as e:
            return False, str(e)

    _scan_media_files = _list_media
    _convert_file_to_mp3 = _ffmpeg_mp3
    _expected_output_path = _mp3_path


audio_convert_mgr = AudioConvertMgr()
