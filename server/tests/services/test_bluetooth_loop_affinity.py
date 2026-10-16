"""BLE 事件循环亲和性回归测试。

## 缺陷（修复前）

`bluetooth_mgr` 用 `async_util.run_async` 跑 BLE 协程，而 `run_async` 每次调用都
「新起线程 → `asyncio.run` → 循环用完即关」。`BleakClient` 却被缓存在
`BluetoothDev.client` 上跨调用复用：

    connect_device            （第 1 次 run_async，循环 A）→ 创建 client、connect
    _get_device_name_from_gatt（同一次调用内，循环 A）→ 读 GATT，正常
    disconnect_device         （第 2 次 run_async，循环 B）→ 再用 device.client，
                                                         可它绑在已关闭的循环 A

于是 disconnect（以及任何后续 GATT 操作）必然失败：
`RuntimeError: Event loop is closed`。症状是「能连上，但之后再也断不开」。

## 这些用例如何抓住回归

- 走**真实**的 `*_sync` 入口（不替换 `bm.run_async`），只把硬件层的 `BleakClient`
  换成复刻 bleak「循环亲和性」的假实现（无蓝牙硬件也能跑）。
- 改回「每次新建循环」→ `test_cached_client_is_reused_on_the_same_loop` 等用例失败；
- 改成「单循环但用原生阻塞的 `future.result(timeout)` 等待」→ hub 探针用例失败。

`fake_client` 记录每次操作所在的循环 id 与创建它的线程，一眼就能看出是否跨循环。
"""

import asyncio
import textwrap
import threading
import time

import pytest

import core.services.bluetooth_mgr as bm
from core.tools.async_loop import get_runner
from tests.services._probe_helper import run_probe_resilient

ADDR = "AA:BB:CC:DD:EE:FF"
ADDR2 = "11:22:33:44:55:66"


class LoopBoundFakeClient:
    """复刻 bleak 的循环亲和性。

    真实 `BleakClient.connect()` 会在当时的事件循环上创建 asyncio 原语
    （Future / Event / transport 与后端 task），之后这些对象只能在**同一个**循环
    上使用：循环关闭 → `Event loop is closed`；换了循环 → `Future attached to a
    different loop`。这里用「记录 loop id + 校验」把它显式化。
    """

    instances: list["LoopBoundFakeClient"] = []

    def __init__(self, address, *args, **kwargs):
        self.address = address
        self.loop = None
        self._gate = None
        self.create_thread = threading.current_thread()
        self.calls: list[tuple[str, int]] = []  # (操作, 运行它的 loop id)
        LoopBoundFakeClient.instances.append(self)

    # ---------------------------------------------------------------- 内部

    def _check_loop(self, op: str) -> asyncio.AbstractEventLoop:
        """模拟 bleak 在复用的绑定对象上做的 loop 校验。"""
        loop = asyncio.get_running_loop()
        self.calls.append((op, id(loop)))
        if self.loop is None:
            raise RuntimeError(f"{op}: 尚未 connect")
        if self.loop.is_closed():
            raise RuntimeError(f"{op}: Event loop is closed")
        if loop is not self.loop:
            raise RuntimeError(
                f"{op}: 跨事件循环使用同一个 client"
                f"（connect 在 loop {id(self.loop)}，现在在 loop {id(loop)}）")
        return loop

    @property
    def used_loops(self) -> set[int]:
        return {loop_id for _, loop_id in self.calls}

    # --------------------------------------------------------- BleakClient 接口

    async def connect(self, **kwargs):
        self.loop = asyncio.get_running_loop()
        self.calls.append(("connect", id(self.loop)))
        # connect() 内创建的、绑定当前循环的 Future；跨循环 await 就会炸
        self._gate = self.loop.create_future()
        self.loop.call_soon(self._gate.set_result, None)

    async def disconnect(self):
        self._check_loop("disconnect")
        await self._gate

    async def read_gatt_char(self, uuid, **kwargs):
        self._check_loop("read_gatt_char")
        return b"LoopName"


class HangingFakeClient(LoopBoundFakeClient):
    """connect 永远不返回：用于验证超时路径。"""

    async def connect(self, **kwargs):
        self.loop = asyncio.get_running_loop()
        self.calls.append(("connect", id(self.loop)))
        await asyncio.sleep(300.0)  # pragma: no cover - 会被取消


@pytest.fixture(autouse=True)
def fake_bleak(monkeypatch):
    """只替换硬件层；`bm.run_async`（别名 `run_async_on_loop`）保持真实。"""
    LoopBoundFakeClient.instances = []
    monkeypatch.setattr(bm, "BleakClient", LoopBoundFakeClient)
    return LoopBoundFakeClient


def _connect(mgr, address=ADDR, timeout=5.0):
    return mgr.connect_device_sync(address, timeout=timeout)


