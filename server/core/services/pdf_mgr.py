"""
PDF 管理服务
提供 PDF 文件上传、解密、列表等功能
采用任务模式，每个文件对应一个任务，支持异步解密处理
"""
import os
from typing import Optional, Tuple, Any, Protocol
from dataclasses import dataclass

from werkzeug.utils import secure_filename

from core.services.base_task_mgr import BaseTaskMgr, FileInfo, TaskBase

import pikepdf

from core.config import app_logger
from core.config import (PDF_BASE_DIR, PDF_UPLOAD_DIR, PDF_UNLOCK_DIR, TASK_STATUS_PROCESSING, TASK_STATUS_SUCCESS,
                         TASK_STATUS_UPLOADED)
from core.utils import ensure_directory, get_file_info, is_allowed_pdf_file

log = app_logger


class FileLike(Protocol):

    def save(self, dst: str) -> Any:
        ...


PdfFileInfo = FileInfo


@dataclass
class PdfTask(TaskBase):
    """PDF 任务"""
    uploaded_path: str
    uploaded_info: PdfFileInfo
    unlocked_path: Optional[str] = None
    unlocked_info: Optional[PdfFileInfo] = None


class PdfMgr(BaseTaskMgr[PdfTask]):
    """PDF 管理器（任务模式）"""

    TASK_META_FILE = 'tasks.json'  # 任务元数据文件名

    def __init__(self) -> None:
        """初始化管理器"""
        super().__init__(base_dir=PDF_BASE_DIR)

    def _task_from_dict(self, data: dict) -> PdfTask:
        return PdfTask(**data)

    def _get_unlocked_path(self, task_id: str) -> str:
        """获取已解密文件路径"""
        base_name, ext = os.path.splitext(task_id)
        unlocked_filename = f"{base_name}_unlocked{ext}"
        return os.path.join(PDF_UNLOCK_DIR, unlocked_filename)

    def _update_unlocked_file_info(self, task: PdfTask) -> None:
        """更新任务的已解密文件信息"""
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
        else:
            task.unlocked_path = None
            task.unlocked_info = None
            if task.status == TASK_STATUS_SUCCESS:
                task.status = TASK_STATUS_UPLOADED

    def _load_history_tasks(self) -> None:
        super()._load_history_tasks()

        with self._task_lock:
            tasks_to_remove = []
            for task_id, task in self._tasks.items():
                if not task.uploaded_path or not os.path.exists(task.uploaded_path):
                    tasks_to_remove.append(task_id)
                    continue

                uploaded_info = get_file_info(task.uploaded_path)
                if uploaded_info:
                    task.uploaded_info = uploaded_info
                else:
                    tasks_to_remove.append(task_id)
                    continue

                self._update_unlocked_file_info(task)

            for task_id in tasks_to_remove:
                del self._tasks[task_id]

            if tasks_to_remove:
                self._save_all_tasks()

    def create_task(self, file_obj: FileLike, filename: str) -> Tuple[int, str, Optional[str]]:
        """上传 PDF 文件并为其创建任务。"""
        try:
            if not is_allowed_pdf_file(filename):
                return -1, "只支持 PDF 文件", None

            ensure_directory(PDF_UPLOAD_DIR)
            ensure_directory(PDF_UNLOCK_DIR)

            safe_filename = secure_filename(filename)
            file_path = os.path.join(PDF_UPLOAD_DIR, safe_filename)

            if os.path.exists(file_path):
                base_name, ext = os.path.splitext(safe_filename)
                counter = 1
                while os.path.exists(file_path):
                    new_filename = f"{base_name}_{counter}{ext}"
                    file_path = os.path.join(PDF_UPLOAD_DIR, new_filename)
                    counter += 1
                safe_filename = os.path.basename(file_path)

            file_obj.save(file_path)
            log.info(f"[PDF] 文件保存完成: {file_path}")

            file_info = get_file_info(file_path)
            if not file_info:
                return -1, "无法获取文件信息", None

            task = PdfTask(task_id=safe_filename,
                           name=safe_filename,
                           status=TASK_STATUS_UPLOADED,
                           uploaded_path=file_path,
                           uploaded_info=file_info)

            return self._create_task_and_save(task, task_id=safe_filename)

        except Exception as e:
            log.error(f"[PDF] 上传文件失败: {e}")
            return -1, f"上传文件失败: {str(e)}", None

    def start_task(self, task_id: str, password: Optional[str] = None) -> Tuple[int, str]:
        """提交一个 PDF 文件解密任务（异步处理）。"""
        task, err = self._get_task_or_err(task_id)
        if err:
            return -1, err

        if not os.path.exists(task.uploaded_path):
            return -1, f"上传文件不存在: {task_id}"

        if task.status == TASK_STATUS_PROCESSING:
            return -1, "任务正在处理中，请稍候"

        if task.status == TASK_STATUS_SUCCESS:
            return 0, "文件已解密，无需重复处理"

        def runner(t: PdfTask) -> None:
            output_path = self._get_unlocked_path(t.task_id)
            code, msg = self._decrypt_with_pikepdf(t.uploaded_path, output_path, password)
            if code != 0:
                raise Exception(msg)

            unlocked_info = get_file_info(output_path)
            if not unlocked_info:
                raise Exception("无法获取已解密文件信息")

            t.unlocked_path = output_path
            t.unlocked_info = unlocked_info
            log.info(f"[PDF] 文件解密成功: {output_path}")

        self._run_task_async(task_id, runner)
        return 0, "解密任务已提交，正在后台处理"

    def _decrypt_with_pikepdf(self,
                              input_path: str,
                              output_path: str,
                              password: Optional[str] = None) -> Tuple[int, str]:
        try:
            pdf_args = {'password': password} if password else {}
            with pikepdf.open(input_path, **pdf_args) as pdf:
                pdf.save(output_path)
            return 0, "PDF 解密成功"
        except pikepdf.PasswordError:
            return -1, "密码错误或PDF需要密码"
        except Exception as e:
            log.error(f"[PDF] pikepdf 解密失败: {e}")
            return -1, f"PDF 解密失败: {str(e)}"

    def _before_delete_task(self, task: PdfTask) -> None:
        """删除关联的上传文件和解密文件。"""
        paths_to_delete = [task.uploaded_path, task.unlocked_path]
        for path in paths_to_delete:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    log.info(f"[PDF] 删除文件: {path}")
                except Exception as e:
                    log.error(f"[PDF] 删除文件失败 {path}: {e}")


pdf_mgr = PdfMgr()
