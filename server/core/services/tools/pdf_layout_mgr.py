"""
PDF 排版管理服务
提供 PDF 文件上传、排版处理、列表、下载等功能
采用任务模式，每个文件对应一个任务，支持异步排版处理
"""
import os
from typing import Optional, Tuple, Any, Protocol
from dataclasses import dataclass

from werkzeug.utils import secure_filename

from core.services.base_task_mgr import BaseTaskMgr, FileInfo, TaskBase

from pikepdf import Pdf

import pikepdf

from core.config import app_logger
from core.config import (PDF_LAYOUT_BASE_DIR, PDF_LAYOUT_UPLOAD_DIR, PDF_LAYOUT_OUTPUT_DIR,
                         TASK_STATUS_PROCESSING, TASK_STATUS_SUCCESS, TASK_STATUS_UPLOADED)
from core.utils import ensure_directory, get_file_info, get_unique_filepath, is_allowed_pdf_file

log = app_logger


class FileLike(Protocol):

    def save(self, dst: str) -> Any:
        ...


PdfLayoutFileInfo = FileInfo


@dataclass
class PdfLayoutTask(TaskBase):
    """PDF 排版任务"""
    uploaded_path: str
    uploaded_info: PdfLayoutFileInfo
    output_path: Optional[str] = None
    output_info: Optional[PdfLayoutFileInfo] = None
    fill_configs: Optional[list[int]] = None


