"""混合负载下的 hub 响应性（验收性回归）。

对应验收目标：模拟 Redis 延迟，同时发文字、语音、取消与状态查询，并让流长时间
等待，确认轻量请求（/health 一类）仍能及时响应。

为什么需要它：单点回归只能证明「某一处不再阻塞」，而真实故障是**多处叠加**的
结果。这里并发跑完整链路，观察最大心跳间隔与轻量请求延迟——任一处残留原生阻塞，
两个指标都会立刻恶化。

探针在独立子进程里跑：`monkey.patch_all` 是进程级行为，且这类缺陷是「进程卡住」
而非抛异常，必须靠外部超时判定。

**探针只跑一次**（模块级 fixture）：它模拟的是持续负载，单次结果即可支撑下面所有
断言；若每个用例各跑一次，整个文件的耗时会成倍增长（曾因此让全量测试看起来像卡住）。
"""

import pytest

from tests.services._mixed_load_probe import MIXED_LOAD_PROBE
from tests.services._probe_helper import probe_value, run_probe_resilient


@pytest.fixture(scope='module')
def load_result(tmp_path_factory):
    """跑一次混合负载探针，所有用例共享结果。"""
    tmp = tmp_path_factory.mktemp('mixed_load')
    proc = run_probe_resilient(MIXED_LOAD_PROBE, tmp, timeout=120)
    assert proc.returncode == 0, f'混合负载探针失败:\n{proc.stdout}\n{proc.stderr}'
    assert 'DONE' in proc.stdout, f'探针未跑完:\n{proc.stdout}\n{proc.stderr}'
    return proc


def _num(proc, key):
    raw = probe_value(proc.stdout, key)
    assert raw is not None, f'探针未产出 {key}:\n{proc.stdout}'
    return float(raw)


def test_mixed_load_converges(load_result):
    """先确认负载真的跑齐了。

    否则后面几条断言可能因为「负载根本没跑起来」而给出误导性结论。
    """
    assert probe_value(load_result.stdout, 'CONVERGED') == 'True', (
        f'混合负载未在时限内跑齐（有环节没启动或被卡住）:\n{load_result.stdout}'
    )


def test_hub_stays_responsive_under_mixed_load(load_result):
    """混合负载期间 hub 必须始终能被调度（最大心跳间隔要小）。"""
    gap = _num(load_result, 'MAX_GAP')
    base = _num(load_result, 'BASE_GAP')
    assert base < 0.1, f'基线本身异常（{base:.3f}s），环境负载过高，无法判定'
    assert gap <= 0.35, (
        f'混合负载下 hub 被占住了约 {gap:.2f}s（基线 {base:.3f}s）：'
        f'说明仍有原生阻塞等待。\n{load_result.stdout}'
    )


def test_light_request_latency_stays_low(load_result):
    """轻量请求的延迟必须保持在毫秒级 —— 这是用户可感知的指标。"""
    p95 = _num(load_result, 'LIGHT_P95')
    worst = _num(load_result, 'LIGHT_MAX')
    assert p95 <= 0.1, f'轻量请求 P95 延迟 {p95:.3f}s 偏高：\n{load_result.stdout}'
    assert worst <= 0.5, f'轻量请求最坏延迟 {worst:.3f}s 偏高：\n{load_result.stdout}'


def test_all_mixed_workloads_complete_correctly(load_result):
    """负载必须真的跑完且结果正确 —— 不能为了「响应快」而丢任务。"""
    assert _num(load_result, 'STREAMS_DONE') >= 12, f'长流未跑完:\n{load_result.stdout}'
    assert _num(load_result, 'STATUS_OK') >= 6, f'状态查询未完成:\n{load_result.stdout}'
    assert probe_value(load_result.stdout, 'STATUS_ERR') == 'None', (
        f'状态转换出错（可能丢更新）:\n{load_result.stdout}'
    )
    assert _num(load_result, 'ASR_ON_HUB') >= 50, f'ASR 结果交付不足:\n{load_result.stdout}'
    assert _num(load_result, 'CANCELS') >= 5, f'取消未执行:\n{load_result.stdout}'
    assert _num(load_result, 'ORDERED') == 60, f'保序通道有任务丢失:\n{load_result.stdout}'


def test_asr_callbacks_all_run_on_hub_thread(load_result):
    """从真实线程交回的 ASR 回调必须全部落在 hub 线程上。"""
    assert _num(load_result, 'ASR_OFF_HUB') == 0, (
        f'有 ASR 回调没有回到 hub 线程执行：\n{load_result.stdout}'
    )


def test_ordered_channel_preserves_order_under_load(load_result):
    """混合负载下，保序通道仍要严格保持顺序（TTS 音频分片依赖它）。"""
    assert probe_value(load_result.stdout, 'ORDERED_IN_ORDER') == 'True', (
        f'保序通道在负载下出现乱序：\n{load_result.stdout}'
    )
