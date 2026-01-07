"""
音频转码管理服务
提供音频文件转码为 MP3 格式的功能
"""
import json
import os
import random
import string
import subprocess
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.log_config import app_logger
from core.models.const import (MEDIA_BASE_DIR, FFMPEG_PATH, FFMPEG_TIMEOUT, TASK_STATUS_PENDING, TASK_STATUS_PROCESSING,
                               TASK_STATUS_SUCCESS, TASK_STATUS_FAILED)
from core.utils import ensure_directory

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
                # 更新目录后，重新计算文件数量
                if task.directory:
                    task.total_files = len(self._scan_media_files(task.directory, task.output_dir))
                updated = True
            if output_dir is not None:
                if not output_dir.strip():
                    return -1, "输出目录名称不能为空"
                task.output_dir = output_dir.strip()
                # 更新输出目录后，重新计算文件数量
                if task.directory:
                    task.total_files = len(self._scan_media_files(task.directory, task.output_dir))
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
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            try:
                if os.path.exists(output_dir):
                    # 目录已存在，检查写权限
                    if not os.access(output_dir, os.W_OK):
                        error_msg = f"输出目录无写权限: {output_dir}"
                        log.error(f"[AudioConvert] {error_msg}")
                        return False, error_msg
                else:
                    # 目录不存在，尝试创建
                    os.makedirs(output_dir, exist_ok=True)
            except PermissionError as e:
                error_msg = f"无法创建输出目录，权限不足: {output_dir}"
                log.error(f"[AudioConvert] {error_msg}: {e}")
                return False, error_msg
            except OSError as e:
                error_msg = f"无法创建输出目录: {output_dir}"
                log.error(f"[AudioConvert] {error_msg}: {e}")
                return False, error_msg

            # 使用 ffmpeg 转换（支持音频和视频文件）
            cmds = [
                FFMPEG_PATH,
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
            result = subprocess.run(cmds, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)

            if result.returncode == 0:
                if os.path.exists(output_file):
                    log.info(f"[AudioConvert] 转换成功: {input_file} -> {output_file}")
                    return True, None
                else:
                    error_msg = f"输出文件不存在: {output_file}"
                    log.error(f"[AudioConvert] {error_msg}")
                    return False, error_msg
            else:
                error_msg = result.stderr or result.stdout or '未知错误'
                log.error(f"[AudioConvert] ffmpeg 执行失败 (返回码: {result.returncode}): {error_msg}")
                return False, error_msg

        except subprocess.TimeoutExpired:
            error_msg = "转换超时"
            log.error(f"[AudioConvert] {error_msg}")
            return False, error_msg
        except FileNotFoundError:
            error_msg = "ffmpeg 未找到，请确保已安装 ffmpeg"
            log.error(f"[AudioConvert] {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"转换失败: {str(e)}"
            log.error(f"[AudioConvert] {error_msg}")
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
            self._save_task(task)

            if total == 0:
                self._update_task_status(task, TASK_STATUS_SUCCESS, None, {'processed': 0})
                log.info(f"[AudioConvert] 任务 {task.task_id} 完成：目录中没有媒体文件")
                return

            output_dir_path = os.path.join(task.directory, task.output_dir)
            # 检查并创建输出目录
            try:
                if os.path.exists(output_dir_path):
                    # 目录已存在，检查写权限
                    if not os.access(output_dir_path, os.W_OK):
                        error_msg = f"输出目录无写权限: {output_dir_path}"
                        log.error(f"[AudioConvert] {error_msg}")
                        self._update_task_status(task, TASK_STATUS_FAILED, error_msg)
                        return
                else:
                    # 目录不存在，尝试创建
                    try:
                        os.makedirs(output_dir_path, exist_ok=True)
                    except PermissionError as e:
                        error_msg = f"无法创建输出目录，权限不足: {output_dir_path}"
                        log.error(f"[AudioConvert] {error_msg}: {e}")
                        self._update_task_status(task, TASK_STATUS_FAILED, error_msg)
                        return
                    except OSError as e:
                        error_msg = f"无法创建输出目录: {output_dir_path}"
                        log.error(f"[AudioConvert] {error_msg}: {e}")
                        self._update_task_status(task, TASK_STATUS_FAILED, error_msg)
                        return
            except Exception as e:
                error_msg = f"检查输出目录时出错: {output_dir_path}"
                log.error(f"[AudioConvert] {error_msg}: {e}")
                self._update_task_status(task, TASK_STATUS_FAILED, error_msg)
                return

            processed = 0
            failed_files = []
            for media_file in media_files:
                if self._stop_flags.get(task.task_id, False):
                    self._update_task_status(task, TASK_STATUS_FAILED, "任务已被停止", {'current_file': ''})
                    log.info(f"[AudioConvert] 任务 {task.task_id} 被停止")
                    return

                task.progress['current_file'] = os.path.basename(media_file)
                self._save_task(task)

                base_name = os.path.splitext(os.path.basename(media_file))[0]
                output_file = os.path.join(output_dir_path, f"{base_name}.mp3")

                if os.path.exists(output_file) and not task.overwrite:
                    processed += 1
                    task.progress['processed'] = processed
                    self._save_task(task)
                    continue

                success, error = self._convert_file_to_mp3(media_file, output_file)
                if success:
                    processed += 1
                    task.progress['processed'] = processed
                    self._save_task(task)
                else:
                    failed_files.append(f"{os.path.basename(media_file)}: {error}")

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
