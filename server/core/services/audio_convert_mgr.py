"""
音频转码管理服务
提供音频文件转码为 MP3 格式的功能
"""
import json
import os
import random
import shutil
import string
import subprocess
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.log_config import app_logger
from core.models.const import MEDIA_BASE_DIR, FFMPEG_PATH
from core.utils import ensure_directory, is_allowed_audio_file

log = app_logger

# 任务状态
TASK_STATUS_PENDING = 'pending'  # 等待中
TASK_STATUS_PROCESSING = 'processing'  # 处理中
TASK_STATUS_SUCCESS = 'success'  # 成功
TASK_STATUS_FAILED = 'failed'  # 失败


@dataclass
class AudioConvertTask:
    """音频转码任务"""
    task_id: str
    name: str
    status: str  # pending, processing, success, failed
    directory: Optional[str] = None  # 转码目录
    output_dir: str = 'mp3'  # 输出目录名称，默认为 mp3
    error_message: Optional[str] = None  # 错误信息
    progress: Optional[Dict] = None  # 转码进度 {total: int, processed: int, current_file: str}
    create_time: float = 0  # 创建时间戳
    update_time: float = 0  # 更新时间戳


class AudioConvertMgr:
    """音频转码管理器"""

    TASK_META_FILE = 'audio_convert_task.json'  # 任务元数据文件名
    DEFAULT_OUTPUT_DIR = 'mp3'  # 默认输出目录名称
    FFMPEG_TIMEOUT = 300  # ffmpeg 超时时间（秒）

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

    def _validate_task_exists(self, task_id: str) -> Tuple[Optional[AudioConvertTask], Optional[str]]:
        """
        验证任务是否存在
        
        :return: (任务对象, 错误消息)，如果任务不存在则返回 (None, 错误消息)
        """
        task = self._get_task(task_id)
        if not task:
            return None, "任务不存在"
        return task, None

    def _validate_task_not_processing(self, task: AudioConvertTask, operation: str) -> Optional[str]:
        """
        验证任务是否不在处理中
        
        :param task: 任务对象
        :param operation: 操作名称
        :return: 错误消息，如果验证通过返回 None
        """
        if task.status == TASK_STATUS_PROCESSING:
            return f"任务正在处理中，无法{operation}"
        return None

    def _get_task_dir(self, task_id: str) -> str:
        """获取任务目录"""
        return os.path.join(MEDIA_BASE_DIR, 'convert', task_id)

    def _get_task_meta_file(self, task_id: str) -> str:
        """获取任务元数据文件路径"""
        return os.path.join(self._get_task_dir(task_id), self.TASK_META_FILE)

    def _load_history_tasks(self):
        """加载历史任务"""
        try:
            convert_dir = os.path.join(MEDIA_BASE_DIR, 'convert')
            if not os.path.exists(convert_dir):
                return

            for task_id in os.listdir(convert_dir):
                task_dir = os.path.join(convert_dir, task_id)
                if not os.path.isdir(task_dir):
                    continue

                meta_file = self._get_task_meta_file(task_id)
                if not os.path.exists(meta_file):
                    continue

                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)
                        task = AudioConvertTask(**task_data)
                        self._tasks[task_id] = task
                except Exception as e:
                    log.error(f"[AudioConvert] 加载任务 {task_id} 失败: {e}")

            log.info(f"[AudioConvert] 加载了 {len(self._tasks)} 个历史任务")
        except Exception as e:
            log.error(f"[AudioConvert] 加载历史任务失败: {e}")

    def _save_task(self, task: AudioConvertTask):
        """保存任务到文件"""
        try:
            task_dir = self._get_task_dir(task.task_id)
            ensure_directory(task_dir)
            meta_file = self._get_task_meta_file(task.task_id)

            task_data = asdict(task)
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"[AudioConvert] 保存任务 {task.task_id} 失败: {e}")

    def _save_all_tasks(self):
        """保存所有任务"""
        try:
            for task in self._tasks.values():
                self._save_task(task)
        except Exception as e:
            log.error(f"[AudioConvert] 保存所有任务失败: {e}")

    def _generate_task_id(self) -> str:
        """生成短任务ID"""
        timestamp = int(datetime.now().timestamp())
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"{timestamp}{random_str}"

    def create_task(self,
                    name: Optional[str] = None,
                    output_dir: Optional[str] = None) -> Tuple[int, str, Optional[str]]:
        """
        创建音频转码任务
        
        :param name: 任务名称，如果为 None 则使用默认日期时间
        :param output_dir: 输出目录名称，如果为 None 则使用默认值 'mp3'
        :return: (错误码, 消息, 任务ID)，0 表示成功
        """
        try:
            # 如果没有提供名称，使用当前日期时间作为默认名称
            if not name:
                name = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # 如果没有提供输出目录名称，使用默认值
            if not output_dir:
                output_dir = self.DEFAULT_OUTPUT_DIR
            # 验证输出目录名称
            if not output_dir.strip():
                return -1, "输出目录名称不能为空", None
            output_dir = output_dir.strip()
            # 生成唯一任务ID
            task_id = self._generate_task_id()
            while task_id in self._tasks:
                task_id = self._generate_task_id()

            # 创建任务目录
            task_dir = self._get_task_dir(task_id)
            os.makedirs(task_dir, exist_ok=True)

            # 创建任务对象
            task = AudioConvertTask(task_id=task_id,
                                    name=name,
                                    status=TASK_STATUS_PENDING,
                                    directory=None,
                                    output_dir=output_dir,
                                    create_time=datetime.now().timestamp(),
                                    update_time=datetime.now().timestamp())

            self._tasks[task_id] = task
            self._save_task(task)

            log.info(f"[AudioConvert] 创建转码任务: {task_id}, 名称: {name}")
            return 0, "任务创建成功", task_id

        except Exception as e:
            error_msg = f"创建任务失败: {str(e)}"
            log.error(f"[AudioConvert] {error_msg}")
            return -1, error_msg, None

    def set_directory(self, task_id: str, directory: str) -> Tuple[int, str]:
        """
        设置转码目录（已废弃，请使用 update_task）
        
        :param task_id: 任务ID
        :param directory: 目录路径
        :return: (错误码, 消息)，0 表示成功
        """
        return self.update_task(task_id, directory=directory)

    def update_task(self,
                    task_id: str,
                    name: Optional[str] = None,
                    directory: Optional[str] = None,
                    output_dir: Optional[str] = None) -> Tuple[int, str]:
        """
        更新任务信息
        
        :param task_id: 任务ID
        :param name: 任务名称（可选）
        :param directory: 目录路径（可选）
        :param output_dir: 输出目录名称（可选）
        :return: (错误码, 消息)，0 表示成功
        """
        task, error = self._validate_task_exists(task_id)
        if error:
            return -1, error

        error = self._validate_task_not_processing(task, "更新任务")
        if error:
            return -1, error

        try:
            updated = False

            # 更新任务名称
            if name is not None:
                if not name.strip():
                    return -1, "任务名称不能为空"
                task.name = name.strip()
                updated = True
                log.info(f"[AudioConvert] 更新任务 {task_id} 名称: {name}")

            # 更新目录
            if directory is not None:
                # 验证目录是否存在
                if not os.path.exists(directory):
                    return -1, "目录不存在"
                if not os.path.isdir(directory):
                    return -1, "路径不是目录"
                task.directory = directory
                updated = True
                log.info(f"[AudioConvert] 更新任务 {task_id} 目录: {directory}")

            # 更新输出目录名称
            if output_dir is not None:
                if not output_dir.strip():
                    return -1, "输出目录名称不能为空"
                task.output_dir = output_dir.strip()
                updated = True
                log.info(f"[AudioConvert] 更新任务 {task_id} 输出目录名称: {output_dir}")

            if not updated:
                return -1, "没有提供要更新的字段"

            task.update_time = datetime.now().timestamp()
            self._save_task(task)

            return 0, "任务更新成功"
        except Exception as e:
            error_msg = f"更新任务失败: {str(e)}"
            log.error(f"[AudioConvert] {error_msg}")
            return -1, error_msg

    def _scan_audio_files(self, directory: str, output_dir: str) -> List[str]:
        """
        扫描目录下的所有音频文件
        
        :param directory: 目录路径
        :param output_dir: 输出目录名称，用于跳过输出目录
        :return: 音频文件路径列表
        """
        audio_files = []
        try:
            for root, dirs, files in os.walk(directory):
                # 跳过输出目录
                if output_dir in root:
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    if is_allowed_audio_file(file_path):
                        audio_files.append(file_path)
        except Exception as e:
            log.error(f"[AudioConvert] 扫描目录失败: {e}")
        return audio_files

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
            os.makedirs(output_dir, exist_ok=True)

            # 使用 ffmpeg 转换
            cmds = [
                FFMPEG_PATH,
                '-i',
                input_file,
                '-codec:a',
                'libmp3lame',
                '-q:a',
                '2',  # 高质量
                '-y',  # 覆盖已存在的文件
                output_file
            ]

            log.info(f"[AudioConvert] 执行 ffmpeg 命令: {' '.join(cmds)}")
            result = subprocess.run(cmds, capture_output=True, text=True, timeout=self.FFMPEG_TIMEOUT)

            if result.returncode == 0 and os.path.exists(output_file):
                return True, None
            else:
                error_msg = result.stderr if result.returncode != 0 else '文件不存在'
                log.error(f"[AudioConvert] ffmpeg 执行失败: {error_msg}")
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
        """
        在后台线程中执行转码任务
        
        :param task: 任务对象
        """
        try:
            task.status = TASK_STATUS_PROCESSING
            task.error_message = None
            task.progress = {'total': 0, 'processed': 0, 'current_file': ''}
            task.update_time = datetime.now().timestamp()
            self._save_task(task)

            if not task.directory or not os.path.exists(task.directory):
                task.status = TASK_STATUS_FAILED
                task.error_message = "目录不存在"
                task.update_time = datetime.now().timestamp()
                self._save_task(task)
                return

            # 扫描音频文件
            audio_files = self._scan_audio_files(task.directory, task.output_dir)
            total = len(audio_files)
            task.progress['total'] = total
            self._save_task(task)

            if total == 0:
                task.status = TASK_STATUS_SUCCESS
                task.progress['processed'] = 0
                task.update_time = datetime.now().timestamp()
                self._save_task(task)
                log.info(f"[AudioConvert] 任务 {task.task_id} 完成：目录中没有音频文件")
                return

            # 创建输出目录
            output_dir_path = os.path.join(task.directory, task.output_dir)
            os.makedirs(output_dir_path, exist_ok=True)

            # 转换每个文件
            processed = 0
            failed_files = []

            for audio_file in audio_files:
                try:
                    # 更新当前处理文件
                    task.progress['current_file'] = os.path.basename(audio_file)
                    self._save_task(task)

                    # 生成输出文件名（保持原文件名，但扩展名为 .mp3）
                    base_name = os.path.splitext(os.path.basename(audio_file))[0]
                    output_file = os.path.join(output_dir_path, f"{base_name}.mp3")

                    # 如果输出文件已存在，跳过
                    if os.path.exists(output_file):
                        log.info(f"[AudioConvert] 文件已存在，跳过: {output_file}")
                        processed += 1
                        task.progress['processed'] = processed
                        self._save_task(task)
                        continue

                    # 转换文件
                    success, error = self._convert_file_to_mp3(audio_file, output_file)
                    if success:
                        processed += 1
                        task.progress['processed'] = processed
                        self._save_task(task)
                        log.info(f"[AudioConvert] 转换成功: {audio_file} -> {output_file}")
                    else:
                        failed_files.append(f"{os.path.basename(audio_file)}: {error}")
                        log.error(f"[AudioConvert] 转换失败: {audio_file}, 错误: {error}")

                except Exception as e:
                    failed_files.append(f"{os.path.basename(audio_file)}: {str(e)}")
                    log.error(f"[AudioConvert] 处理文件失败: {audio_file}, 错误: {e}")

            # 更新任务状态
            if processed == total:
                task.status = TASK_STATUS_SUCCESS
                task.error_message = None
            else:
                task.status = TASK_STATUS_FAILED
                task.error_message = f"部分文件转换失败: {', '.join(failed_files[:5])}"  # 只显示前5个错误
                if len(failed_files) > 5:
                    task.error_message += f" 等共 {len(failed_files)} 个文件"

            task.progress['current_file'] = ''
            task.update_time = datetime.now().timestamp()
            self._save_task(task)

            log.info(f"[AudioConvert] 任务 {task.task_id} 完成: 成功 {processed}/{total}")

        except Exception as e:
            error_msg = f"转码过程出错: {str(e)}"
            log.error(f"[AudioConvert] {error_msg}")
            task.status = TASK_STATUS_FAILED
            task.error_message = error_msg
            task.update_time = datetime.now().timestamp()
            self._save_task(task)

    def start_task(self, task_id: str) -> Tuple[int, str]:
        """
        开始转码任务
        
        :param task_id: 任务ID
        :return: (错误码, 消息)，0 表示成功
        """
        task, error = self._validate_task_exists(task_id)
        if error:
            return -1, error

        if task.status == TASK_STATUS_PROCESSING:
            return -1, "任务正在处理中"

        if not task.directory:
            return -1, "请先设置转码目录"

        try:
            # 在后台线程中执行转码
            thread = threading.Thread(target=self._convert_directory, args=(task, ), daemon=True)
            thread.start()

            log.info(f"[AudioConvert] 启动转码任务: {task_id}")
            return 0, "转码任务已启动"
        except Exception as e:
            error_msg = f"启动任务失败: {str(e)}"
            log.error(f"[AudioConvert] {error_msg}")
            return -1, error_msg

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        获取任务信息
        
        :param task_id: 任务ID
        :return: 任务字典，不存在返回 None
        """
        task = self._get_task(task_id)
        if not task:
            return None
        return asdict(task)

    def get_task_list(self) -> List[Dict]:
        """
        获取所有任务列表
        
        :return: 任务列表
        """
        return [asdict(task) for task in self._tasks.values()]

    def delete_task(self, task_id: str) -> Tuple[int, str]:
        """
        删除任务
        
        :param task_id: 任务ID
        :return: (错误码, 消息)，0 表示成功
        """
        task, error = self._validate_task_exists(task_id)
        if error:
            return -1, error

        error = self._validate_task_not_processing(task, "删除")
        if error:
            return -1, error

        try:
            # 删除任务目录
            task_dir = self._get_task_dir(task_id)
            if os.path.exists(task_dir):
                shutil.rmtree(task_dir)

            # 从内存中删除
            del self._tasks[task_id]

            log.info(f"[AudioConvert] 删除任务: {task_id}")
            return 0, "任务删除成功"
        except Exception as e:
            error_msg = f"删除任务失败: {str(e)}"
            log.error(f"[AudioConvert] {error_msg}")
            return -1, error_msg


# 创建全局实例
audio_convert_mgr = AudioConvertMgr()