def test_cached_client_is_reused_on_the_same_loop(fake_bleak):
    """核心回归：connect 缓存的 client，disconnect 时必须在**同一个**循环上。

    修复前：disconnect 走新循环 → "Event loop is closed" → code=-1。
    """
    mgr = bm.BluetoothMgr()

    conn = _connect(mgr)
    assert conn["code"] == 0, conn

    client = mgr.devices[ADDR].client
    assert client is not None
    assert not client.loop.is_closed(), "connect 用的循环被关掉了（这就是缺陷本身）"

    disc = mgr.disconnect_device_sync(ADDR, timeout=5.0)
    assert disc["code"] == 0, f"断开失败（正是修复前的症状）: {disc}"
    assert disc["msg"] == "Disconnected"
    assert mgr.devices[ADDR].connected is False

    assert len(client.used_loops) == 1, (
        f"同一个 client 被用在多个事件循环上: {client.calls}")
    assert client.used_loops == {id(client.loop)}


def test_client_is_created_on_the_shared_persistent_loop(fake_bleak):
    """client 的创建与使用都在那条持久循环上，且它就是共享 runner 的循环。"""
    mgr = bm.BluetoothMgr()
    assert _connect(mgr)["code"] == 0

    client = mgr.devices[ADDR].client
    runner = get_runner()
    assert client.loop is runner.loop, "BLE 没有跑在共享的持久事件循环上"
    assert not client.loop.is_closed()
    assert client.create_thread is runner.thread, "client 不是在循环线程里创建的"
    assert client.create_thread is not threading.current_thread()


def test_gatt_name_read_happens_on_the_same_loop_as_connect(fake_bleak):
    """connect 内的 GATT 读取与 connect 同循环，返回的 client 仍可继续使用。

    注意触发条件：`connect_device` 只在设备名「为空或等于地址」时才读 GATT
    （名称等于地址是 bleak 扫描无名字设备的常见结果），所以这里按扫描结果预置设备。
    """
    mgr = bm.BluetoothMgr()
    mgr._update_or_create_device(ADDR, ADDR, {})

    assert _connect(mgr)["code"] == 0
    assert mgr.devices[ADDR].name == "LoopName"

    client = mgr.devices[ADDR].client
    ops = [op for op, _ in client.calls]
    assert ops[0] == "connect", ops
    assert "read_gatt_char" in ops, f"没有真的读 GATT，用例失去意义: {ops}"
    assert len(client.used_loops) == 1, client.calls

    # 读完 GATT 之后还能正常断开（跨调用复用同一 client）
    assert mgr.disconnect_device_sync(ADDR, timeout=5.0)["code"] == 0
    assert len(client.used_loops) == 1, client.calls


def test_repeated_connect_disconnect_cycles_keep_working(fake_bleak):
    """反复连接/断开：每个 client 都绑定同一条持久循环，不因复用而失效。"""
    mgr = bm.BluetoothMgr()

    for i in range(3):
        assert _connect(mgr)["code"] == 0, f"第 {i + 1} 轮连接失败"
        client = mgr.devices[ADDR].client
        assert mgr.disconnect_device_sync(ADDR, timeout=5.0)["code"] == 0, \
            f"第 {i + 1} 轮断开失败"
        assert len(client.used_loops) == 1, client.calls

    assert len(fake_bleak.instances) == 3


def test_concurrent_operations_share_one_loop(fake_bleak, monkeypatch):
    """scan / connect / disconnect 三类操作都必须落在同一条循环上。"""
    loop_ids: list[int] = []

    async def fake_discover(timeout, return_adv):
        assert return_adv is True
        loop_ids.append(id(asyncio.get_running_loop()))
        return {}

    monkeypatch.setattr(bm.BleakScanner, "discover", fake_discover)

    mgr = bm.BluetoothMgr()
    assert mgr.scan_devices_sync(timeout=0.01) == []
    assert _connect(mgr)["code"] == 0
    client = mgr.devices[ADDR].client
    assert mgr.disconnect_device_sync(ADDR, timeout=5.0)["code"] == 0

    assert loop_ids, "扫描没有真的跑起来，用例失去意义"
    assert set(loop_ids) == client.used_loops, (
        f"扫描与连接/断开用了不同的循环: scan={loop_ids}, client={client.calls}")


def test_hanging_connect_times_out_without_poisoning_the_loop(monkeypatch):
    """挂死的 connect 必须按超时返回（不能无限等），且循环之后仍可用。"""
    monkeypatch.setattr(bm, "BleakClient", HangingFakeClient)
    mgr = bm.BluetoothMgr()

    t0 = time.monotonic()
    res = mgr.connect_device_sync(ADDR, timeout=0.4)
    elapsed = time.monotonic() - t0

    assert res["code"] == -1, res
    assert "timeout" in res["msg"].lower(), res
    assert elapsed < 5.0, f"超时没有生效（耗时 {elapsed:.2f}s）"
    # connect 没成功，设备不应被标记为已连接（connect 失败时不写缓存）
    assert ADDR not in mgr.devices or mgr.devices[ADDR].connected is False

    # 同一条循环上继续正常干活
    monkeypatch.setattr(bm, "BleakClient", LoopBoundFakeClient)
    assert _connect(mgr, ADDR2)["code"] == 0
    assert mgr.devices[ADDR2].client.loop is get_runner().loop


