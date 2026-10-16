"""Redis 客户端按线程隔离的回归测试。

背景（真实故障，2026-10-16）：服务运行十几分钟后整个进程冻结、日志完全空白、
只能重启。根因是 `rds_mgr` 用一个全局 Redis 客户端给所有线程共用：

1. gevent 下 socket 与创建它的线程绑定。hub（主线程）建立的连接被 TTS 的 ws
   线程（真实 OS 线程）复用时抛 "Cannot switch to a different thread"
   （日志里 54 次）；redis-py 的 `get_connection` 在 `except BaseException` 中会
   把这条坏连接 `release()` 回 `_available_connections`，之后 hub 再取到它就会
   永久阻塞。
2. 连接池的 `_lock` 是 `threading.Lock`，而 `main.py` 用
   `patch_all(thread=False)` —— 它是**真实锁**。hub 的 greenlet 一旦等在这把锁上，
   gevent 的 `Timeout` 无法中断（已实测：`with Timeout(3)` 包裹后进程永久冻结），
   于是全站停摆。

修复方式：按 OS 线程隔离客户端。这些测试锁住"隔离"这一不变量 —— 一旦有人改回
全局共享，它们必须失败。
"""

import threading

import fakeredis
import pytest

import core.db.rds_mgr as rds_mgr


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    """注入 fake 客户端，并避免真实构造连接。

    新线程会通过 `_create_redis_client()` 惰性建客户端，测试里换成连到**同一个
    FakeServer** 的新实例：既能直接比较实例是否隔离，又能验证"隔离的是连接、
    不是数据"。
    """
    server = fakeredis.FakeServer()
    fake = fakeredis.FakeRedis(server=server)
    monkeypatch.setattr(rds_mgr, 'rds', fake)
    monkeypatch.setattr(rds_mgr, '_local_store', None)
    monkeypatch.setattr(rds_mgr, 'is_local_fallback', False)
    monkeypatch.setattr(
        rds_mgr, '_create_redis_client',
        lambda: fakeredis.FakeRedis(server=server),
    )
    # 让代次回到基线，避免测试间相互影响
    monkeypatch.setattr(rds_mgr, '_client_generation', 0)
    yield rds_mgr


def _run_in_thread(fn):
    """在真实 OS 线程里执行并收集返回值（模拟 TTS ws 线程）。"""
    box = {}

    def wrapper():
        try:
            box['value'] = fn()
        except BaseException as e:  # noqa: BLE001 - 测试要看到任何异常
            box['error'] = e

    t = threading.Thread(target=wrapper)
    t.start()
    t.join(10)
    assert not t.is_alive(), "线程未结束（可能被阻塞）"
    if 'error' in box:
        raise box['error']
    return box['value']


def test_main_thread_reuses_global_client(isolated_env):
    """主线程（hub）复用全局 rds：保持单一注入点，也避免多建连接。"""
    assert rds_mgr._current_client() is rds_mgr.rds


def test_worker_thread_does_not_share_the_hub_client(isolated_env):
    """真实线程不得复用 hub 的客户端。

    这是本次故障的核心：复用会让该线程跨线程使用 hub 建立的 socket。
    """
    client = _run_in_thread(rds_mgr._current_client)

    assert client is not rds_mgr.rds


def test_same_thread_reuses_its_own_client(isolated_env):
    """同一线程内多次取用应复用同一实例（连接池惰性创建）。"""
    seen = _run_in_thread(
        lambda: [rds_mgr._current_client(), rds_mgr._current_client()]
    )

    assert seen[0] is seen[1]


def test_each_thread_gets_a_distinct_client(isolated_env):
    """多个真实线程之间必须彼此隔离，各自持有独立连接池与锁。"""
    clients = []
    lock = threading.Lock()

    def collect():
        c = rds_mgr._current_client()
        with lock:
            clients.append(c)

    threads = [threading.Thread(target=collect) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    for t in threads:
        assert not t.is_alive()

    assert len(clients) == 3
    assert len({id(c) for c in clients}) == 3, "不同线程不能共用客户端"
    assert all(c is not rds_mgr.rds for c in clients)


def test_generation_bump_forces_rebuild(isolated_env):
    """Redis 重连后递增代次：**同一线程内**下次取用要重建，丢掉失效连接池。

    必须在同一个线程里比较 —— 换线程本来就会新建实例，那样测不出代次的作用。
    """
    def scenario():
        first = rds_mgr._current_client()
        rds_mgr._client_generation += 1
        second = rds_mgr._current_client()
        return first, second

    first, second = _run_in_thread(scenario)

    assert second is not first, "代次变化后应重建客户端"


def test_worker_redis_writes_reach_the_same_store(isolated_env):
    """隔离的是连接，不是数据：线程写入仍要能被主线程读到。"""
    def write():
        rds_mgr.set('thread-key', 'from-worker')

    _run_in_thread(write)

    assert rds_mgr.get_str('thread-key') == 'from-worker'
