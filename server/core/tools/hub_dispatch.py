"""把真实线程里的回调安全地交回主 hub 执行。

背景（真实故障，2026-10-16）：ASR 的 WebSocket 由
`threading.Thread(target=self.ws.run_forever)` 驱动，因此 `on_result` 回调运行在
**真实 OS 线程**里。而回调链路（`ChatMgr.on_asr_result`）会做 Redis 读写、
`socketio.emit`、发起 `requests` 流式请求——这些对象都归属 hub：

- gevent 的 socket 与创建它的线程绑定，真实线程使用会抛
  "Cannot switch to a different thread"，并可能污染连接池；
- greenlet / socketio 的内部状态在跨线程使用时行为未定义。

所以这些操作必须回到 hub 的 greenlet 上执行。

**为什么不用 `gevent.spawn` 直接投递**：`spawn` 只是在**当前**（真实）线程上新建
greenlet，达不到"回到 hub"的目的——这是本文件存在的首要理由。

**为什么消费端还要为每个任务再 `spawn` 一次**：回到 hub 之后，
`_handle_asr_result` 会调用 `stream_msg` 并一直读到整段流结束（数十秒）。若消费
循环直接 `func()`，这期间它无法取下一个任务，于是所有用户的语音结果被**串行化**
——A 的对话没结束，B 就得排队。而交回 hub 之前，每个用户的 ASR 各在自己的 ws
线程里，本来就是并发的；串行化是引入本文件时带进来的回归。

在 hub 上为每个任务单独起 greenlet 即可恢复并发：它仍是 hub 线程，线程归属不变，
但 `stream_msg` 读流时会 park 自己，让出事件循环给其它任务。这与"用 spawn 回到
hub"是两件事——这里 spawn 的前提是**已经在 hub 上**。

任务内的异常必须在 greenlet 内部捕获：否则异常会逃逸到 hub 的错误处理，消费循环
虽然不受影响（每个任务已独立），但日志里会缺少可读的上下文。

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
from gevent import spawn

from core.config import app_logger

log = app_logger

_POLL_INTERVAL = 0.01


def _run_task(func: Callable[[], None]) -> None:
    """在独立 greenlet 中执行单个任务，异常就地记录。

    不能在消费循环里直接调用：`stream_msg` 会读到整段流结束，那样会把不同用户的
    对话串行化。
    """
    try:
        func()
    except Exception as e:  # noqa: BLE001 - 单个任务失败不能影响其它任务
        log.error(f'[HubDispatch] 任务执行失败: {e}', exc_info=True)


class HubDispatcher:
    """把任务从任意线程投递回创建它的线程（hub）执行。

    做成类而非模块级全局，是为了让每个实例持有自己的队列与消费循环：
    全局共享时，重复 `start()` 会留下多个消费循环抢同一个队列，既难以推理，
    也让"任务是否被串行化"无法被测试确定地覆盖。

    Args:
        ordered: True 时**严格按投递顺序串行执行**；False（默认）时每个任务各起
            一个 greenlet，可并发、但**不保证任务之间的先后**。
    """

    def __init__(self, ordered: bool = False) -> None:
        # 未被 gevent patch 的原生队列，可安全跨线程传递
        self._queue: 'queue.Queue[Callable[[], None]]' = queue.Queue()
        self._started = False
        self._ordered = ordered

    def post(self, func: Callable[[], None]) -> None:
        """入队，不阻塞、不等待结果。可从任意线程调用。"""
        self._queue.put(func)

    def run_pending(self) -> int:
        """同步执行队列中所有待处理任务（按取出的顺序），返回执行数量。

        主要给测试用：把「投递即返回」的异步语义收敛成一个**确定性的同步点**，
        避免用例依赖 `sleep` 的时序假设（那样在负载高时会偶发失败）。

        与消费循环并存时也安全：`get_nowait` 保证每个任务只会被一方取走，
        因此不会重复执行。
        """
        count = 0
        while True:
            try:
                func = self._queue.get_nowait()
            except queue.Empty:
                return count
            _run_task(func)
            count += 1

    def start(self) -> None:
        """在调用方线程（应为 hub）上启动消费循环。幂等。"""
        if self._started:
            return
        self._started = True
        spawn(self._drain)
        log.info(
            f'[HubDispatch] hub 投递消费循环已启动（{"保序串行" if self._ordered else "并发"}）'
        )

    def _drain(self) -> None:
        while True:
            try:
                func = self._queue.get_nowait()
            except queue.Empty:
                gevent_sleep(_POLL_INTERVAL)
                continue

            if self._ordered:
                # 保序：就地执行，绝不并发。用于**顺序有语义**的回调
                # （例如 TTS 音频分片必须先于完成事件到达）。
                # 这些回调都是协作式的（socketio.emit、Redis 追加），
                # 不会占住 OS 线程，因此串行不会造成 hub 卡死。
                _run_task(func)
            else:
                # 每个任务独立 greenlet：仍运行在 hub 线程上（线程归属不变），
                # 但任务内部的协作式等待会让出事件循环，多段对话得以并发。
                spawn(_run_task, func)


# 进程级单例：生产代码经 post_to_hub / start_hub_drain 使用
_dispatcher = HubDispatcher()
# 保序通道：见 post_to_hub_ordered
_ordered_dispatcher = HubDispatcher(ordered=True)


def post_to_hub(func: Callable[[], None]) -> None:
    """从任意线程投递一个可调用对象，由主 hub 的 greenlet 执行。

    **不保证**多次投递之间的执行顺序（每个任务各起一个 greenlet，可并发）。
    顺序有语义时请用 `post_to_hub_ordered`。
    """
    _dispatcher.post(func)


def post_to_hub_ordered(func: Callable[[], None]) -> None:
    """投递到 hub 的**保序**通道：严格按投递顺序串行执行。

    用于顺序即语义的回调，例如 TTS 的音频分片与紧随其后的「完成」事件：
    若分片之间发生乱序或「完成」先到，前端播放就会错乱。

    代价是这些任务彼此串行（不像 `post_to_hub` 那样并发），因此只应投递
    **短小且协作式**的操作（emit、Redis 追加），不要把整段流式读取放进来。
    """
    _ordered_dispatcher.post(func)


def start_hub_drain() -> None:
    """在 hub 上启动消费循环（幂等）。须在应用初始化时调用。"""
    _dispatcher.start()
    _ordered_dispatcher.start()


def run_pending_hub_tasks() -> int:
    """同步执行两个通道中所有待处理任务（保序通道按 FIFO）。

    测试用：把交回 hub 的异步回调收敛成可断言的同步点。
    生产环境由消费循环处理，无需调用。
    """
    return _dispatcher.run_pending() + _ordered_dispatcher.run_pending()
