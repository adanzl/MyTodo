"""图片管理服务。

提供上传、删除、查看（含缩放缓存）等核心逻辑。
上传的图片保存在 DEFAULT_BASE_DIR/pic 目录下。
"""

from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple

from werkzeug.utils import secure_filename

from core.config import PIC_BASE_DIR, app_logger
from core.utils import ensure_directory, get_unique_filepath, is_allowed_image_file

log = app_logger

# 缓存文件名格式：{basename}_w{w}_h{h}.png
_CACHE_PATTERN = re.compile(r'^(.+)_w(\d+)_h(\d+)\.png$')


class PicMgr:
    """图片管理器。"""

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = base_dir or PIC_BASE_DIR
        ensure_directory(self._base_dir)

    def _get_cache_filename(self, base_name: str, w: int, h: int) -> str:
        """规范化缓存文件名：basename_w{w}_h{h}.png"""
        safe_base = re.sub(r'[^\w\-]', '_', base_name) or 'image'
        return f"{safe_base}_w{w}_h{h}.png"

    def _get_base_name_from_filename(self, filename: str) -> str:
        """从文件名提取基础名。缓存文件 image_w100_h100.png -> image；原图 image.jpg -> image。"""
        m = _CACHE_PATTERN.match(filename)
        if m:
            return m.group(1)
        return os.path.splitext(filename)[0] or 'image'

    def validate_path(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """校验文件名并返回安全路径。返回 (abs_path, error_msg)。"""
        if not filename:
            return None, "文件名为空"
        safe_name = secure_filename(filename)
        if not safe_name:
            return None, "非法文件名"
        if not is_allowed_image_file(safe_name):
            return None, "不允许的图片格式，支持 jpg/jpeg/png/gif/webp/bmp"
        abs_path = os.path.abspath(os.path.join(self._base_dir, safe_name))
        if not abs_path.startswith(os.path.abspath(self._base_dir)):
            return None, "非法路径"
        return abs_path, None

    def upload(self, file) -> Tuple[str, str]:
        """上传图片到 pic 目录。返回 (filename, target_path)。"""
        if not file or file.filename == '':
            raise ValueError("文件名不能为空")
        if not is_allowed_image_file(file.filename):
            raise ValueError("不允许的图片格式，支持 jpg/jpeg/png/gif/webp/bmp")

        ensure_directory(self._base_dir)
        base_name, ext = os.path.splitext(secure_filename(file.filename))
        base_name = base_name or "image"
        target_path = get_unique_filepath(self._base_dir, base_name, ext.lower())
        file.save(target_path)
        filename = os.path.basename(target_path)
        log.info(f"[Pic] 上传成功: {filename}")
        return filename, target_path

    def _collect_related_files(self, base_name: str) -> List[str]:
        """收集与 base_name 相关的所有文件（原图 + 所有缓存变体）。返回完整路径列表。"""
        result: List[str] = []
        try:
            for f in os.listdir(self._base_dir):
                fpath = os.path.join(self._base_dir, f)
                if not os.path.isfile(fpath):
                    continue
                fbase = self._get_base_name_from_filename(f)
                if fbase == base_name:
                    result.append(fpath)
        except OSError as e:
            log.warning(f"[Pic] 列出目录失败: {e}")
        return result

    def delete(self, name: str) -> List[str]:
        """删除指定文件名的图片及其所有缓存变体。返回已删除的文件名列表。"""
        abs_path, err_msg = self.validate_path(name)
        if err_msg:
            raise ValueError(err_msg)
        if not os.path.isfile(abs_path):
            raise FileNotFoundError("文件不存在")

        base_name = self._get_base_name_from_filename(os.path.basename(abs_path))
        to_delete = self._collect_related_files(base_name)
        deleted: List[str] = []
        for fpath in to_delete:
            try:
                os.remove(fpath)
                deleted.append(os.path.basename(fpath))
            except OSError as e:
                log.warning(f"[Pic] 删除失败 {fpath}: {e}")

        log.info(f"[Pic] 删除成功: {deleted}")
        return deleted

    def _resize_and_cache(self, orig_path: str, w: int, h: int, cache_path: str) -> None:
        """缩放图片（保持纵横比），使用透明底，保存为 PNG 缓存。"""
        from PIL import Image

        with Image.open(orig_path) as img:
            # 统一转为 RGBA，兼容 CMYK、P 等模式
            if img.mode in ('RGBA', 'LA'):
                img = img.convert('RGBA')
            elif img.mode == 'P':
                img = img.convert('RGBA')
            elif img.mode in ('CMYK', 'YCbCr', 'I', 'F'):
                img = img.convert('RGB').convert('RGBA')
            else:
                img = img.convert('RGBA')

            orig_w, orig_h = img.size
            if orig_w <= 0 or orig_h <= 0:
                raise ValueError("Invalid image dimensions")
            if orig_w <= w and orig_h <= h:
                out_w, out_h = orig_w, orig_h
            else:
                ratio = min(w / orig_w, h / orig_h)
                out_w = max(1, int(orig_w * ratio))
                out_h = max(1, int(orig_h * ratio))

            resized = img.resize((out_w, out_h), Image.Resampling.LANCZOS)
            ensure_directory(os.path.dirname(cache_path))
            resized.save(cache_path, 'PNG', optimize=True)

    def get_view_path(
        self, name: str, w: Optional[int] = None, h: Optional[int] = None
    ) -> Tuple[str, Optional[str]]:
        """获取图片查看路径。

        无 w、h 时返回原图路径及 mimetype。
        有 w、h 时按比例缩放并缓存，返回缓存路径及 'image/png'。
        返回 (path, mimetype)，mimetype 为 None 时由调用方推断。
        """
        abs_path, err_msg = self.validate_path(name)
        if err_msg:
            raise ValueError(err_msg)
        if not os.path.isfile(abs_path):
            raise FileNotFoundError("Image not found")

        if w is None or h is None or w <= 0 or h <= 0:
            return abs_path, None

        base_name = os.path.splitext(os.path.basename(abs_path))[0]
        cache_filename = self._get_cache_filename(base_name, w, h)
        cache_path = os.path.join(self._base_dir, cache_filename)

        if os.path.isfile(cache_path):
            return cache_path, 'image/png'

        try:
            self._resize_and_cache(abs_path, w, h, cache_path)
        except Exception as e:
            log.warning(f"[Pic] 缩放缓存失败，返回原图: {e}")
            return abs_path, None
        return cache_path, 'image/png'


pic_mgr = PicMgr()
