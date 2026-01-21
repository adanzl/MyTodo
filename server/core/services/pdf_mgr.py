"""
PDF 管理服务
提供 PDF 文件上传、解密、列表等功能
采用任务模式，每个文件对应一个任务，支持异步解密处理
"""
import os
import json
import threading
from typing import Optional, Tuple, Dict, List, Any, TypedDict, Protocol
from dataclasses import dataclass, asdict
from datetime import datetime
from werkzeug.utils import secure_filename

import pikepdf

from core.config import app_logger
from core.config import (PDF_BASE_DIR, PDF_UPLOAD_DIR, PDF_UNLOCK_DIR, TASK_STATUS_PENDING, TASK_STATUS_PROCESSING,
                         TASK_STATUS_SUCCESS, TASK_STATUS_FAILED, TASK_STATUS_UPLOADED)
from core.utils import ensure_directory, get_file_info, is_allowed_pdf_file

log = app_logger


class FileLike(Protocol):

    def save(self, dst: str) -> Any:
        ...


class PdfFileInfo(TypedDict, total=False):
    name: str
    path: str
    size: int
    modified: float


class PdfTaskInfo(TypedDict, total=False):
    task_id: str
    filename: str
    status: str
    uploaded_info: PdfFileInfo
    unlocked_info: Optional[PdfFileInfo]
    error_message: Optional[str]
    create_time: float
    update_time: float


@dataclass
class PdfTask:
    """PDF 任务"""
    task_id: str  # 任务ID（使用文件名）
    filename: str  # 文件名
    status: str  # 任务状态：uploaded, pending, processing, success, failed
    uploaded_path: str  # 上传文件路径
    uploaded_info: PdfFileInfo  # 上传文件信息（name, path, size, modified）
    unlocked_path: Optional[str] = None  # 已解密文件路径
    unlocked_info: Optional[PdfFileInfo] = None  # 已解密文件信息
    error_message: Optional[str] = None  # 错误信息
    create_time: float = 0  # 创建时间戳
    update_time: float = 0  # 更新时间戳


