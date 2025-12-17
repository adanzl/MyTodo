"""
媒体工具管理服务
提供音频合成等功能
"""
import os
import json
import subprocess
import threading
import shutil
import random
import string
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime

from core.log_config import root_logger
from core.models.const import (
    MEDIA_BASE_DIR,
    MEDIA_TASK_DIR,
    get_media_task_dir,
    get_media_task_result_dir,
    ALLOWED_AUDIO_EXTENSIONS
)
from core.utils import get_media_duration

log = root_logger()

# 任务状态
TASK_STATUS_PENDING = 'pending'  # 等待中
TASK_STATUS_PROCESSING = 'processing'  # 处理中
TASK_STATUS_SUCCESS = 'success'  # 成功
TASK_STATUS_FAILED = 'failed'  # 失败


@dataclass
class AudioMergeTask:
    """音频合成任务"""
    task_id: str
    name: str
    status: str  # pending, processing, success, failed
    files: List[Dict]  # 文件列表，每个文件包含 name, path, size 等信息
    result_file: Optional[str] = None  # 结果文件路径
    error_message: Optional[str] = None  # 错误信息
    create_time: float = 0  # 创建时间戳
    update_time: float = 0  # 更新时间戳


class MediaToolMgr:
    """媒体工具管理器"""
    
    TASK_META_FILE = 'task.json'  # 任务元数据文件名
    MERGED_FILENAME = 'merged.mp3'  # 合并后的文件名
    FFMPEG_TIMEOUT = 300  # ffmpeg 超时时间（秒）
    
    def __init__(self):
        """初始化管理器"""
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
                log.warning("[MediaTool] task.json 格式错误，应为字典格式")
                return
            
            loaded_count = 0
            for task_id, task_data in all_tasks_data.items():
                try:
                    task_dir = get_media_task_dir(task_id)
                    if not os.path.exists(task_dir):
                        log.warning(f"[MediaTool] 任务目录不存在: {task_id}")
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
                    task = AudioMergeTask(
                        task_id=task_id,
                        name=task_data.get('name', '未命名任务'),
                        status=task_data.get('status', TASK_STATUS_PENDING),
                        files=files,
                        result_file=result_file,
                        error_message=task_data.get('error_message'),
                        create_time=task_data.get('create_time', 0),
                        update_time=task_data.get('update_time', 0)
                    )
                    
                    self._tasks[task_id] = task
                    loaded_count += 1
                    log.info(f"[MediaTool] 加载历史任务: {task_id}, 名称: {task.name}, 状态: {task.status}")
                    
                except Exception as e:
                    log.error(f"[MediaTool] 加载任务失败 {task_id}: {e}")
                    continue
            
            log.info(f"[MediaTool] 共加载 {loaded_count} 个历史任务")
            
        except json.JSONDecodeError as e:
            log.error(f"[MediaTool] 解析 task.json 失败: {e}")
        except Exception as e:
            log.error(f"[MediaTool] 加载历史任务失败: {e}")
    
    def _save_all_tasks(self):
        """保存所有任务到统一的 task.json 文件"""
        try:
            task_meta_file = os.path.join(MEDIA_BASE_DIR, self.TASK_META_FILE)
            os.makedirs(MEDIA_BASE_DIR, exist_ok=True)
            
            all_tasks_data = {
                task_id: asdict(task)
                for task_id, task in self._tasks.items()
            }
            
            with open(task_meta_file, 'w', encoding='utf-8') as f:
                json.dump(all_tasks_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            log.error(f"[MediaTool] 保存所有任务失败: {e}")
    
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
            task = AudioMergeTask(
                task_id=task_id,
                name=name,
                status=TASK_STATUS_PENDING,
                files=[],
                create_time=datetime.now().timestamp(),
                update_time=datetime.now().timestamp()
            )
            
            self._tasks[task_id] = task
            self._save_all_tasks()
            
            log.info(f"[MediaTool] 创建音频合成任务: {task_id}, 名称: {name}")
            return 0, "任务创建成功", task_id
            
        except Exception as e:
            error_msg = f"创建任务失败: {str(e)}"
            log.error(f"[MediaTool] {error_msg}")
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
            self._update_task_time(task)
            self._save_all_tasks()
            
            log.info(f"[MediaTool] 添加文件到任务 {task_id}: {filename}")
            return 0, "文件添加成功"
            
        except Exception as e:
            error_msg = f"添加文件失败: {str(e)}"
            log.error(f"[MediaTool] {error_msg}")
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
            self._update_task_time(task)
            self._save_all_tasks()
            
            log.info(f"[MediaTool] 从任务 {task_id} 移除文件: {removed_file['name']}")
            return 0, "文件移除成功"
            
        except Exception as e:
            error_msg = f"移除文件失败: {str(e)}"
            log.error(f"[MediaTool] {error_msg}")
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
            self._update_task_time(task)
            self._save_all_tasks()
            
            log.info(f"[MediaTool] 调整任务 {task_id} 的文件顺序")
            return 0, "文件顺序调整成功"
            
        except Exception as e:
            error_msg = f"调整文件顺序失败: {str(e)}"
            log.error(f"[MediaTool] {error_msg}")
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
            self._update_task_time(task)
            self._save_all_tasks()
            
            # 在后台线程中执行合成
            def merge_thread():
                try:
                    result_file = self._merge_audio_files(task_id, task.files)
                    if result_file:
                        task.status = TASK_STATUS_SUCCESS
                        task.result_file = result_file
                        log.info(f"[MediaTool] 任务 {task_id} 合成成功: {result_file}")
                    else:
                        task.status = TASK_STATUS_FAILED
                        task.error_message = "合成失败"
                        log.error(f"[MediaTool] 任务 {task_id} 合成失败")
                except Exception as e:
                    task.status = TASK_STATUS_FAILED
                    task.error_message = str(e)
                    log.error(f"[MediaTool] 任务 {task_id} 合成异常: {e}")
                finally:
                    self._update_task_time(task)
                    self._save_all_tasks()
            
            threading.Thread(target=merge_thread, daemon=True).start()
            
            return 0, "任务已开始处理"
            
        except Exception as e:
            error_msg = f"启动任务失败: {str(e)}"
            log.error(f"[MediaTool] {error_msg}")
            return -1, error_msg
    
    def _merge_audio_files(self, task_id: str, files: List[Dict]) -> Optional[str]:
        """
        使用 ffmpeg 合并音频文件
        
        :param task_id: 任务ID
        :param files: 文件列表
        :return: 结果文件路径，失败返回 None
        """
        if not files:
            return None
        
        try:
            result_dir = get_media_task_result_dir(task_id)
            result_file = os.path.join(result_dir, self.MERGED_FILENAME)
            
            # 如果只有一个文件，直接复制
            if len(files) == 1:
                shutil.copy2(files[0]['path'], result_file)
                return result_file
            
            # 创建文件列表文件（用于 ffmpeg concat）
            file_list_path = os.path.join(get_media_task_dir(task_id), 'file_list.txt')
            with open(file_list_path, 'w', encoding='utf-8') as f:
                for file_info in files:
                    file_path = file_info['path'].replace("'", "'\\''")
                    f.write(f"file '{file_path}'\n")
            
            # 使用 ffmpeg 合并
            cmds = [
                '/usr/bin/ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', file_list_path,
                '-c', 'copy',
                '-y',
                result_file
            ]
            
            log.info(f"[MediaTool] 执行 ffmpeg 命令: {' '.join(cmds)}")
            result = subprocess.run(cmds, capture_output=True, text=True, timeout=self.FFMPEG_TIMEOUT)
            
            if result.returncode == 0 and os.path.exists(result_file):
                return result_file
            
            log.error(f"[MediaTool] ffmpeg 执行失败: {result.stderr if result.returncode != 0 else '文件不存在'}")
            return None
                
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            log.error(f"[MediaTool] ffmpeg 执行失败: {' '.join(cmds)} error: {e}")
            return None
        except Exception as e:
            log.error(f"[MediaTool] 合并音频文件失败: {e}")
            return None
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        获取任务信息
        
        :param task_id: 任务ID
        :return: 任务字典，不存在返回 None
        """
        task = self._get_task(task_id)
        return asdict(task) if task else None
    
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
            
            log.info(f"[MediaTool] 删除任务: {task_id}")
            return 0, "任务删除成功"
            
        except Exception as e:
            error_msg = f"删除任务失败: {str(e)}"
            log.error(f"[MediaTool] {error_msg}")
            return -1, error_msg


# 创建全局实例
media_tool_mgr = MediaToolMgr()