class PdfLayoutMgr(BaseTaskMgr[PdfLayoutTask]):
    """PDF 排版管理器（任务模式）"""

    TASK_META_FILE = 'tasks.json'

    def __init__(self) -> None:
        """初始化管理器"""
        super().__init__(base_dir=PDF_LAYOUT_BASE_DIR)

    def _task_from_dict(self, data: dict) -> PdfLayoutTask:
        return PdfLayoutTask(**data)

    def _get_output_path(self, task_id: str) -> str:
        """获取排版输出文件路径"""
        base_name, ext = os.path.splitext(task_id)
        output_filename = f"{base_name}_layout{ext}"
        return os.path.join(PDF_LAYOUT_OUTPUT_DIR, output_filename)

    def _update_output_file_info(self, task: PdfLayoutTask) -> None:
        """更新任务的输出文件信息"""
        output_path = self._get_output_path(task.task_id)
        if os.path.exists(output_path):
            output_info = get_file_info(output_path)
            if output_info:
                task.output_path = output_path
                task.output_info = output_info
                if task.status != TASK_STATUS_PROCESSING:
                    task.status = TASK_STATUS_SUCCESS
            else:
                task.output_path = None
                task.output_info = None
                if task.status == TASK_STATUS_SUCCESS:
                    task.status = TASK_STATUS_UPLOADED
        else:
            task.output_path = None
            task.output_info = None
            if task.status == TASK_STATUS_SUCCESS:
                task.status = TASK_STATUS_UPLOADED

    def _load_history_tasks(self) -> None:
        super()._load_history_tasks()

        with self._task_lock.gen_wlock():
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

                self._update_output_file_info(task)

            for task_id in tasks_to_remove:
                del self._tasks[task_id]

            if tasks_to_remove:
                self._save_all_tasks()

    def create_task(self, file_obj: FileLike, filename: str) -> Tuple[int, str, Optional[str]]:
        """上传 PDF 文件并为其创建任务。"""
        try:
            if not is_allowed_pdf_file(filename):
                return -1, "只支持 PDF 文件", None

            ensure_directory(PDF_LAYOUT_UPLOAD_DIR)
            ensure_directory(PDF_LAYOUT_OUTPUT_DIR)

            safe_filename = secure_filename(filename)
            base_name, ext = os.path.splitext(safe_filename)

            # 使用统一的函数生成唯一文件路径
            file_path = get_unique_filepath(
                PDF_LAYOUT_UPLOAD_DIR, base_name, ext)
            safe_filename = os.path.basename(file_path)

            file_obj.save(file_path)
            log.info(f"[PDF 排版] 文件保存完成: {file_path}")

            file_info = get_file_info(file_path)
            if not file_info:
                return -1, "无法获取文件信息", None

            task = PdfLayoutTask(task_id=safe_filename,
                                 name=safe_filename,
                                 status=TASK_STATUS_UPLOADED,
                                 uploaded_path=file_path,
                                 uploaded_info=file_info)

            return self._create_task_and_save(task, task_id=safe_filename)

        except Exception as e:
            log.error(f"[PDF 排版] 上传文件失败: {e}")
            return -1, f"上传文件失败: {str(e)}", None

    def start_task(self, task_id: str, **kwargs: Any) -> Tuple[int, str]:
        """提交一个 PDF 排版任务（异步处理）。"""
        task, err = self._get_task_or_err(task_id)
        if not task:
            return -1, err

        if not os.path.exists(task.uploaded_path):
            return -1, f"上传文件不存在: {task_id}"

        if task.status == TASK_STATUS_PROCESSING:
            return -1, "任务正在处理中，请稍候"

        if task.status == TASK_STATUS_SUCCESS:
            return 0, "文件已处理，无需重复处理"

        def runner(t: PdfLayoutTask) -> None:
            output_path = self._get_output_path(t.task_id)
            code, msg = self._process_layout(t.uploaded_path, output_path)
            if code != 0:
                raise Exception(msg)

            output_info = get_file_info(output_path)
            if not output_info:
                raise Exception("无法获取输出文件信息")

            t.output_path = output_path
            t.output_info = output_info
            log.info(f"[PDF 排版] 文件处理成功: {output_path}")

        self._run_task_async(task_id, runner)
        return 0, "排版任务已提交，正在后台处理"

    def _process_layout(self, input_path: str, output_path: str) -> Tuple[int, str]:
        """执行 PDF 排版处理。

        当前为占位实现，直接复制输入文件作为输出，
        后续可扩展为实际的页面重排、合并等排版操作。
        """
        try:
            with pikepdf.open(input_path) as pdf:
                pdf.save(output_path)
            return 0, "PDF 排版处理成功"
        except Exception as e:
            log.error(f"[PDF 排版] 处理失败: {e}")
            return -1, f"PDF 排版处理失败: {str(e)}"

    def _before_delete_task(self, task: PdfLayoutTask) -> None:
        """删除关联的上传文件和输出文件。"""
        paths_to_delete = [task.uploaded_path, task.output_path]
        for path in paths_to_delete:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    log.info(f"[PDF 排版] 删除文件: {path}")
                except Exception as e:
                    log.error(f"[PDF 排版] 删除文件失败 {path}: {e}")

    def save_fill_configs(self, task_id: str, fill_configs: list[int]) -> Tuple[int, str]:
        """更新任务的填充配置。"""
        with self._task_lock.gen_wlock():
            task, err = self._get_task_or_err(task_id)
            if not task:
                return -1, err

            task.fill_configs = fill_configs
            self._save_task_and_update_time(task)
            log.info(f"[PDF 排版] 更新填充配置: {task_id} {fill_configs}")
            return 0, "填充配置已保存"

    def generate_layout(self, task_id: str) -> Tuple[int, str]:
        """生成骑缝排版 PDF（使用已保存的 fill_configs）。"""
        with self._task_lock.gen_wlock():
            task, err = self._get_task_or_err(task_id)
            if not task:
                return -1, err

            if not task.uploaded_path or not os.path.exists(task.uploaded_path):
                return -1, "上传文件不存在"

            fill_configs = task.fill_configs or []
            output_path = self._get_output_path(task.task_id)

        try:
            with pikepdf.open(task.uploaded_path) as pdf:
                total_pages = len(pdf.pages)
                effective = _build_effective_pages(total_pages, fill_configs)
                spreads = _generate_saddle_stitch_spreads(len(effective))

                out = Pdf.new()
                # 获取原始页尺寸
                ref_rect = pikepdf.Rectangle(pdf.pages[0].mediabox)
                pw = float(ref_rect.width)
                ph = float(ref_rect.height)

                for left_idx, right_idx in spreads:
                    # 每个 spread 合并为一页（两页左右拼接）
                    merge_page = out.add_blank_page(page_size=(2 * pw, ph))

                    left_pn = effective[left_idx - 1]
                    right_pn = effective[right_idx - 1]

                    if left_pn > 0:
                        src = pdf.pages[left_pn - 1]
                        merge_page.add_overlay(
                            src, pikepdf.Rectangle(0, 0, pw, ph))

                    if right_pn > 0:
                        src = pdf.pages[right_pn - 1]
                        merge_page.add_overlay(
                            src, pikepdf.Rectangle(pw, 0, 2 * pw, ph))

                out.save(output_path)

            with self._task_lock.gen_wlock():
                task2, _ = self._get_task_or_err(task_id)
                if task2:
                    task2.output_path = output_path
                    task2.output_info = get_file_info(output_path)
                    task2.status = TASK_STATUS_SUCCESS
                    self._save_task_and_update_time(task2)

            log.info(f"[PDF 排版] 骑缝 PDF 生成成功: {output_path}")
            return 0, "骑缝 PDF 已生成"

        except Exception as e:
            log.error(f"[PDF 排版] 生成骑缝 PDF 失败: {e}")
            return -1, f"生成骑缝 PDF 失败: {str(e)}"


# ---- 算法辅助函数（与前端对齐） ----

def _build_effective_pages(total_pages: int, insert_at: list[int]) -> list[int]:
    """构建有效页码列表，0=空白，按 insert_at 在指定页前插入空白。"""
    pages: list[int] = []
    for i in range(1, total_pages + 1):
        count = sum(1 for p in insert_at if p == i)
        for _ in range(count):
            pages.append(0)
        pages.append(i)
    # 末尾追加空白（填值 > total_pages 表示在末尾追加）
    trailing = sum(1 for p in insert_at if p > total_pages)
    for _ in range(trailing):
        pages.append(0)
    padded = ((len(pages) + 3) // 4) * 4
    while len(pages) < padded:
        pages.append(0)
    return pages


def _generate_saddle_stitch_spreads(effective_count: int) -> list[tuple[int, int]]:
    """生成骑缝对开页索引序列（1-based）。"""
    spreads: list[tuple[int, int]] = []
    for s in range(effective_count // 4):
        spreads.append((effective_count - 2 * s, 2 * s + 1))
        spreads.append((2 * s + 2, effective_count - 2 * s - 1))
    return spreads


pdf_layout_mgr = PdfLayoutMgr()
