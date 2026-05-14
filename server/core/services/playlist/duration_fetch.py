"""媒体时长获取（单文件同步 / 全量后台批量）。

设计要点：
- `get_media_duration` 底层是 `subprocess(ffprobe)`，**真阻塞 syscall**；批量获取必须跑在
  OS 线程里，否则会卡死 gevent hub。
- 线程内不能直接调 `rds_mgr.*`（gevent monkey-patched socket 在没 hub 的线程里行为未定义），
  所以线程结束时只往 `rds_save_queue` 里投一个 `'save_playlist'` 信号，
  由 `PlaylistRepository.start_save_worker` 起的 greenlet 兜底落库。
- 单例线程：用 `threading.Lock` + 线程引用，保证同一时刻只有一个 ffprobe 队列在跑，
  避免重复打爆 I/O。
- 黑名单：`Counter` 记录失败次数；同一文件失败超过 ``_BLACKLIST_THRESHOLD`` 次后
  ``collect_files_without_duration(check_blacklist=True)`` 不再返回它，避免反复重试坏文件。
"""

import threading
from collections import Counter
from queue import Queue
from typing import Any, Callable, Dict, Iterator, Optional, Set

from core.config import app_logger
from core.utils import get_media_duration

log = app_logger
_LOG = "[DurationFetcher]"
_BLACKLIST_THRESHOLD = 3


def _iter_file_items(playlist_data: Dict[str, Any]) -> Iterator[Any]:
    """遍历 playlist_data 内全部 file_item（pre_lists 7 天 + playlist）。

    仅产出 ``dict`` 项；``playlist`` 缺失或非 list 时跳过，避免 ``yield from None``。
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


class DurationFetcher:
    """媒体时长获取器。

    Args:
        playlist_raw_provider: 无参 Callable，返回当前播放列表 dict（同 repository 的设计，
            避免 `_playlist_raw` 被重赋值后引用过期）。
        rds_save_queue: 线程→greenlet 的保存信号队列；批量获取完成后线程会 ``put`` 一次。
        save_async: 单文件 duration 更新成功后调用的「请异步落一次库」回调；应当在 gevent 侧
            起 greenlet，例如 ``lambda: spawn(repo.save, swallow_errors=True)``。
    """

    def __init__(
        self,
        *,
        playlist_raw_provider: Callable[[], Dict[str, Any]],
        rds_save_queue: Queue,
        save_async: Callable[[], Any],
    ) -> None:
        self._playlist_raw_provider = playlist_raw_provider
        self._rds_save_queue = rds_save_queue
        self._save_async = save_async
        self.blacklist: Counter[str] = Counter()
        self._thread: Optional[threading.Thread] = None
        self._thread_lock = threading.Lock()

    # ---------- 单文件同步路径（gevent 侧） ----------

    def update_file_duration(self, file_path: str, file_item: Any) -> Optional[int]:
        """同步获取单个文件的时长并写回 file_item；成功后触发 save_async。"""
        if not file_path:
            return None
        if file_item.get("duration"):
            return file_item.get("duration")

        duration = get_media_duration(file_path)
        log.info(f"{_LOG} 获取文件时长: {file_path}, {duration}")
        if duration is None:
            return None

        seconds = int(duration)
        file_item["duration"] = seconds
        self._save_async()
        return seconds

    # ---------- 纯函数式工具：扫描 / 写回 ----------

    def collect_files_without_duration(
        self,
        playlist_data: Dict[str, Any],
        check_blacklist: bool = True,
    ) -> Set[str]:
        """收集播放列表中没有 duration 的文件 URI（覆盖 7 天 pre_lists 与 playlist）。"""
        out: Set[str] = set()
        for file_item in _iter_file_items(playlist_data):
            self._maybe_add(file_item, out, check_blacklist)
        return out

    def _maybe_add(self, file_item: Any, target: Set[str], check_blacklist: bool) -> None:
        if file_item.get("duration"):
            return
        file_uri = file_item.get("uri")
        if not file_uri:
            return
        if check_blacklist and self.blacklist.get(file_uri, 0) >= _BLACKLIST_THRESHOLD:
            return
        target.add(file_uri)

    def update_files_duration(
        self,
        playlist_data: Dict[str, Any],
        file_durations: Dict[str, int],
    ) -> int:
        """把 ``file_durations`` 里的时长写回 playlist_data，返回更新条数。"""
        return sum(self._write_back(file_item, file_durations) for file_item in _iter_file_items(playlist_data))

    @staticmethod
    def _write_back(file_item: Any, file_durations: Dict[str, int]) -> int:
        file_uri = file_item.get("uri")
        if file_uri and file_uri in file_durations and not file_item.get("duration"):
            file_item["duration"] = file_durations[file_uri]
            return 1
        return 0

    # ---------- 后台批量路径（OS 线程） ----------

    def start_batch_fetch(self, playlists: Dict[str, Dict[str, Any]]) -> None:
        """启动单例后台线程批量获取所有缺失 duration 的文件。

        线程结束时往 ``rds_save_queue`` 投递 ``'save_playlist'`` 通知 worker 落库；
        本方法不会等待线程完成。
        """
        files_to_fetch: Set[str] = set()
        for playlist_data in playlists.values():
            files_to_fetch.update(self.collect_files_without_duration(playlist_data, check_blacklist=True))

        if not files_to_fetch:
            return

        thread = self._create_batch_thread_if_idle(files_to_fetch)
        if thread is not None:
            # 勿在持锁状态下 start()：单测 FakeThread 同步执行时，worker finally 会再抢同一把锁而死锁。
            thread.start()

    def _create_batch_thread_if_idle(self, files_to_fetch: Set[str]) -> Optional[threading.Thread]:
        with self._thread_lock:
            if self._thread is not None and self._thread.is_alive():
                log.debug(f"{_LOG} 批量获取时长的线程正在运行，跳过本次启动")
                return None
            log.info(f"{_LOG} 发现 {len(files_to_fetch)} 个文件需要获取时长，启动批量获取线程")
            self._thread = threading.Thread(
                target=self._batch_worker,
                args=(files_to_fetch,),
                daemon=True,
                name="PlaylistDurationFetcher",
            )
            return self._thread

    def _batch_worker(self, files_to_fetch: Set[str]) -> None:
        file_durations: Dict[str, int] = {}
        failed_uris: list[str] = []
        try:
            for file_uri in files_to_fetch:
                try:
                    duration = get_media_duration(file_uri)
                except Exception as e:
                    log.warning(f"{_LOG} 获取文件时长异常: {file_uri}, {e}")
                    failed_uris.append(file_uri)
                    self.blacklist[file_uri] += 1
                    continue

                if duration is not None:
                    file_durations[file_uri] = int(duration)
                    self.blacklist.pop(file_uri, None)
                else:
                    log.warning(f"{_LOG} 获取文件时长失败: {file_uri}, duration=None")
                    failed_uris.append(file_uri)
                    self.blacklist[file_uri] += 1

            updated_count = sum(
                self.update_files_duration(playlist_data, file_durations)
                for playlist_data in self._playlist_raw_provider().values()
            )

            if updated_count > 0:
                self._rds_save_queue.put("save_playlist")
                log.info(
                    f"{_LOG} 批量获取时长完成: 成功 {updated_count} 个, "
                    f"失败 {len(failed_uris)} 个, 失败文件: {failed_uris}"
                )
        except Exception as e:
            log.error(f"{_LOG} 批量获取时长线程异常: {e}")
        finally:
            with self._thread_lock:
                self._thread = None
