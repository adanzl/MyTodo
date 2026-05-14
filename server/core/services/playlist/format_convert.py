"""播放列表内媒体转 MP3（ffmpeg）与路径替换。"""

import os
import threading
from queue import Queue
from typing import Any, Callable, Dict, Iterator, List, Tuple

from core.config import app_logger, FFMPEG_PATH
from core.utils import run_subprocess_safe

log = app_logger
_LOG = "[PlaylistFormatConvert]"
_FFMPEG_TIMEOUT_SEC = 300
# ffmpeg 命令模板，运行时再补 `-i <src>` 与目标路径，避免在循环里重复构造。
_FFMPEG_BASE_ARGS = ("-loglevel", "error", "-vn", "-codec:a", "libmp3lame", "-q:a", "2", "-y")


def _iter_file_items(playlist_data: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """遍历 playlist_data 内全部 file_item（pre_lists 7 天 + playlist）。

    仅产出 ``dict`` 项；损坏数据（非 list / 非 dict）跳过，避免 ``yield from None`` 或 ``.get`` 崩溃。
    """
    pre_lists = playlist_data.get("pre_lists", [])
    if isinstance(pre_lists, list) and len(pre_lists) == 7:
        for pre_list in pre_lists:
            if isinstance(pre_list, list):
                for item in pre_list:
                    if isinstance(item, dict):
                        yield item
    playlist = playlist_data.get("playlist")
    if not isinstance(playlist, list):
        return
    for item in playlist:
        if isinstance(item, dict):
            yield item


class PlaylistFormatConvert:
    """ffmpeg 子进程转码；线程内只通过队列请求持久化。"""

    def __init__(
        self,
        playlist_raw_provider: Callable[[], Dict[str, Any]],
        rds_save_queue: Queue,
    ) -> None:
        self._playlist_raw_provider = playlist_raw_provider
        self._rds_save_queue = rds_save_queue
        self._convert_locks: Dict[str, threading.Lock] = {}

    def is_converting(self, playlist_id: str) -> bool:
        lock = self._convert_locks.get(playlist_id)
        return bool(lock and lock.locked())

    def convert_playlist_to_mp3(self, playlist_id: str) -> Tuple[int, str]:
        raw = self._playlist_raw_provider()
        if not raw or playlist_id not in raw:
            return -1, "播放列表不存在"

        lock = self._convert_locks.setdefault(playlist_id, threading.Lock())
        if not lock.acquire(blocking=False):
            log.warning(f"{_LOG} 播放列表 {playlist_id} 正在转换中")
            return -1, "播放列表正在转换中，请稍后再试"

        # 取到锁之后到 thread.start() 之前的任何提前返回 / 异常都必须释放锁，
        # 否则 is_converting 会长期为 True，整个列表的修改会被锁死。
        try:
            playlist_data = raw[playlist_id]
            p_name = playlist_data.get("name", "未知播放列表")
            # dict.fromkeys 保留首次出现顺序去重，便于日志重现。
            unique_files = list(dict.fromkeys(
                item.get("uri") for item in _iter_file_items(playlist_data) if item.get("uri")
            ))

            if not unique_files:
                lock.release()
                return -1, "播放列表中没有可转换的文件"

            log.info(f"{_LOG} 开始转换播放列表 {playlist_id} - {p_name} 中的 {len(unique_files)} 个文件为MP3格式")
            # Thread 拥有锁的释放责任：见 `_run_convert_task` finally。
            threading.Thread(
                target=self._run_convert_task,
                args=(playlist_id, playlist_data, unique_files, lock),
                daemon=True,
                name=f"PlaylistConvert_{playlist_id}",
            ).start()
            return 0, f"已开始转换播放列表 {p_name} 中的文件为MP3格式，共 {len(unique_files)} 个文件"
        except Exception as e:
            lock.release()
            log.error(f"{_LOG} convert_playlist_to_mp3 异常: {playlist_id}, {e}", exc_info=True)
            return -1, f"转换失败: {str(e)}"

    def _run_convert_task(
        self,
        playlist_id: str,
        playlist_data: Dict[str, Any],
        files: List[str],
        lock: threading.Lock,
    ) -> None:
        success = 0
        failures: List[str] = []
        try:
            for file_path in files:
                ok, err = self._convert_one(playlist_data, file_path)
                if ok:
                    success += 1
                else:
                    failures.append(f"{file_path}: {err}")

            # OS 线程内不能直接写 Redis，交给 repository worker。
            self._rds_save_queue.put("save_playlist")

            if failures:
                preview = ", ".join(failures[:5])
                tail = f" 等共 {len(failures)} 个" if len(failures) > 5 else ""
                log.warning(f"{_LOG} 转换完成: 成功 {success}, 失败 {len(failures)}（{preview}{tail}）")
            else:
                log.info(f"{_LOG} 转换完成: 全部 {success} 个文件成功")
        except Exception as e:
            log.error(f"{_LOG} 转换任务异常: {playlist_id}, {e}", exc_info=True)
        finally:
            lock.release()
            log.info(f"{_LOG} 播放列表 {playlist_id} 转换锁已释放")

    def _convert_one(self, playlist_data: Dict[str, Any], file_path: str) -> Tuple[bool, str]:
        """单文件转 MP3；已是 mp3 / 转换成功均返回 (True, "")，其余返回 (False, 错误信息)。"""
        try:
            if not os.path.exists(file_path):
                log.warning(f"{_LOG} 文件不存在，跳过: {file_path}")
                return False, "文件不存在"

            if file_path.lower().endswith(".mp3"):
                log.info(f"{_LOG} 已是MP3，跳过: {file_path}")
                return True, ""

            mp3_path = os.path.join(
                os.path.dirname(file_path),
                f"{os.path.splitext(os.path.basename(file_path))[0]}.mp3",
            )
            if os.path.exists(mp3_path):
                os.remove(mp3_path)

            cmds = [FFMPEG_PATH, "-i", file_path, *_FFMPEG_BASE_ARGS, mp3_path]
            log.info(f"{_LOG} 执行ffmpeg: {' '.join(cmds)}")
            rc, stdout, stderr = run_subprocess_safe(cmds, timeout=_FFMPEG_TIMEOUT_SEC)

            if rc == 0 and os.path.exists(mp3_path):
                os.remove(file_path)
                self._rewrite_file_path(playlist_data, file_path, mp3_path)
                log.info(f"{_LOG} 转换成功: {file_path} -> {mp3_path}")
                return True, ""

            err = stderr or stdout or "未知错误"
            log.error(f"{_LOG} 转换失败: {file_path}, {err}")
            return False, err
        except Exception as e:
            log.error(f"{_LOG} 转换异常: {file_path}, {e}")
            return False, str(e)

    @staticmethod
    def _rewrite_file_path(playlist_data: Dict[str, Any], old_path: str, new_path: str) -> None:
        """把 playlist_data 中所有 uri==old_path 的条目改为 new_path，并清掉过期 duration。"""
        for item in _iter_file_items(playlist_data):
            if item.get("uri") == old_path:
                item["uri"] = new_path
                item.pop("duration", None)