# --------------------------------------------------------------------------- hub
#
# 等待循环上的结果有两条路：`future.done()` + `gevent_sleep` 轮询（协作式，hub 照常
# 调度），或 `future.result(timeout)`（threading 未被 patch，是**原生阻塞**，会把整个
# OS 线程占住）。第二种写法能通过上面所有用例，却会让别的请求全部排不上，所以这里
# 单独用子进程探针守住：这类缺陷是「进程卡住」而不是「报错」，必须外部超时兜底。
_HUB_PROBE = textwrap.dedent("""
    from gevent import monkey
    monkey.patch_all(subprocess=True, thread=False, queue=False)

    import asyncio, threading, time
    from gevent import sleep, spawn

    # 证人 greenlet 持续记录时间戳；hub 被卡住多久，相邻间隔就有多长。
    # 不能用「调用期间测心跳」：hub 被阻塞时测量代码自己也排不上队。
    witness = []
    def witness_loop():
        while True:
            witness.append(time.monotonic())
            sleep(0.01)
    spawn(witness_loop)
    sleep(0.3)

    def max_gap_between(t0, t1):
        ticks = [t for t in witness if t0 <= t <= t1]
        if len(ticks) < 2:
            return t1 - t0
        return max(b - a for a, b in zip(ticks, ticks[1:]))

    now = time.monotonic()
    print('BASE_GAP=%.4f' % max_gap_between(now - 1.0, now))

    import core.services.bluetooth_mgr as bm

    class FakeClient:
        def __init__(self, address, *a, **k):
            self.address = address
            self.loop = None
            self.ops = []
        async def connect(self, **k):
            self.loop = asyncio.get_running_loop()
            self.ops.append(('connect', id(self.loop)))
        async def read_gatt_char(self, uuid, **k):
            self.loop_check('read_gatt_char')
            return b''
        async def disconnect(self):
            self.loop_check('disconnect')
            await asyncio.sleep(1.0)      # 模拟耗时的真实断开
        def loop_check(self, op):
            loop = asyncio.get_running_loop()
            self.ops.append((op, id(loop)))
    bm.BleakClient = FakeClient

    mgr = bm.BluetoothMgr()
    print('CONNECT=%s' % mgr.connect_device_sync('AA:BB:CC:DD:EE:FF', timeout=5.0)['code'])
    client = mgr.devices['AA:BB:CC:DD:EE:FF'].client

    t0 = time.monotonic()
    res = mgr.disconnect_device_sync('AA:BB:CC:DD:EE:FF', timeout=5.0)
    t1 = time.monotonic()
    print('DISCONNECT=%s' % res['code'])
    print('ELAPSED=%.3f' % (t1 - t0))
    print('MAX_GAP=%.4f' % max_gap_between(t0, t1))
    print('LOOPS=%d' % len({lid for _, lid in client.ops}))
    print('DONE')
""")


def test_ble_disconnect_does_not_block_hub(tmp_path):
    """BLE 断开期间 hub 必须照常被调度（不能原生阻塞等待循环结果）。

    探针在独立子进程里跑（卡死是这类缺陷的表现，需要外部超时），
    同时验证「断开成功」与「同一个循环」——两条要求一次覆盖。

    用带负载重试的运行器：机器繁忙时基线会偏大，此时测量无法判定；
    曾因本地并行跑第二个全量测试而误报过失败。
    """
    proc = run_probe_resilient(_HUB_PROBE, tmp_path, timeout=90)
    assert proc.returncode == 0, f'BLE 探针失败:\n{proc.stdout}\n{proc.stderr}'

    def value(key):
        line = [l for l in proc.stdout.splitlines() if l.startswith(key + '=')]
        assert line, f'探针未产出 {key}:\n{proc.stdout}'
        return line[0].split('=', 1)[1]

    base = float(value('BASE_GAP'))
    gap = float(value('MAX_GAP'))
    assert value('CONNECT') == '0', f'连接失败:\n{proc.stdout}'
    assert value('DISCONNECT') == '0', f'断开失败（跨循环复用 client）:\n{proc.stdout}'
    assert int(value('LOOPS')) == 1, (
        f'connect/disconnect 落在了不同的循环上:\n{proc.stdout}')
    assert float(value('ELAPSED')) >= 0.9, (
        f'断开没有真的耗时，用例失去意义:\n{proc.stdout}')
    assert base < 0.1, f'基线心跳本身异常（{base:.3f}s），环境负载过高，无法判定'
    assert gap <= 0.25, (
        f'BLE 断开把 hub 阻塞了约 {gap:.2f}s（正常应 ~{base:.3f}s）：'
        f'等待循环结果时不能用原生阻塞的 future.result()\n{proc.stdout}')
