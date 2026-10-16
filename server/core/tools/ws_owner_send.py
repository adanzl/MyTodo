"""让 WebSocket 的发送发生在「连接所属线程」上。

## 为什么需要

`monkey.patch_all(...)` 把 socket 换成了 gevent 版本。gevent 的 socket 绑定在
**创建它的那个线程**的 hub 上，从别的线程使用会抛：

    Cannot switch to a different thread

而 websocket-client 的连接与发送天然分属两个线程：

    run_forever 线程   → WebSocketApp.connect → 创建并连接 socket（socket 归它）
    业务线程           → ws.send(...)          ← 跨线程使用该 socket

更麻烦的是它**不是每次都报错**：只有当发送需要等待（对端不收、TCP 发送缓冲写满）
时才触发。于是表现为偶发失败 + 连接状态被写坏，严重时把 hub 卡死。
2026-10-16 的停摆就是这一类：日志里刷了 54 次该错误，随后 10 分钟零输出。

本机实测（同一进程，socket 在 run_forever 线程创建，从另一线程发送并制造背压）：

    直接发送            → Cannot switch to a different thread（第 4 次发送时触发）
    调度到所属线程发送  → 无错误，背压下正常阻塞

## 做法

不替换 socket/ssl，而是把发送**调度到持有该 socket 的线程**执行：

1. `app.sock.sock.hub` 就是持有该连接的 hub；`hub.thread_ident` 指出所属线程；
2. `hub.loop.run_callback` 是**线程安全**的（libev/libuv 的 async watcher），
   可在任意线程投递；
3. `WebSocketApp.run_forever` 的读循环里 `Dispatcher.read` 用
   `selectors.DefaultSelector().select(...)`，而 selectors 已被 patch，因此它在
   等待数据时会让出到该线程的 hub loop —— 我们排入的回调会被及时执行。

于是无论调用方在哪个线程，实际的 `send` 都发生在 socket 所属线程上，符合 gevent
的线程归属要求。

## 为什么不用「把 socket/ssl 换成原生实现」

那条路试过，走不通：

- **标准库 ssl.py 在 gevent 下整体不可用**。它多处用
  `super(SSLContext, SSLContext).xxx.__set__(...)` / `super(SSLSocket, self)` 这类
  写法，运行时解析**模块全局名**；gevent 已把这些名字替换成自己的子类，于是要么
  无限递归（`verify_mode`），要么 `obj is not an instance or subtype of type`
  （`SSLSocket._create`）。生产用的正是 `wss://`，因此该方案不可行。
- 只换 socket、保留 gevent 的 ssl，跨线程发送**依然失败**（SSL 层仍走 hub）。

## 阻塞策略

- 调用方**就是** socket 所属线程 → 直接发送（也是消费回调时的路径）；
- 调用方是 **hub 线程** → 只入队、不等待。hub 绝不能被阻塞（这正是要修的问题），
  因此发送失败只记录日志；
- 调用方是**其它真实线程**（例如 TTS SDK 的工作线程）→ 等待完成，让调用方能拿到
  错误、并保证顺序性。
"""

from __future__ import annotations

import queue
import threading
import weakref
from typing import Any, Callable, Optional

from gevent import get_hub, spawn

from core.config import app_logger

log = app_logger

_installed = False

# hub 线程的 ident：install() 在模块导入时执行，那时正处于主 hub 线程。
# 用它区分「调用方是 hub」与「调用方是普通工作线程」。
_HUB_THREAD_IDENT: Optional[int] = None

_state_lock = threading.Lock()
_states: 'weakref.WeakKeyDictionary[Any, _SendState]' = weakref.WeakKeyDictionary()


class _SendState:
    """一个 WebSocketApp 的待发送队列与调度标记。"""

    __slots__ = ('queue', 'scheduled')

    def __init__(self) -> None:
        # 未被 gevent patch 的原生队列，可安全跨线程传递
        self.queue: 'queue.Queue[tuple]' = queue.Queue()
        self.scheduled = False


def _state_for(app: Any) -> _SendState:
    with _state_lock:
        state = _states.get(app)
        if state is None:
            state = _SendState()
            _states[app] = state
        return state


def _owner_hub(app: Any):
    """取持有该连接 socket 的 hub；连接尚未建立或不是 gevent socket 时返回 None。"""
    ws = getattr(app, 'sock', None)          # websocket.WebSocket
    sock = getattr(ws, 'sock', None)         # gevent socket（未 patch 时是标准库 socket）
    return getattr(sock, 'hub', None)


def _drain(state: _SendState) -> None:
    """在 socket 所属线程上执行排队中的发送（按入队顺序）。

    必须作为**greenlet** 运行，不能直接放在 hub 的 loop 回调里：背压时
    `send` 会让出等待，而在 loop 回调中调用阻塞操作会抛
    `BlockingSwitchOutError`（gevent 不允许在回调里阻塞事件循环）。
    """
    while True:
        with _state_lock:
            try:
                call, box, done = state.queue.get_nowait()
            except queue.Empty:
                # 清标记必须在持锁状态下与「队列为空」一起判断：
                # 否则并发的入队会看到 scheduled=True 而不调度，任务就留在队列里没人处理。
                state.scheduled = False
                return
        try:
            box['result'] = call()
        except BaseException as e:  # noqa: BLE001
            box['error'] = e
            if done is None:
                # 非阻塞路径（hub 调用方）没有等待方来检查 box，
                # 异常必须在这里记录，否则发送失败会**完全静默**
                log.error(f'[WS] 发送失败（异步）：{e}', exc_info=True)
        finally:
            if done is not None:
                done.set()


