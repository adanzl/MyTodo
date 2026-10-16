"""WebSocket 发送的线程归属（跨线程发送）回归测试。

故障背景（2026-10-16 停摆的成因之一）：

连接由 `run_forever` 线程建立，而业务代码从别的线程（hub 或 SDK 工作线程）
`ws.send()`。gevent 的 socket 绑定在创建它的线程的 hub 上，跨线程使用会抛

    Cannot switch to a different thread

它**不是每次都报错**——只有当发送需要等待（对端不收、发送缓冲写满）时才触发，
于是表现为偶发失败 + 连接状态被写坏，严重时把 hub 卡死。当日日志里刷了 54 次
该错误，随后 10 分钟零输出。

修复见 `core/tools/ws_owner_send.py`：把发送调度到 socket 所属线程执行。

这些用例跑**两个独立子进程**（服务端普通 Python + 客户端 gevent patch），
因为 `monkey.patch_all` 是进程级行为，同进程内无法既 patch 又不 patch。
`unfixed` 一条本身即反证：它确认故障真实存在、且本用例有检测能力。
"""

import os
import subprocess
import sys
import time

import pytest

from tests.services._ws_owner_probe_helper import write_scripts

_SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _env():
    env = dict(os.environ)
    env.setdefault('PYTHONIOENCODING', 'utf-8')
    env['PYTHONPATH'] = os.pathsep.join([_SERVER_ROOT, env.get('PYTHONPATH', '')]).rstrip(os.pathsep)
    return env


def _run_client(server_script, client_script, tmp_dir, mode):
    """起 TLS 服务端（独立进程）→ 跑客户端探针 → 返回解析后的结果。"""
    port_file = os.path.join(str(tmp_dir), f'ws_port_{mode}.txt')
    if os.path.exists(port_file):
        os.remove(port_file)

    server = subprocess.Popen(
        [sys.executable, server_script, port_file],
        cwd=_SERVER_ROOT, env=_env(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors='replace',
    )
    try:
        # 等服务端写出端口（证书生成需要一两秒）
        deadline = time.monotonic() + 30
        while not os.path.exists(port_file) and time.monotonic() < deadline:
            if server.poll() is not None:
                out = server.stdout.read() if server.stdout else ''
                raise AssertionError(f'服务端提前退出:\n{out}')
            time.sleep(0.1)
        assert os.path.exists(port_file), '服务端未写出端口文件'

        try:
            proc = subprocess.run(
                [sys.executable, client_script, port_file, mode],
                cwd=_SERVER_ROOT, env=_env(),
                capture_output=True, text=True, errors='replace', timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise AssertionError(f'客户端探针（{mode}）超时，可能挂死')
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    assert proc.returncode == 0, f'客户端探针（{mode}）失败:\n{proc.stdout}\n{proc.stderr}'
    assert 'DONE' in proc.stdout, f'客户端探针（{mode}）未跑完:\n{proc.stdout}\n{proc.stderr}'

    result = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            key, _, value = line.partition('=')
            if key.isupper():
                result[key] = value.strip()
    result['_output'] = proc.stdout
    return result


@pytest.fixture(scope='module')
def probe_results(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('ws_owner_send')
    server_script, client_script = write_scripts(tmp)
    return {
        mode: _run_client(server_script, client_script, tmp, mode)
        for mode in ('unfixed', 'fixed-worker', 'fixed-hub')
    }


def test_unfixed_reproduces_cross_thread_error(probe_results):
    """反证：不接管发送时，跨线程发送必须复现 `Cannot switch to a different thread`。

    这条守住的是「本用例确实有检测能力」：若哪天不再复现（例如 monkey.patch_all
    参数被改、或 websocket-client 换了底层实现），说明前提变了，需要重新评估。
    """
    r = probe_results['unfixed']
    assert r.get('OPENED') == 'True', f"连接未建立:\n{r['_output']}"
    err = (r.get('ERR') or '') + (r.get('ON_ERROR') or '')
    assert 'Cannot switch to a different thread' in err, (
        f"预期复现跨线程错误，实际 ERR={r.get('ERR')!r} ON_ERROR={r.get('ON_ERROR')!r}\n{r['_output']}"
    )


def test_fixed_from_worker_thread_has_no_cross_thread_error(probe_results):
    """接管后，从普通工作线程发送不得再抛跨线程错误（TTS SDK 的场景）。

    这条路径是**阻塞**的：真实线程需要拿到错误、并保证发送顺序。
    """
    r = probe_results['fixed-worker']
    assert r.get('INSTALLED') == 'True', '发送接管未安装'
    assert r.get('OPENED') == 'True', f"连接未建立:\n{r['_output']}"
    combined = (r.get('ERR') or '') + (r.get('ON_ERROR') or '')
    assert 'Cannot switch to a different thread' not in combined, (
        f"仍有跨线程错误: {combined!r}\n{r['_output']}"
    )
    assert (r.get('ERR') or 'None') == 'None', f"不应报错: ERR={r.get('ERR')!r}\n{r['_output']}"


def test_fixed_from_hub_thread_does_not_block(probe_results):
    """从 hub 线程发送必须**立即返回**（ASR 音频分片的场景）。

    hub 绝不能被阻塞：那正是要修的问题本身。因此这条路径只入队、不等待。
    """
    r = probe_results['fixed-hub']
    assert r.get('OPENED') == 'True', f"连接未建立:\n{r['_output']}"
    elapsed = float(r.get('SEND_CALL_ELAPSED', '999'))
    assert elapsed < 1.0, (
        f"hub 线程发送耗时 {elapsed:.2f}s —— 应当只入队后立即返回\n{r['_output']}"
    )
    # 任务确实排进了队列（说明没有退化成「什么都不做」）
    assert int(r.get('QUEUED', '0')) > 0, '发送没有被排队，可能根本没有执行'
    # 所属线程会异步消费，队列应随之下降
    assert int(r.get('QUEUE_AFTER', '9999')) < int(r.get('QUEUED', '0')), (
        f"队列没有被所属线程消费: QUEUED={r.get('QUEUED')} "
        f"QUEUE_AFTER={r.get('QUEUE_AFTER')}\n{r['_output']}"
    )


def test_install_is_idempotent_and_wraps_all_send_methods():
    """安装必须幂等，并接管 WebSocketApp 的全部发送方法。"""
    from websocket import WebSocketApp

    from core.tools import ws_owner_send

    assert ws_owner_send.install() is True
    assert ws_owner_send.install() is True
    assert ws_owner_send.is_installed() is True

    for name in ('send', 'send_bytes', 'send_text'):
        wrapped = getattr(WebSocketApp, name)
        original = ws_owner_send._original_methods.get(name)
        assert original is not None, f'{name} 未被接管'
        assert wrapped is not original, f'{name} 仍指向原实现，跨线程发送会失败'


def test_original_methods_are_recoverable():
    """必须能取回原实现 —— 测试需要用「还原」来构造反证。"""
    from core.tools import ws_owner_send

    ws_owner_send.install()
    for name in ('send', 'send_bytes', 'send_text'):
        assert callable(ws_owner_send._original_methods[name])
