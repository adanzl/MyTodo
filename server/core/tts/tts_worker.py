"""TTS SDK 操作的单线程执行器。

为什么需要它（2026-10-16 全面扫描的 P1 项）：

1. **阻塞 hub**：DashScope 的 `SpeechSynthesizer.streaming_complete()` 内部用
   `threading.Event.wait(timeout=complete_timeout_millis/1000)` 等待，默认
   `600000ms = 10 分钟`；`call()` 更是等到整段合成为止。而
   `monkey.patch_all(thread=False)` 使 `threading.Event` 保持**原生**实现，
   所以这些等待会占住整个 OS 线程（hub）——期间所有 HTTP/Socket 请求都排不上。

2. **连接的线程归属**：SDK 的 WebSocket 与创建它的线程绑定，跨线程使用会出现
   `Cannot switch to a different thread` 并可能污染连接池。

把**每个 TTSClient 自己的** SDK 操作投递到它自己的专用 OS 线程即可同时解决两点：
hub 不再被阻塞，连接自始至终属于同一个线程。

**为什么不是全局单例**：单个共享线程会把不同会话的操作排队——A 的
`streaming_complete()`（最长等 10 分钟）会把 B 的合成全部堵住。这与
`hub_dispatch` 曾经踩过的串行化是同一类问题。

**空闲自终止**：客户端数量会随时间增长（TTS 任务各自创建客户端），线程若一直
挂着会累积。空闲超过 `idle_timeout` 后线程自行退出，下次投递时再拉起。

注意这里用阻塞式 `queue.get(timeout=...)` 是**可以接受**的：它运行在本模块自己的
专用线程上，不影响 hub。这与 `hub_dispatch`（消费端在 hub，必须用 `get_nowait`）相反。
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable, Optional

from core.config import app_logger

log = app_logger

# 默认空闲多久后线程自行退出（秒）
DEFAULT_IDLE_TIMEOUT = 60.0


class SdkWorker:
    """串行执行 SDK 操作的单线程执行器，空闲时自动退出。"""

    def __init__(self, name: str = 'tts-sdk', idle_timeout: float = DEFAULT_IDLE_TIMEOUT) -> None:
        self._name = name
        self._idle_timeout = idle_timeout
        self._queue: 'queue.Queue[tuple]' = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        # 保护「线程是否存活」的判断与「入队」这两步，避免空闲退出与投递竞态
        # 导致任务被丢在无人消费的队列里。
        self._lock = threading.Lock()

    def _run(self) -> None:
        while True:
            try:
                action, box, done = self._queue.get(timeout=self._idle_timeout)
            except queue.Empty:
                with self._lock:
                    # 持锁检查：若此刻仍为空才退出并清引用，
                    # 使并发的 submit 能够看到 None 并重新拉起线程。
                    if self._queue.empty():
                        self._thread = None
                        return
                continue

            try:
                box['value'] = action()
            except BaseException as e:  # noqa: BLE001 - 交给等待方或就地记录
                box['error'] = e
            finally:
                if done is not None:
                    done.set()

    def submit(
        self,
        action: Callable[[], Any],
        *,
        wait: bool = False,
        timeout: Optional[float] = None,
    ) -> Any:
        """投递一个操作。

        Args:
            action: 在 SDK 线程上执行的可调用对象。
            wait: 是否等待执行完成。默认「点火即走」——音频通过回调返回，
                调用方（hub）不应等待。
            timeout: wait=True 时的等待上限（秒），超时抛 TimeoutError。

        Returns:
            wait=True 时返回 action 的返回值；否则返回 None。
        """
        box: dict[str, Any] = {}
        done = threading.Event() if wait else None

        # 拉起线程与入队必须在同一把锁内：否则「线程刚判定空闲退出」与
        # 「任务刚入队」可能交错，任务会永远留在队列里没人处理。
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._run, name=self._name, daemon=True
                )
                self._thread.start()
            self._queue.put((action, box, done))

        if not wait or done is None:
            return None

        if not done.wait(timeout):
            raise TimeoutError(f'{self._name} 操作超时（{timeout}s）')
        if 'error' in box:
            raise box['error']
        return box.get('value')

    def wait_pending(self, timeout: float = 10.0) -> None:
        """等待已投递的操作全部执行完。

        队列 FIFO 且串行，因此「投递一个空动作并等它」等价于前面都做完了。
        主要给测试用：把「投递即返回」的异步语义收敛成可断言的同步点。
        """
        self.submit(lambda: None, wait=True, timeout=timeout)

    def discard_pending(self) -> int:
        """丢弃尚未执行的动作，返回被丢弃的数量。

        取消场景要用它：已经排队的文本片段在取消之后不该再发出去。
        等待中的调用方会收到完成信号（`discarded` 标记），避免一直卡到超时。
        """
        dropped = 0
        while True:
            try:
                _action, box, done = self._queue.get_nowait()
            except queue.Empty:
                break
            dropped += 1
            box['discarded'] = True
            if done is not None:
                done.set()
        return dropped

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
