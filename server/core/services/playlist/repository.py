"""DB-only playlist repository with optimistic configuration and runtime merges.

Redis is read exclusively by the explicit migration/export tooling. The background
worker persists field deltas against its loaded baseline, not whole stale snapshots.
"""

from queue import Empty, Queue
from typing import Any, Callable, Dict, Optional

from gevent import sleep, spawn

from core.config import app_logger
from core.db.db_mgr import db_mgr
from core.services.playlist.calendar_rules import RUNTIME_FIELDS
from copy import deepcopy

log = app_logger

_HISTORY_LIMIT = 10


class PlaylistRepository:
    """负责播放列表数据与 DB 的读写。

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
        self._loaded_storage: Optional[tuple[str, int]] = None

    @property
    def is_ready(self) -> bool:
        return self._loaded_storage is not None

    def invalidate(self) -> None:
        self._loaded_storage = None

    def load_raw(self) -> Dict[str, Any]:
        self.invalidate()
        data = db_mgr.playlist_operation('load')
        self._baseline = deepcopy(data)
        self._loaded_storage = ('db', 1)
        return data

    def get_history(self, limit: int = 10) -> Dict[str, str]:
        return db_mgr.playlist_operation('history', limit)

    def get_calendar(self, start_date, end_date):
        return db_mgr.playlist_operation('calendar', start_date, end_date)

    def refresh_one(self, identifier):
        """Refresh one configuration without advancing other rows' save baselines."""
        row = db_mgr.playlist_operation('load').get(identifier)
        if row is None:
            return None
        self._baseline[identifier] = deepcopy(row)
        target = self._playlist_raw_provider()
        for key in RUNTIME_FIELDS:
            if key in target.get(identifier, {}):
                row[key] = deepcopy(target[identifier][key])
        target[identifier] = row
        return row

    def save(self, swallow_errors=False, *, replace=False, patch=None, deletion=None) -> bool:
        try:
            if not self.is_ready:
                raise RuntimeError('播放列表尚未成功读取，拒绝保存')
            live = deepcopy(self._playlist_raw_provider())
            data = db_mgr.playlist_operation('save', live,
                self._baseline, replace=replace, patch=patch, deletion=deletion, runtime=live)
            self._baseline = deepcopy(data)
            target = self._playlist_raw_provider()
            target.clear()
            target.update(data)
            return True
        except Exception:
            self.invalidate()
            if swallow_errors:
                log.exception('播放列表后台保存失败')
                return False
            raise

    def start_save_worker(self) -> None:
        """启动后台 greenlet 处理 DB 保存队列（单例）。"""
        if self._save_greenlet is not None and not self._save_greenlet.dead:
            return

        def _worker() -> None:
            # 当前所有投递方都只是「请保存一次」的信号，消息体本身无意义；
            # 收到任何非空消息（包括历史遗留的元组 / 字符串）都触发一次保存。
            while True:
                try:
                    # 这里**不能**用阻塞的 `get(timeout=...)`：`queue` 在
                    # `patch_all(queue=False)` 下是原生实现，其超时等待会占住整个
                    # OS 线程（hub）。空闲时该循环反复进入等待，实测把 50ms 的
                    # 心跳拖到约 1 秒，即持续拖慢所有其它请求。
                    # 改为非阻塞取 + 协作式让出，既能及时让出事件循环，
                    # 也把保存周期从 1.1s 缩短到 0.1s。
                    try:
                        self.rds_save_queue.get_nowait()
                        # 单次保存失败时吞掉，避免 worker 自身被外层 try 标记为异常退出
                        self.save(swallow_errors=True)
                    except Empty:
                        pass
                    sleep(0.1)
                except Exception as e:
                    log.error(f"[PlaylistRepository] save worker 异常: {e}", exc_info=True)
                    sleep(1.0)

        self._save_greenlet = spawn(_worker)
