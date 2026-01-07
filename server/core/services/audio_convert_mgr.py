"""
音频转码管理服务
提供音频文件转码为 MP3 格式的功能
"""
import json
import os
import random
import string
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from core.log_config import app_logger
from core.models.const import (MEDIA_BASE_DIR, FFMPEG_PATH, FFMPEG_TIMEOUT, TASK_STATUS_PENDING, TASK_STATUS_PROCESSING,
                               TASK_STATUS_SUCCESS, TASK_STATUS_FAILED)
from core.utils import ensure_directory, run_subprocess_safe, get_media_duration

log = app_logger


@dataclass
class AudioConvertTask:
    """音频转码任务"""
    task_id: str
    name: str
    status: str  # pending, processing, success, failed
    directory: Optional[str] = None  # 转码目录
    output_dir: str = 'mp3'  # 输出目录名称，默认为 mp3
    overwrite: bool = True  # 是否覆盖同名文件，默认为 True
    total_files: Optional[int] = None  # 可处理的文件总数
    error_message: Optional[str] = None  # 错误信息
    progress: Optional[Dict] = None  # 转码进度 {total: int, processed: int, current_file: str}
    file_status: Optional[Dict[str, Any]] = None  # 文件状态 {file_path: {'status': 'success'|'failed'|'pending'|'processing', 'error': str?, 'size': int?, 'duration': int?}}
    create_time: float = 0  # 创建时间戳
    update_time: float = 0  # 更新时间戳