def _wake(state: _SendState) -> None:
    """loop 回调：只负责唤醒一个 greenlet 去发送，本身不做任何阻塞操作。"""
    spawn(_drain, state)


def _schedule(state: _SendState, hub: Any) -> None:
    """把唤醒回调排到 hub 的 loop 上（幂等：已有待执行回调时不重复排）。

    `hub.loop.run_callback` 是线程安全的（libev/libuv 的 async watcher），
    因此可以从任意线程把控制权交回 socket 所属线程。
    """
    with _state_lock:
        if state.scheduled:
            return
        state.scheduled = True
    hub.loop.run_callback(_wake, state)


def send_on_owner(app: Any, call: Callable[[], Any], *, timeout: float = 15.0) -> Any:
    """把一次发送调度到 socket 所属线程执行。

    Args:
        app: `WebSocketApp` 实例（用来定位它的 socket 与所属 hub）。
        call: 真正执行发送的可调用对象，在所属线程上被调用。
        timeout: 非 hub 调用方的等待上限（秒）。

    Returns:
        所属线程上 `call()` 的返回值；hub 调用方（不等待）返回 None。

    Raises:
        TimeoutError: 连接所属线程长时间未处理该发送。
    """
    hub = _owner_hub(app)
    current = threading.get_ident()

    # 已是同线程（或不是 gevent socket）：直接发送，避免无谓的调度开销
    if hub is None or getattr(hub, 'thread_ident', None) == current:
        return call()

    state = _state_for(app)
    on_hub = _HUB_THREAD_IDENT is not None and current == _HUB_THREAD_IDENT
    done = None if on_hub else threading.Event()
    box: dict[str, Any] = {}

    state.queue.put((call, box, done))
    _schedule(state, hub)

    if done is None:
        # hub 不能被阻塞：只入队，错误由 drain 或调用链自行上报
        return None

    if not done.wait(timeout):
        raise TimeoutError(
            'WebSocket 发送调度超时：连接所属线程未处理该发送（'
            '该线程可能已阻塞或已退出）'
        )
    if 'error' in box:
        raise box['error']
    return box.get('result')


def _wrap_send(method_name: str) -> Callable[..., Any]:
    """把 WebSocketApp 的某个发送方法包装成「调度到所属线程」。"""

    def wrapper(self, *args, **kwargs):
        original = _original_methods[method_name]

        def call():
            return original(self, *args, **kwargs)

        return send_on_owner(self, call)

    wrapper.__name__ = method_name
    wrapper.__doc__ = f'把 `{method_name}` 调度到 socket 所属线程执行（见模块说明）。'
    return wrapper


def _wrap_call_soon(method_name: str) -> Callable[..., Any]:
    """包装 `run_forever` 之类：不改行为，仅保留原实现。"""
    original = _original_methods[method_name]

    def wrapper(self, *args, **kwargs):
        return original(self, *args, **kwargs)

    wrapper.__name__ = method_name
    return wrapper


# 需要接管的发送方法。WebSocketApp 暴露 send / send_bytes / send_text，
# 我们自己的 ASR/TTS 客户端与 DashScope SDK 都经由它们发送。
_SEND_METHODS = ('send', 'send_bytes', 'send_text')

_original_methods: dict[str, Callable[..., Any]] = {}


def install() -> bool:
    """接管 `WebSocketApp` 的发送方法（幂等）。

    Returns:
        是否安装成功；已安装时直接返回 True。
    """
    global _installed, _HUB_THREAD_IDENT
    if _installed:
        return True

    try:
        from websocket import WebSocketApp
    except ImportError:  # pragma: no cover - websocket-client 是硬依赖
        log.warning('[WS] 未安装 websocket-client，跳过发送线程归属处理')
        return False

    # 记录当前线程为 hub 线程：install() 在模块导入时执行，那时正是主 hub 线程
    try:
        _HUB_THREAD_IDENT = get_hub().thread_ident
    except Exception:  # noqa: BLE001 - 极端情况下取不到就退化为「一律等待」
        _HUB_THREAD_IDENT = None

    for name in _SEND_METHODS:
        original = getattr(WebSocketApp, name, None)
        if original is None:
            continue
        _original_methods[name] = original
        setattr(WebSocketApp, name, _wrap_send(name))

    _installed = True
    log.info(
        f'[WS] 已接管 WebSocketApp 发送（{len(_original_methods)} 个方法），'
        '发送将调度到连接所属线程'
    )
    return True


def is_installed() -> bool:
    return _installed


def hub_thread_ident() -> Optional[int]:
    return _HUB_THREAD_IDENT
