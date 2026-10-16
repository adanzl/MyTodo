"""跨线程唤醒能力探针（#2 的对照）。

背景：把发送调度到连接所属线程时，必须**唤醒**那个线程的循环。gevent 有两个接口：

    def run_callback(self, func, *args):
        cb = callback(func, args)
        self._callbacks.append(cb)   # Relying on the GIL for this to be threadsafe
        self._setup_for_run_callback()   # ← 只启动回调定时器 + uv_ref
        return cb

    def run_callback_threadsafe(self, func, *args):
        cb = self.run_callback(func, *args)
        self._threadsafe_async.send()    # ← 发 async watcher，真正唤醒 epoll
        return cb

`_setup_for_run_callback` 不会唤醒正空闲在 `epoll_wait` 的循环，所以从别的线程用
`run_callback` 投递时，回调要等到循环因**其它**事件醒来才会执行 —— 对空闲连接
就是不执行。这正是「投递超时」的成因。

探针构造一个真实线程持有的 gevent 连接并让它空闲等待（模拟 `run_forever` 的
select），然后用生产代码 `run_on_owner` 投递，测量多久被执行：

- `threadsafe`（修复后）：应立即执行
- `plain`（把唤醒换成 run_callback，即修复前）：应超时不被执行 —— 这条即反证
"""

import os
import subprocess
import sys

PROBE_SOURCE = r'''
import sys
import threading
import time
from types import SimpleNamespace

from gevent import monkey

monkey.patch_all(subprocess=True, thread=False, queue=False)

import socket  # noqa: E402

from gevent import sleep  # noqa: E402

MODE = sys.argv[1] if len(sys.argv) > 1 else 'threadsafe'

import core.tools.ws_owner_send as wos  # noqa: E402

wos.install()          # 把当前（主）线程记为 hub 线程
print(f"INSTALLED={wos.is_installed()}", flush=True)

STATE = {}


def owner_thread():
    """模拟 run_forever：在本线程建立连接，然后空闲等待数据。"""
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    conn = socket.socket()
    conn.connect(srv.getsockname())
    STATE["conn"] = conn
    STATE["srv"] = srv
    STATE["hub"] = conn.hub
    STATE["tid"] = threading.get_ident()
    STATE["ready"] = True
    # 空闲等待（永不返回）：循环就此睡在 epoll 上
    try:
        while True:
            if not conn.recv(1):
                break
    except Exception:
        pass


threading.Thread(target=owner_thread, daemon=True).start()
deadline = time.monotonic() + 10
while not STATE.get("ready") and time.monotonic() < deadline:
    time.sleep(0.01)
assert STATE.get("ready"), "owner 线程未就绪"
sleep(0.3)              # 让它真正进入空闲等待

if MODE == "plain":
    # 模拟修复前：把唤醒换成不会叫醒空闲循环的 run_callback
    loop = STATE["hub"].loop
    loop.run_callback_threadsafe = loop.run_callback

# 构造 app，使 _owner_hub 能找到该连接的 hub（生产里 app.sock.sock 就是它）
app = SimpleNamespace(sock=SimpleNamespace(sock=STATE["conn"]))

ran = []
ran_tid = []


def action():
    ran.append(time.monotonic())
    ran_tid.append(threading.get_ident())


t0 = time.monotonic()
wos.run_on_owner(app, action)          # 从 hub 线程投递：不等待，自己观察

LIMIT = 2.0
while not ran and time.monotonic() - t0 < LIMIT:
    sleep(0.01)

if ran:
    print(f"LATENCY={ran[0] - t0:.3f}")
    print(f"RAN_ON_OWNER={ran_tid[0] == STATE['tid']}")
else:
    print("LATENCY=-1")               # 超时未被唤醒执行
    print("RAN_ON_OWNER=False")
print("DONE", flush=True)
'''


def run_probe(tmp_path, mode: str, *, timeout: int = 90) -> dict:
    """在独立子进程里跑探针（monkey patch 是进程级的，必须隔离）。"""
    server_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = os.path.join(str(tmp_path), f'_wake_probe_{mode}.py')
    with open(script, 'w', encoding='utf-8') as fh:
        fh.write(PROBE_SOURCE)

    env = dict(os.environ)
    env.setdefault('PYTHONIOENCODING', 'utf-8')
    env['PYTHONPATH'] = os.pathsep.join([server_root, env.get('PYTHONPATH', '')]).rstrip(os.pathsep)
    env['RDS_LOCAL_FILE'] = os.path.join(str(tmp_path), 'rds_probe.json')
    # 显式关掉 Redis：省掉每次 ~5 秒连接超时，并让结果不依赖本机是否跑着 Redis
    env['REDIS_ENABLED'] = 'false'

    try:
        proc = subprocess.run(
            [sys.executable, script, mode],
            cwd=server_root, env=env,
            capture_output=True, text=True, errors='replace', timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise AssertionError(f'唤醒探针（{mode}）超时，可能挂死')

    assert proc.returncode == 0, f'唤醒探针（{mode}）失败:\n{proc.stdout}\n{proc.stderr}'
    assert 'DONE' in proc.stdout, f'唤醒探针（{mode}）未跑完:\n{proc.stdout}'

    result = {'_output': proc.stdout}
    for line in proc.stdout.splitlines():
        if '=' in line:
            key, _, value = line.partition('=')
            if key.isupper():
                result[key] = value.strip()
    return result