class AudioConvertMgr:
    """音频转码管理器"""

    def __init__(self):
        """初始化管理器"""
        # 确保媒体任务目录存在
        ensure_directory(MEDIA_BASE_DIR)
        self._tasks: Dict[str, AudioConvertTask] = {}
        self._stop_flags: Dict[str, bool] = {}  # 任务停止标志
        self._load_history_tasks()

    def _get_task(self, task_id: str) -> Optional[AudioConvertTask]:
        """获取任务对象，不存在返回 None"""
        return self._tasks.get(task_id)

    def _update_task_status(self,
                            task: AudioConvertTask,
                            status: str = None,
                            error_message: Optional[str] = None,
                            progress: Optional[Dict] = None):
        """更新任务状态并保存"""
        if status:
            task.status = status
        if error_message is not None:
            task.error_message = error_message
        if progress is not None:
            task.progress = progress
        task.update_time = datetime.now().timestamp()
        self._save_task(task)

    def _get_task_meta_file(self, task_id: str) -> str:
        """获取任务元数据文件路径"""
        return os.path.join(MEDIA_BASE_DIR, 'convert', f"{task_id}.json")

    def _load_history_tasks(self):
        """加载历史任务"""
        convert_dir = os.path.join(MEDIA_BASE_DIR, 'convert')
        if not os.path.exists(convert_dir):
            return

        for filename in os.listdir(convert_dir):
            if not filename.endswith('.json'):
                continue
            task_id = filename[:-5]
            meta_file = os.path.join(convert_dir, filename)
            if not os.path.isfile(meta_file):
                continue
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    self._tasks[task_id] = AudioConvertTask(**json.load(f))
            except Exception as e:
                log.error(f"[AudioConvert] 加载任务 {task_id} 失败: {e}")
        log.info(f"[AudioConvert] 加载了 {len(self._tasks)} 个历史任务")

    def _save_task(self, task: AudioConvertTask):
        """保存任务到文件"""
        try:
            ensure_directory(os.path.join(MEDIA_BASE_DIR, 'convert'))
            with open(self._get_task_meta_file(task.task_id), 'w', encoding='utf-8') as f:
                json.dump(asdict(task), f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"[AudioConvert] 保存任务 {task.task_id} 失败: {e}")

    def _generate_task_id(self) -> str:
        """生成短任务ID"""
        timestamp = int(datetime.now().timestamp())
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"{timestamp}{random_str}"

    def create_task(self,
                    name: Optional[str] = None,
                    output_dir: Optional[str] = None,
                    overwrite: Optional[bool] = None) -> Tuple[int, str, Optional[str]]:
        """创建音频转码任务"""
        try:
            name = name or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            output_dir = (output_dir or 'mp3').strip()
            if not output_dir:
                return -1, "输出目录名称不能为空", None

            task_id = self._generate_task_id()
            while task_id in self._tasks:
                task_id = self._generate_task_id()

            now = datetime.now().timestamp()
            task = AudioConvertTask(task_id=task_id,
                                    name=name,
                                    status=TASK_STATUS_PENDING,
                                    directory=None,
                                    output_dir=output_dir,
                                    overwrite=overwrite if overwrite is not None else True,
                                    create_time=now,
                                    update_time=now)
            self._tasks[task_id] = task
            self._save_task(task)
            log.info(f"[AudioConvert] 创建转码任务: {task_id}, 名称: {name}")
            return 0, "任务创建成功", task_id
        except Exception as e:
            log.error(f"[AudioConvert] 创建任务失败: {e}")
            return -1, f"创建任务失败: {str(e)}", None

    def update_task(self,
                    task_id: str,
                    name: Optional[str] = None,
                    directory: Optional[str] = None,
                    output_dir: Optional[str] = None,
                    overwrite: Optional[bool] = None) -> Tuple[int, str]:
        """更新任务信息"""
        task = self._get_task(task_id)
        if not task:
            return -1, "任务不存在"
        if task.status == TASK_STATUS_PROCESSING:
            return -1, "任务正在处理中，无法更新任务"

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
                # 更新目录后，重新扫描文件并初始化文件状态
                if task.directory:
                    media_files = self._scan_media_files(task.directory, task.output_dir)
                    task.total_files = len(media_files)
                    self._initialize_file_status(task, media_files)
                updated = True
            if output_dir is not None:
                if not output_dir.strip():
                    return -1, "输出目录名称不能为空"
                task.output_dir = output_dir.strip()
                # 更新输出目录后，重新扫描文件并初始化文件状态
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

            task.update_time = datetime.now().timestamp()
            self._save_task(task)
            return 0, "任务更新成功"
        except Exception as e:
            log.error(f"[AudioConvert] 更新任务失败: {e}")
            return -1, f"更新任务失败: {str(e)}"

    def _get_file_info(self, file_path: str) -> Dict:
        """获取文件信息（大小），时长异步获取"""
        file_info = {}
        try:
            # 获取文件大小（同步，快速）
            if os.path.exists(file_path):
                file_info['size'] = os.path.getsize(file_path)
        except Exception as e:
            log.warning(f"[AudioConvert] 获取文件大小失败 {file_path}: {e}")
        return file_info
    
    def _initialize_file_status(self, task: AudioConvertTask, media_files: List[str]):
        """初始化文件状态，保留已有文件信息"""
        if task.file_status is None:
            task.file_status = {}
        
        new_file_status = {}
        for media_file in media_files:
            if media_file in task.file_status:
                # 保留已有状态（如果任务已完成或失败，保持状态）
                old_status = task.file_status[media_file]
                if task.status in (TASK_STATUS_SUCCESS, TASK_STATUS_FAILED):
                    new_file_status[media_file] = old_status
                else:
                    # 重置状态但保留文件信息（大小、时长）
                    file_info = {'size': old_status.get('size'), 'duration': old_status.get('duration')}
                    new_file_status[media_file] = {'status': 'pending', **file_info}
            else:
                # 新文件，获取文件信息（大小），时长异步获取
                file_info = self._get_file_info(media_file)
                new_file_status[media_file] = {'status': 'pending', **file_info}
        
        task.file_status = new_file_status
        # 异步获取所有文件的时长
        self._start_async_duration_update(task.task_id, list(new_file_status.keys()))
    
    def _ensure_output_directory(self, output_dir_path: str) -> Tuple[bool, Optional[str]]:
        """确保输出目录存在且有写权限"""
        try:
            if os.path.exists(output_dir_path):
                # 目录已存在，检查写权限
                if not os.access(output_dir_path, os.W_OK):
                    error_msg = f"输出目录无写权限: {output_dir_path}"
                    log.error(f"[AudioConvert] {error_msg}")
                    return False, error_msg
            else:
                # 目录不存在，尝试创建
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
    
    def _update_file_status(self, task: AudioConvertTask, file_path: str, status: str, error: Optional[str] = None):
        """更新文件状态，保留已有文件信息"""
        old_status = task.file_status.get(file_path, {})
        new_status = {**old_status, 'status': status}
        if error is not None:
            new_status['error'] = error
        task.file_status[file_path] = new_status
    
    def _update_file_duration_async(self, task_id: str, file_path: str):
        """异步获取文件时长并更新任务"""
        try:
            duration = get_media_duration(file_path)
            if duration is not None:
                task = self._get_task(task_id)
                if task and task.file_status and file_path in task.file_status:
                    # 更新文件状态中的时长
                    file_status = task.file_status[file_path]
                    file_status['duration'] = duration
                    self._save_task(task)
                    log.debug(f"[AudioConvert] 异步更新文件时长: {file_path}, {duration}秒")
        except Exception as e:
            log.warning(f"[AudioConvert] 异步获取文件时长失败 {file_path}: {e}")
    
    def _start_async_duration_update(self, task_id: str, file_paths: List[str]):
        """启动异步获取文件时长的任务"""
        from gevent import spawn
        
        def update_durations():
            """在 gevent 协程中异步更新所有文件的时长"""
            for file_path in file_paths:
                try:
                    self._update_file_duration_async(task_id, file_path)
                except Exception as e:
                    log.warning(f"[AudioConvert] 异步更新文件时长异常 {file_path}: {e}")
        
        # 使用 gevent.spawn 异步执行，不阻塞主流程
        spawn(update_durations)

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
        """
        将单个文件转换为 MP3 格式
        
        :param input_file: 输入文件路径
        :param output_file: 输出文件路径
        :return: (是否成功, 错误消息)
        """
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        success, error_msg = self._ensure_output_directory(output_dir)
        if not success:
            return False, error_msg

        # 使用 ffmpeg 转换（支持音频和视频文件）
        cmds = [
            FFMPEG_PATH,
            '-loglevel', 'error',  # 只输出错误信息，不输出中间信息
            '-i',
            input_file,
            '-vn',  # 不处理视频流，只处理音频
            '-codec:a',
            'libmp3lame',
            '-q:a',
            '2',  # 高质量
            '-y',  # 覆盖已存在的文件
            output_file
        ]

        log.info(f"[AudioConvert] 执行 ffmpeg 命令: {' '.join(cmds)}")
        # 使用公共方法安全地运行 subprocess，避免 gevent 与 asyncio 冲突
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
            else:
                error_msg = f"输出文件不存在: {output_file}"
                log.error(f"[AudioConvert] {error_msg}")
                return False, error_msg
        else:
            error_msg = stderr or stdout or '未知错误'
            log.error(f"[AudioConvert] ffmpeg 执行失败 (返回码: {returncode}): {error_msg}")
            return False, error_msg

    def _convert_directory(self, task: AudioConvertTask):
        """在后台线程中执行转码任务"""
        self._stop_flags[task.task_id] = False
        try:
            self._update_task_status(task, TASK_STATUS_PROCESSING, None, {
                'total': 0,
                'processed': 0,
                'current_file': ''
            })

            if not task.directory or not os.path.exists(task.directory):
                self._update_task_status(task, TASK_STATUS_FAILED, "目录不存在")
                return

            media_files = self._scan_media_files(task.directory, task.output_dir)
            total = len(media_files)
            task.progress['total'] = total
            task.progress['processed'] = 0  # 重置已处理数量
            # 初始化所有文件状态为 pending
            if task.file_status is None:
                task.file_status = {}
            for media_file in media_files:
                if media_file not in task.file_status:
                    # 获取文件信息（大小），时长异步获取
                    file_info = self._get_file_info(media_file)
                    task.file_status[media_file] = {'status': 'pending', **file_info}
                else:
                    # 确保有 status 字段
                    old_status = task.file_status[media_file]
                    if 'status' not in old_status:
                        old_status['status'] = 'pending'
            self._save_task(task)
            # 异步获取所有文件的时长
            self._start_async_duration_update(task.task_id, media_files)

            if total == 0:
                self._update_task_status(task, TASK_STATUS_SUCCESS, None, {'processed': 0})
                log.info(f"[AudioConvert] 任务 {task.task_id} 完成：目录中没有媒体文件")
                return

            output_dir_path = os.path.join(task.directory, task.output_dir)
            # 检查并创建输出目录
            success, error_msg = self._ensure_output_directory(output_dir_path)
            if not success:
                self._update_task_status(task, TASK_STATUS_FAILED, error_msg)
                return

            processed = 0
            failed_files = []
            # 初始化文件状态字典
            if task.file_status is None:
                task.file_status = {}
            
            for media_file in media_files:
                if self._stop_flags.get(task.task_id, False):
                    self._update_task_status(task, TASK_STATUS_FAILED, "任务已被停止", {'current_file': ''})
                    log.info(f"[AudioConvert] 任务 {task.task_id} 被停止")
                    return

                task.progress['current_file'] = os.path.basename(media_file)
                # 标记为处理中，保留文件信息
                self._update_file_status(task, media_file, 'processing')
                self._save_task(task)

                base_name = os.path.splitext(os.path.basename(media_file))[0]
                output_file = os.path.join(output_dir_path, f"{base_name}.mp3")

                if os.path.exists(output_file) and not task.overwrite:
                    processed += 1
                    task.progress['processed'] = processed
                    self._update_file_status(task, media_file, 'success')
                    self._save_task(task)
                    continue

                success, error = self._convert_file_to_mp3(media_file, output_file)
                processed += 1
                task.progress['processed'] = processed
                
                if success:
                    self._update_file_status(task, media_file, 'success')
                else:
                    self._update_file_status(task, media_file, 'failed', error)
                    failed_files.append(f"{os.path.basename(media_file)}: {error}")
                self._save_task(task)

            if self._stop_flags.get(task.task_id, False):
                self._update_task_status(task, TASK_STATUS_FAILED, "任务已被停止", {'current_file': ''})
                return

            status = TASK_STATUS_SUCCESS if processed == total else TASK_STATUS_FAILED
            error_msg = None if processed == total else (
                f"部分文件转换失败: {', '.join(failed_files[:5])}" +
                (f" 等共 {len(failed_files)} 个文件" if len(failed_files) > 5 else ""))
            self._update_task_status(task, status, error_msg, {'current_file': ''})
            log.info(f"[AudioConvert] 任务 {task.task_id} 完成: 成功 {processed}/{total}")

        except Exception as e:
            log.error(f"[AudioConvert] 转码过程出错: {e}")
            self._update_task_status(task, TASK_STATUS_FAILED, f"转码过程出错: {str(e)}")
        finally:
            self._stop_flags.pop(task.task_id, None)

    def start_task(self, task_id: str) -> Tuple[int, str]:
        """开始转码任务"""
        task = self._get_task(task_id)
        if not task:
            return -1, "任务不存在"
        if task.status == TASK_STATUS_PROCESSING:
            return -1, "任务正在处理中"
        if not task.directory:
            return -1, "请先设置转码目录"

        threading.Thread(target=self._convert_directory, args=(task, ), daemon=True).start()
        log.info(f"[AudioConvert] 启动转码任务: {task_id}")
        return 0, "转码任务已启动"

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务信息"""
        task = self._get_task(task_id)
        return asdict(task) if task else None

    def get_task_list(self) -> List[Dict]:
        """获取所有任务列表"""
        return [asdict(task) for task in self._tasks.values()]

    def delete_task(self, task_id: str) -> Tuple[int, str]:
        """删除任务（可以删除正在执行的任务，会停止执行）"""
        task = self._get_task(task_id)
        if not task:
            return -1, "任务不存在"

        if task.status == TASK_STATUS_PROCESSING:
            self._stop_flags[task.task_id] = True
            log.info(f"[AudioConvert] 设置任务 {task_id} 停止标志")

        meta_file = self._get_task_meta_file(task_id)
        if os.path.exists(meta_file):
            try:
                os.remove(meta_file)
            except Exception as e:
                log.warning(f"[AudioConvert] 删除元数据文件失败: {e}")

        del self._tasks[task_id]
        self._stop_flags.pop(task_id, None)
        log.info(f"[AudioConvert] 删除任务: {task_id}")
        return 0, "任务删除成功"


# 创建全局实例
audio_convert_mgr = AudioConvertMgr()
