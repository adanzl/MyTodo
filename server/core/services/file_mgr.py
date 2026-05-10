"""
文件管理服务
提供目录列表、递归扫描等功能
"""
import os
import re
import urllib.parse
from typing import Any, Dict, List

from core.config import app_logger, config
from core.utils import get_media_duration

log = app_logger


class FileMgr:
    """文件管理器"""

    def __init__(self) -> None:
        """初始化管理器"""
        self.default_base_dir = config.DEFAULT_BASE_DIR

    def list_directory(
        self,
        path: str,
        extensions_filter: str = "all",
        recursive: bool = False
    ) -> Dict[str, Any]:
        """
        列出目录内容
        
        Args:
            path: 目录路径
            extensions_filter: 文件扩展名过滤（audio/video/all/.pdf,.mp4等）
            recursive: 是否递归扫描
            
        Returns:
            {
                "code": 0,
                "msg": "ok",
                "data": [...],  # DirectoryItem 数组，递归时包含 subItems
                "currentPath": "..."
            }
        """
        try:
            # URL 解码
            while '%' in path:
                decoded = urllib.parse.unquote(path)
                if decoded == path:
                    break
                path = decoded

            log.info(f"===== [List Directory] path={path}, extensions={extensions_filter}, recursive={recursive}")

            # 处理路径
            if not path:
                path = self.default_base_dir
            elif '..' in path.split('/') or path.startswith('~'):
                return {"code": -1, "msg": "Invalid path: Path traversal not allowed"}
            else:
                path = os.path.abspath(
                    path if os.path.isabs(path) else os.path.join(self.default_base_dir, path.lstrip('/'))
                )

            if not os.path.exists(path):
                log.warning(f"Path does not exist: {path}, using default directory: {self.default_base_dir}")
                path = self.default_base_dir

            # 验证读取权限
            try:
                entries = os.listdir(path)
            except Exception:
                path = self.default_base_dir
                entries = os.listdir(path)

            if not os.access(path, os.R_OK):
                if path != self.default_base_dir and os.access(self.default_base_dir, os.R_OK):
                    log.warning(f"No read permission for {path}, using default directory: {self.default_base_dir}")
                    path = self.default_base_dir
                else:
                    return {"code": -1, "msg": f"Permission denied: No read permission for {path}"}

            # 递归模式：扫描所有子目录和文件
            if recursive:
                return self._scan_recursive(path)

            # 非递归模式：只列出当前目录
            items = self._sort_items(self._list_items(path, entries))
            
            # 过滤
            if extensions_filter and extensions_filter != "all":
                items = self._filter_by_extensions(items, extensions_filter)

            return {"code": 0, "msg": "ok", "data": items, "currentPath": path}

        except PermissionError as e:
            log.error(f"Permission denied for {path}: {e}")
            return {"code": -1, "msg": f"Permission denied: {str(e)}"}
        except Exception as e:
            log.error(f"Error listing directory: {e}")
            return {"code": -1, "msg": f"Error: {str(e)}"}

    def _list_items(self, path: str, entries: List[str]) -> List[Dict[str, Any]]:
        """列出目录项"""
        items: List[Dict[str, Any]] = []
        
        for entry in entries:
            entry_path = os.path.join(path, entry)
            try:
                stat_info = os.stat(entry_path)
                is_dir = os.path.isdir(entry_path) if os.path.exists(entry_path) else False
                
                item = {
                    "name": entry,
                    "path": entry_path,
                    "isDirectory": is_dir,
                    "size": 0 if is_dir else getattr(stat_info, 'st_size', 0),
                    "modified": getattr(stat_info, 'st_mtime', 0),
                    "accessible": True,
                }
                items.append(item)
            except (OSError, PermissionError) as e:
                log.warning(f"Cannot access {entry_path}: {e}")
                items.append({
                    "name": entry,
                    "path": entry_path,
                    "isDirectory": False,
                    "size": 0,
                    "modified": 0,
                    "accessible": False,
                })
                continue
        
        return items

    def _sort_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """自然排序目录项"""
        def natural_sort_key(item: Dict[str, Any]):
            name = item["name"]
            is_dir = item["isDirectory"]

            track_match = re.search(r'track\s+(\d+)', name, re.IGNORECASE)
            track_number = int(track_match.group(1)) if track_match else float('inf')
            has_track = track_match is not None

            def split_name_into_parts(s: str):
                parts = []
                current_text = ''
                i = 0
                while i < len(s):
                    if s[i].isdigit():
                        num_str = ''
                        while i < len(s) and s[i].isdigit():
                            num_str += s[i]
                            i += 1
                        if current_text:
                            parts.append((0, current_text.lower()))
                            current_text = ''
                        parts.append((1, int(num_str)))
                    else:
                        current_text += s[i]
                        i += 1
                if current_text:
                    parts.append((0, current_text.lower()))
                return tuple(parts)

            return (not is_dir, not has_track, track_number, split_name_into_parts(name))

        items.sort(key=natural_sort_key)
        return items

    def _filter_by_extensions(
        self,
        items: List[Dict[str, Any]],
        extensions_filter: str
    ) -> List[Dict[str, Any]]:
        """根据扩展名过滤"""
        if extensions_filter == "audio":
            allowed_exts = {'.mp3', '.wav', '.aac', '.ogg', '.m4a', '.flac', '.wma', '.mp4'}
        elif extensions_filter == "video":
            allowed_exts = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
        elif extensions_filter.startswith("."):
            allowed_exts = {ext.strip().lower() for ext in extensions_filter.split(",")}
        else:
            allowed_exts = None

        if allowed_exts:
            items = [
                item for item in items
                if item["isDirectory"] or os.path.splitext(item["name"])[1].lower() in allowed_exts
            ]
        
        return items

    def _scan_recursive(self, root_path: str) -> Dict[str, Any]:
        """
        递归扫描目录，返回树形结构
        
        Args:
            root_path: 根目录路径
            
        Returns:
            {
                "code": 0,
                "msg": "ok",
                "data": [DirectoryItem],  # 包含 subItems 的树形结构
                "currentPath": "..."
            }
        """
        try:
            entries = os.listdir(root_path)
        except Exception as e:
            log.error(f"Cannot list directory {root_path}: {e}")
            return {"code": -1, "msg": f"无法读取目录: {str(e)}", "data": []}
        
        # 构建当前目录的项列表
        items = self._sort_items(self._list_items(root_path, entries))
        
        # 为每个子目录递归添加 subItems
        for item in items:
            if item["isDirectory"] and item.get("path"):
                sub_result = self._scan_recursive(item["path"])
                item["subItems"] = sub_result["data"] if sub_result["code"] == 0 else []
        
        return {"code": 0, "msg": "ok", "data": items, "currentPath": root_path}

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            {
                "code": 0,
                "msg": "ok",
                "data": {
                    "name": "...",
                    "path": "...",
                    "size": ...,
                    "modified": ...,
                    "isDirectory": false,
                    "duration": ...,
                    "isMediaFile": true/false
                }
            }
        """
        try:
            if not file_path:
                return {"code": -1, "msg": "文件路径不能为空"}

            # URL 解码
            while '%' in file_path:
                decoded = urllib.parse.unquote(file_path)
                if decoded == file_path:
                    break
                file_path = decoded

            # 安全检查
            if '..' in file_path.split('/') or file_path.startswith('~'):
                return {"code": -1, "msg": "Invalid path: Path traversal not allowed"}

            # 处理相对路径
            file_path = os.path.abspath(
                file_path if os.path.isabs(file_path) else os.path.join(self.default_base_dir, file_path.lstrip('/'))
            )

            # 验证路径在允许的目录内
            if not file_path.startswith(config.ALLOWED_DIR):
                log.warning(f"Path {file_path} is outside allowed directory {config.ALLOWED_DIR}")
                return {"code": -1, "msg": "文件路径不在允许的目录内"}

            # 验证文件存在
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return {"code": -1, "msg": "文件不存在" if os.path.exists(file_path) else "路径不是文件"}

            # 获取基本信息
            stat_info = os.stat(file_path)
            file_info: Dict[str, Any] = {
                "name": os.path.basename(file_path),
                "path": file_path,
                "size": stat_info.st_size,
                "modified": stat_info.st_mtime,
                "isDirectory": False,
            }

            # 判断是否为媒体文件
            media_extensions = {
                '.mp3', '.wav', '.aac', '.ogg', '.m4a', '.flac', '.wma', '.mp4',
                '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'
            }
            file_ext = os.path.splitext(file_path)[1].lower()
            is_media_file = file_ext in media_extensions

            # 如果是媒体文件，获取时长
            file_info["duration"] = get_media_duration(file_path) if is_media_file else None
            file_info["isMediaFile"] = is_media_file

            return {"code": 0, "msg": "ok", "data": file_info}

        except PermissionError as e:
            log.error(f"Permission denied for {file_path}: {e}")
            return {"code": -1, "msg": f"Permission denied: {str(e)}"}
        except Exception as e:
            log.error(f"Error getting file info: {e}")
            return {"code": -1, "msg": f"Error: {str(e)}"}


# 单例实例
file_mgr = FileMgr()