class PdfMgr:
    """PDF 管理器（任务模式）"""

    TASK_META_FILE = 'tasks.json'  # 任务元数据文件名

    def __init__(self) -> None:
        """初始化管理器"""
        self._tasks: Dict[str, PdfTask] = {}  # key: task_id (filename)
        self._task_lock = threading.Lock()  # 任务操作锁
        self._load_history_tasks()

    def _get_task(self, task_id: str) -> Optional[PdfTask]:
        """获取任务对象，不存在返回 None"""
        return self._tasks.get(task_id)

    def _task_to_dict(self, task: PdfTask) -> PdfTaskInfo:
        """将任务对象转换为字典"""
        return {
            "task_id": task.task_id,
            "filename": task.filename,
            "status": task.status,
            "uploaded_info": task.uploaded_info,
            "unlocked_info": task.unlocked_info,
            "error_message": task.error_message,
            "create_time": task.create_time,
            "update_time": task.update_time
        }

    def _get_unlocked_path(self, task_id: str) -> str:
        """获取已解密文件路径"""
        base_name, ext = os.path.splitext(task_id)
        unlocked_filename = f"{base_name}_unlocked{ext}"
        return os.path.join(PDF_UNLOCK_DIR, unlocked_filename)

    def _update_unlocked_file_info(self, task: PdfTask) -> None:
        """更新任务的已解密文件信息"""
        if task.unlocked_path and os.path.exists(task.unlocked_path):
            unlocked_info = get_file_info(task.unlocked_path)
            if unlocked_info:
                task.unlocked_info = unlocked_info
                if task.status != TASK_STATUS_PROCESSING:
                    task.status = TASK_STATUS_SUCCESS
            else:
                task.unlocked_path = None
                task.unlocked_info = None
                if task.status == TASK_STATUS_SUCCESS:
                    task.status = TASK_STATUS_UPLOADED
        else:
            # 检查是否有对应的已解密文件
            unlocked_path = self._get_unlocked_path(task.task_id)
            if os.path.exists(unlocked_path):
                unlocked_info = get_file_info(unlocked_path)
                if unlocked_info:
                    task.unlocked_path = unlocked_path
                    task.unlocked_info = unlocked_info
                    if task.status != TASK_STATUS_PROCESSING:
                        task.status = TASK_STATUS_SUCCESS
            else:
                task.unlocked_path = None
                task.unlocked_info = None
                if task.status == TASK_STATUS_SUCCESS:
                    task.status = TASK_STATUS_UPLOADED

    def _load_history_tasks(self) -> None:
        """加载历史任务"""
        try:
            if not os.path.exists(PDF_BASE_DIR):
                return

            task_meta_file = os.path.join(PDF_BASE_DIR, self.TASK_META_FILE)
            if not os.path.exists(task_meta_file):
                return

            with open(task_meta_file, 'r', encoding='utf-8') as f:
                all_tasks_data = json.load(f)

            if not isinstance(all_tasks_data, dict):
                log.warning("[PDF] tasks.json 格式错误，应为字典格式")
                return

            loaded_count = 0
            for task_id, task_data in all_tasks_data.items():
                try:
                    # 验证上传文件是否存在
                    uploaded_path = task_data.get('uploaded_path')
                    if not uploaded_path or not os.path.exists(uploaded_path):
                        log.warning(f"[PDF] 上传文件不存在: {task_id}")
                        continue

                    # 重新获取上传文件信息
                    uploaded_info = get_file_info(uploaded_path)
                    if not uploaded_info:
                        log.warning(f"[PDF] 无法获取上传文件信息: {task_id}")
                        continue

                    # 验证已解密文件是否存在
                    unlocked_path = task_data.get('unlocked_path')
                    unlocked_info = None
                    status = task_data.get('status', TASK_STATUS_UPLOADED)
                    if unlocked_path and os.path.exists(unlocked_path):
                        unlocked_info = get_file_info(unlocked_path)
                        if unlocked_info:
                            status = TASK_STATUS_SUCCESS
                        else:
                            status = TASK_STATUS_UPLOADED
                    elif status == TASK_STATUS_PROCESSING:
                        # 如果之前是处理中状态，重置为已上传
                        status = TASK_STATUS_UPLOADED

                    # 创建任务对象
                    task = PdfTask(task_id=task_id,
                                   filename=task_data.get('filename', task_id),
                                   status=status,
                                   uploaded_path=uploaded_path,
                                   uploaded_info=uploaded_info,
                                   unlocked_path=unlocked_path if unlocked_info else None,
                                   unlocked_info=unlocked_info,
                                   error_message=task_data.get('error_message'),
                                   create_time=task_data.get('create_time', 0),
                                   update_time=task_data.get('update_time', 0))

                    self._tasks[task_id] = task
                    loaded_count += 1
                    log.info(f"[PDF] 加载历史任务: {task_id}")

                except Exception as e:
                    log.error(f"[PDF] 加载任务失败 {task_id}: {e}")
                    continue

            log.info(f"[PDF] 共加载 {loaded_count} 个历史任务")

        except json.JSONDecodeError as e:
            log.error(f"[PDF] 解析 tasks.json 失败: {e}")
        except Exception as e:
            log.error(f"[PDF] 加载历史任务失败: {e}")

    def _save_all_tasks(self) -> None:
        """保存所有任务到统一的 tasks.json 文件"""
        try:
            task_meta_file = os.path.join(PDF_BASE_DIR, self.TASK_META_FILE)
            os.makedirs(PDF_BASE_DIR, exist_ok=True)

            all_tasks_data = {task_id: asdict(task) for task_id, task in self._tasks.items()}

            with open(task_meta_file, 'w', encoding='utf-8') as f:
                json.dump(all_tasks_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            log.error(f"[PDF] 保存所有任务失败: {e}")

    def _update_task_time(self, task: PdfTask) -> None:
        """更新任务的更新时间"""
        task.update_time = datetime.now().timestamp()

    def _save_task_and_update_time(self, task: PdfTask) -> None:
        """更新任务时间并保存"""
        self._update_task_time(task)
        self._save_all_tasks()

    def upload_file(self, file_obj: FileLike, filename: str) -> Tuple[int, str, Optional[PdfFileInfo]]:
        """上传 PDF 文件并为其创建任务。

        Args:
            file_obj (FileLike): 符合 `save` 方法协议的文件对象（如 werkzeug FileStorage）。
            filename (str): 原始文件名。

        Returns:
            Tuple[int, str, Optional[PdfFileInfo]]: (code, msg, file_info)。code=0 表示成功。
        """
        try:
            if not is_allowed_pdf_file(filename):
                return -1, "只支持 PDF 文件", None

            # 确保目录存在
            ensure_directory(PDF_UPLOAD_DIR)
            ensure_directory(PDF_UNLOCK_DIR)

            # 使用安全文件名
            safe_filename = secure_filename(filename)
            file_path = os.path.join(PDF_UPLOAD_DIR, safe_filename)

            # 如果文件已存在，添加序号
            if os.path.exists(file_path):
                base_name, ext = os.path.splitext(safe_filename)
                counter = 1
                while os.path.exists(file_path):
                    new_filename = f"{base_name}_{counter}{ext}"
                    file_path = os.path.join(PDF_UPLOAD_DIR, new_filename)
                    counter += 1
                safe_filename = os.path.basename(file_path)

            # 保存文件
            file_obj.save(file_path)
            log.info(f"[PDF] 文件保存完成: {file_path}")

            # 确保文件完全写入磁盘
            try:
                fd = os.open(file_path, os.O_RDONLY)
                os.fsync(fd)
                os.close(fd)
            except Exception as e:
                log.warning(f"[PDF] 同步文件到磁盘失败: {e}")

            # 获取文件信息
            file_info = get_file_info(file_path)
            if not file_info:
                return -1, "无法获取文件信息", None

            log.info(f"[PDF] 开始创建/更新任务: {safe_filename}")
            # 创建或更新任务
            now = datetime.now().timestamp()
            with self._task_lock:
                if safe_filename in self._tasks:
                    task = self._tasks[safe_filename]
                    task.uploaded_path = file_path
                    task.uploaded_info = file_info
                    task.status = TASK_STATUS_UPLOADED
                    task.update_time = now
                else:
                    task = PdfTask(task_id=safe_filename,
                                   filename=safe_filename,
                                   status=TASK_STATUS_UPLOADED,
                                   uploaded_path=file_path,
                                   uploaded_info=file_info,
                                   create_time=now,
                                   update_time=now)
                    self._tasks[safe_filename] = task

            log.info(f"[PDF] 开始保存任务元数据")
            # 保存任务
            self._save_all_tasks()
            log.info(f"[PDF] 任务元数据保存完成，准备返回响应")

            return 0, "文件上传成功", file_info

        except Exception as e:
            log.error(f"[PDF] 上传文件失败: {e}")
            return -1, f"上传文件失败: {str(e)}", None

    def decrypt(self, task_id: str, password: Optional[str] = None) -> Tuple[int, str]:
        """提交一个 PDF 文件解密任务（异步处理）。

        此方法将任务状态更新为 'pending'，然后启动一个后台线程来执行
        实际的解密操作。

        Args:
            task_id (str): 任务 ID（即上传时的文件名）。
            password (Optional[str]): PDF 文件的解密密码。

        Returns:
            Tuple[int, str]: (code, msg)。code=0 表示任务已成功提交。
        """
        try:
            with self._task_lock:
                task = self._get_task(task_id)
                if not task:
                    return -1, f"任务不存在: {task_id}"

                # 检查文件是否存在
                if not os.path.exists(task.uploaded_path):
                    return -1, f"上传文件不存在: {task_id}"

                # 检查任务状态
                if task.status == TASK_STATUS_PROCESSING:
                    return -1, "任务正在处理中，请稍候"

                if task.status == TASK_STATUS_SUCCESS:
                    return 0, "文件已解密，无需重复处理"

                # 构建输出文件路径
                output_path = self._get_unlocked_path(task_id)

                # 更新任务状态为等待处理
                task.status = TASK_STATUS_PENDING
                task.error_message = None
                self._save_task_and_update_time(task)

            # 在后台线程中异步执行解密
            thread = threading.Thread(target=self._decrypt_file_async,
                                      args=(task_id, task.uploaded_path, output_path, password),
                                      daemon=True)
            thread.start()

            log.info(f"[PDF] 已提交解密任务: {task_id}")
            return 0, "解密任务已提交，正在后台处理"

        except Exception as e:
            log.error(f"[PDF] 提交解密任务失败: {e}")
            return -1, f"提交解密任务失败: {str(e)}"

    def _decrypt_file_async(self, task_id: str, input_path: str, output_path: str, password: Optional[str]) -> None:
        """
        异步解密文件（在后台线程中执行）
        
        :param task_id: 任务ID（文件名）
        :param input_path: 输入文件路径
        :param output_path: 输出文件路径
        :param password: 密码（可选）
        """
        try:
            with self._task_lock:
                task = self._get_task(task_id)
                if not task:
                    log.error(f"[PDF] 任务不存在: {task_id}")
                    return
                task.status = TASK_STATUS_PROCESSING
                task.error_message = None
                self._save_task_and_update_time(task)

            log.info(f"[PDF] 开始解密文件: {task_id}")

            # 执行解密
            code, msg = self._decrypt_with_pikepdf(input_path, output_path, password)

            with self._task_lock:
                task = self._get_task(task_id)
                if not task:
                    log.error(f"[PDF] 任务不存在: {task_id}")
                    return

                if code != 0:
                    # 解密失败
                    task.status = TASK_STATUS_FAILED
                    task.error_message = msg
                    log.error(f"[PDF] 文件解密失败 {task_id}: {msg}")
                else:
                    # 获取已解密文件信息
                    unlocked_info = get_file_info(output_path)
                    if not unlocked_info:
                        task.status = TASK_STATUS_FAILED
                        task.error_message = "无法获取已解密文件信息"
                        log.error(f"[PDF] 无法获取已解密文件信息: {task_id}")
                    else:
                        # 解密成功
                        task.status = TASK_STATUS_SUCCESS
                        task.unlocked_path = output_path
                        task.unlocked_info = unlocked_info
                        task.error_message = None
                        log.info(f"[PDF] 文件解密成功: {output_path}")

                self._save_task_and_update_time(task)

        except Exception as e:
            log.error(f"[PDF] 异步解密文件失败 {task_id}: {e}")
            with self._task_lock:
                task = self._get_task(task_id)
                if task:
                    task.status = TASK_STATUS_FAILED
                    task.error_message = f"解密失败: {str(e)}"
                    self._save_task_and_update_time(task)

    def _decrypt_with_pikepdf(self,
                              input_path: str,
                              output_path: str,
                              password: Optional[str] = None) -> Tuple[int, str]:
        """使用 pikepdf 解密 PDF"""
        try:
            if password is not None:
                # 如果明确提供了密码（包括空字符串），使用该密码
                try:
                    with pikepdf.open(input_path, password=password) as pdf:
                        pdf.save(output_path)
                except pikepdf.PasswordError:
                    return -1, "密码错误"
            else:
                # 先尝试无密码打开（处理无密码的 PDF）
                try:
                    with pikepdf.open(input_path) as pdf:
                        pdf.save(output_path)
                except pikepdf.PasswordError:
                    return -1, "PDF 需要密码，但未提供密码"

            return 0, "PDF 解密成功"

        except Exception as e:
            log.error(f"[PDF] pikepdf 解密失败: {e}")
            return -1, f"PDF 解密失败: {str(e)}"

    def list(self) -> List[PdfTaskInfo]:
        """列出所有 PDF 任务的详情。

        在返回列表前，会同步检查每个任务关联的文件是否存在，并更新文件信息。
        如果文件不存在，对应的任务将被清理。

        Returns:
            List[PdfTaskInfo]: 任务详情列表，按更新时间倒序排列。
        """
        try:
            # 确保目录存在
            ensure_directory(PDF_UPLOAD_DIR)
            ensure_directory(PDF_UNLOCK_DIR)

            with self._task_lock:
                # 重新验证文件是否存在，更新任务
                tasks_to_remove = []
                for task_id, task in self._tasks.items():
                    # 验证上传文件
                    if not os.path.exists(task.uploaded_path):
                        tasks_to_remove.append(task_id)
                        continue

                    # 重新获取上传文件信息
                    uploaded_info = get_file_info(task.uploaded_path)
                    if uploaded_info:
                        task.uploaded_info = uploaded_info
                    else:
                        tasks_to_remove.append(task_id)
                        continue

                    # 更新已解密文件信息
                    self._update_unlocked_file_info(task)

                # 移除不存在的文件任务
                for task_id in tasks_to_remove:
                    del self._tasks[task_id]

                if tasks_to_remove:
                    self._save_all_tasks()

            # 按更新时间排序（最新的在前）
            sorted_tasks = sorted(self._tasks.values(), key=lambda x: x.update_time, reverse=True)

            # 构建任务详情列表
            return [self._task_to_dict(task) for task in sorted_tasks]

        except Exception as e:
            log.error(f"[PDF] 列出任务失败: {e}")
            return []

    def get_task_status(self, task_id: str) -> Tuple[int, str, Optional[PdfTaskInfo]]:
        """获取单个 PDF 任务的状态与详情。

        Args:
            task_id (str): 任务 ID（文件名）。

        Returns:
            Tuple[int, str, Optional[PdfTaskInfo]]: (code, msg, data)。code=0 表示成功。
        """
        try:
            with self._task_lock:
                task = self._get_task(task_id)
                if not task:
                    return -1, "任务不存在", None

                return 0, "获取任务状态成功", self._task_to_dict(task)

        except Exception as e:
            log.error(f"[PDF] 获取任务状态失败: {e}")
            return -1, f"获取任务状态失败: {str(e)}", None

    def delete(self, task_id: str) -> Tuple[int, str]:
        """
        删除 PDF 任务
        
        :param task_id: 任务ID（文件名）
        :return: (错误码, 消息)，0 表示成功
        """
        try:
            with self._task_lock:
                task = self._get_task(task_id)
                if not task:
                    return -1, f"任务不存在: {task_id}"

                # 如果正在处理中，不允许删除
                if task.status == TASK_STATUS_PROCESSING:
                    return -1, "任务正在处理中，无法删除"

                deleted_files = []

                # 删除上传文件
                if task.uploaded_path and os.path.exists(task.uploaded_path):
                    os.remove(task.uploaded_path)
                    deleted_files.append(task.uploaded_path)
                    log.info(f"[PDF] 删除上传文件: {task.uploaded_path}")

                # 删除已解密文件
                if task.unlocked_path and os.path.exists(task.unlocked_path):
                    os.remove(task.unlocked_path)
                    deleted_files.append(task.unlocked_path)
                    log.info(f"[PDF] 删除已解密文件: {task.unlocked_path}")

                if not deleted_files:
                    return -1, "文件不存在"

                # 移除任务
                del self._tasks[task_id]

                # 保存任务
                self._save_all_tasks()

            return 0, "任务删除成功"

        except Exception as e:
            log.error(f"[PDF] 删除任务失败: {e}")
            return -1, f"删除任务失败: {str(e)}"


# 创建全局实例
pdf_mgr = PdfMgr()
