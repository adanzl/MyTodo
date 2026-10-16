"""把真实线程里的回调安全地交回主 hub 执行。

背景（真实故障，2026-10-16）：ASR 的 WebSocket 由
`threading.Thread(target=self.ws.run_forever)` 驱动，因此 `on_result` 回调运行在
**真实 OS 线程**里。而回调链路（`ChatMgr.on_asr_result`）会做 Redis 读写、
`socketio.emit`、发起 `requests` 流式请求——这些对象都归属 hub：

- gevent 的 socket 与创建它的线程绑定，真实线程使用会抛
  "Cannot switch to a different thread"，并可能污染连接池；
- greenlet / socketio 的内部状态在跨线程使用时行为未定义。

所以这些操作必须回到 hub 的 greenlet 上执行。

为什么不用 `gevent.spawn`：它创建的是 **greenlet**，仍然运行在当前（真实）线程，
完全达不到"回到 hub"的目的——这是本文件存在的唯一理由。

实现要点：用 `queue.Queue` 投递。`main.py` 里
`monkey.patch_all(thread=False, queue=False)` 使 `queue` 保持**原生**实现，
因此它自带跨线程所需的条件变量，真实线程 `put` 能让 hub 侧可见。
消费端在主 hub 上，用 `get_nowait` + `gevent_sleep` 轮询——**不能**用阻塞的
`get()`：那会占住整个 OS 线程，反而制造本文件要避免的卡死。
"""

from __future__ import annotations

import queue
from typing import Callable

from gevent import sleep as gevent_sleep

from core.config import app_logger

log = app_logger

# 未被 gevent patch 的原生队列，可安全跨线程传递
_hub_queue: 'queue.Queue[Callable[[], None]]' = queue.Queue()

_POLL_INTERVAL = 0.01
_drain_started = False


def post_to_hub(func: Callable[[], None]) -> None:
    """从任意线程投递一个可调用对象，由主 hub 的 greenlet 执行。

    只做入队，不阻塞、不等待结果；异常在 hub 侧记录，不影响投递方。
    """
    _hub_queue.put(func)


def start_hub_drain() -> None:
    """在 hub 上启动消费循环（幂等）。须在应用初始化时、于任一绿色线程中调用。"""
    global _drain_started
    if _drain_started:
        return
    _drain_started = True

    from gevent import spawn

    def _drain() -> None:
        while True:
            try:
                func = _hub_queue.get_nowait()
            except queue.Empty:
                gevent_sleep(_POLL_INTERVAL)
                continue
            try:
                func()
            except Exception as e:  # noqa: BLE001 - 单个任务失败不能拖垮消费循环
                log.error(f'[HubDispatch] 任务执行失败: {e}', exc_info=True)

    spawn(_drain)
    log.info('[HubDispatch] hub 投递消费循环已启动')
