"""播放列表数据的 RDS 读写封装。

P1 阶段从 `core/services/playlist_mgr.py` 抽出。

设计要点：
- 通过 `playlist_raw_provider`（无参函数，返回当前 dict）+ `rds_save_queue` 注入。
  使用 provider 而不是直接传 dict，是因为 `PlaylistMgr` 在 `reload()` / `save_playlist()`
  中会 **重赋值** `self._playlist_raw`（而非 in-place clear/update），直接持有 dict 引用
  会拿到过期对象。
- `start_save_worker` 启动单例 greenlet，从队列拉取 `'save_playlist'` 任务并保存，
  解决了独立线程不能直接写 Redis 的并发问题。
- 历史记录保存失败不影响主流程，只记日志。

兼容性：
- `core/services/playlist_mgr.py` 中保留 `_save_playlist_to_rds`、`_save_playlist_to_rds_safely`、
  `_save_playlist_history`、`_start_rds_save_worker` 作为 thin wrapper 转发到本模块，
  以便现有 `monkeypatch`/`patch` 路径继续生效。
"""

import datetime
import json
from queue import Empty, Queue
from typing import Any, Callable, Dict, Optional

from gevent import sleep, spawn

from core.config import app_logger
from core.db import rds_mgr
from core.services.playlist.constants import PLAYLIST_RDS_FULL_KEY, PLAYLIST_RDS_HISTORY_KEY

log = app_logger

_HISTORY_LIMIT = 10


class PlaylistRepository:
    """负责播放列表数据与 RDS 的读写。

    Args:
        playlist_raw_provider: 无参 Callable，返回当前播放列表 dict（用 provider 避免引用过期）。
        rds_save_queue: 跨线程的保存请求队列。
    """

    def __init__(
        self,
        playlist_raw_provider: Callable[[], Dict[str, Any]],
        rds_save_queue: Queue,
    ) -> None:
        self._playlist_raw_provider = playlist_raw_provider
        self.rds_save_queue = rds_save_queue
        self._save_greenlet: Optional[Any] = None

    def save(self) -> None:
        """保存播放列表到 RDS，同时保存历史记录。"""
        try:
            json_str = json.dumps(self._playlist_raw_provider(), ensure_ascii=False)
            rds_mgr.set(PLAYLIST_RDS_FULL_KEY, json_str)
            self._save_history(json_str)
        except Exception as e:
            log.error(f"[PlaylistMgr] _save_playlist_to_rds error: {e}", exc_info=True)
            raise

    def save_safely(self) -> None:
        """异步持久化用：吞掉异常，避免 spawn 出去的 greenlet 因 Redis 失败影响主流程。"""
        try:
            self.save()
        except Exception as e:
            log.warning(f"[PlaylistMgr] _save_playlist_to_rds_safely error: {e}")

    def _save_history(self, json_str: str) -> None:
        """保存播放列表历史记录到 Redis Hash，最多保留 N 个历史版本。"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rds_mgr.hset(PLAYLIST_RDS_HISTORY_KEY, timestamp, json_str)

            current_count = rds_mgr.hlen(PLAYLIST_RDS_HISTORY_KEY)
            if current_count > _HISTORY_LIMIT:
                history_dict = rds_mgr.hgetall(PLAYLIST_RDS_HISTORY_KEY)
                sorted_keys = sorted(history_dict.keys())
                keys_to_remove = sorted_keys[: current_count - _HISTORY_LIMIT]
                if keys_to_remove:
                    rds_mgr.hdel(PLAYLIST_RDS_HISTORY_KEY, *keys_to_remove)
                    log.info(f"[PlaylistMgr] 清理过期历史记录，删除 {len(keys_to_remove)} 个旧记录")

            log.debug(f"[PlaylistMgr] 保存播放列表历史记录: {timestamp}")
        except Exception as e:
            log.error(f"[PlaylistMgr] _save_playlist_history error: {e}", exc_info=True)
            # 历史记录保存失败不影响主流程，只记录错误

    def start_save_worker(self) -> None:
        """启动后台 greenlet 处理 Redis 保存队列（单例）。"""
        if self._save_greenlet is not None and not self._save_greenlet.dead:
            return

        def _worker() -> None:
            while True:
                try:
                    try:
                        operation = self.rds_save_queue.get(timeout=1.0)
                        if operation == "save_playlist":
                            self.save()
                    except Empty:
                        pass
                    sleep(0.1)
                except Exception as e:
                    log.error(f"[PlaylistMgr] Redis 保存 worker 异常: {e}", exc_info=True)
                    sleep(1.0)

        self._save_greenlet = spawn(_worker)
