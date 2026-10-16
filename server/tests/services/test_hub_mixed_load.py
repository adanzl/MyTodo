"""混合负载下的 hub 响应性（验收性回归）。

对应验收目标：模拟 Redis 延迟，同时发文字、语音、取消与状态查询，并让流长时间
等待，确认轻量请求（/health 一类）仍能及时响应。

为什么需要它：单点回归只能证明「某一处不再阻塞」，而真实故障是**多处叠加**的
结果。这里并发跑完整链路，观察最大心跳间隔与轻量请求延迟——任一处残留原生阻塞，
两个指标都会立刻恶化。

探针在独立子进程里跑：`monkey.patch_all` 是进程级行为，且这类缺陷是「进程卡住」
而非抛异常，必须靠外部超时判定。
"""

from tests.services._probe_helper import probe_value, run_probe_resilient
from tests.services._mixed_load_probe import MIXED_LOAD_PROBE


def _run(tmp_path):
    proc = run_probe_resilient(MIXED_LOAD_PROBE, tmp_path, timeout=180)
    assert proc.returncode == 0, f'混合负载探针失败:\n{proc.stdout}\n{proc.stderr}'
    assert 'DONE' in proc.stdout, f'探针未跑完:\n{proc.stdout}\n{proc.stderr}'
    return proc


def _num(proc, key):
    raw = probe_value(proc.stdout, key)
    assert raw is not None, f'探针未产出 {key}:\n{proc.stdout}'
    return float(raw)


def test_hub_stays_responsive_under_mixed_load(tmp_path):
    """混合负载期间 hub 必须始终能被调度（最大心跳间隔要小）。"""
    proc = _run(tmp_path)

    gap = _num(proc, 'MAX_GAP')
    base = _num(proc, 'BASE_GAP')
    assert base < 0.1, f'基线本身异常（{base:.3f}s），环境负载过高，无法判定'
    assert gap <= 0.35, (
        f'混合负载下 hub 被占住了约 {gap:.2f}s（基线 {base:.3f}s）：'
        f'说明仍有原生阻塞等待。\n{proc.stdout}'
    )
    assert base < 0.1


def test_light_request_latency_stays_low(tmp_path):
    """轻量请求的延迟必须保持在毫秒级 —— 这是用户可感知的指标。"""
    proc = _run(tmp_path)

    p95 = _num(proc, 'LIGHT_P95')
    worst = _num(proc, 'LIGHT_MAX')
    assert p95 <= 0.1, f'轻量请求 P95 延迟 {p95:.3f}s 偏高：\n{proc.stdout}'
    assert worst <= 0.5, f'轻量请求最坏延迟 {worst:.3f}s 偏高：\n{proc.stdout}'


def test_all_mixed_workloads_complete_correctly(tmp_path):
    """负载必须真的跑完且结果正确 —— 不能为了「响应快」而丢任务。"""
    proc = _run(tmp_path)

    assert _num(proc, 'STREAMS_DONE') >= 12, f'长流未跑完:\n{proc.stdout}'
    assert _num(proc, 'STATUS_OK') >= 6, f'状态查询未完成:\n{proc.stdout}'
    assert probe_value(proc.stdout, 'STATUS_ERR') == 'None', (
        f'状态转换出错（可能丢更新）:\n{proc.stdout}'
    )
    assert _num(proc, 'ASR_ON_HUB') >= 50, f'ASR 结果交付不足:\n{proc.stdout}'
    assert _num(proc, 'CANCELS') >= 5, f'取消未执行:\n{proc.stdout}'
    assert _num(proc, 'ORDERED') == 60, f'保序通道有任务丢失:\n{proc.stdout}'


def test_asr_callbacks_all_run_on_hub_thread(tmp_path):
    """从真实线程交回的 ASR 回调必须全部落在 hub 线程上。"""
    proc = _run(tmp_path)

    assert _num(proc, 'ASR_OFF_HUB') == 0, (
        f'有 ASR 回调没有回到 hub 线程执行：\n{proc.stdout}'
    )


def test_ordered_channel_preserves_order_under_load(tmp_path):
    """混合负载下，保序通道仍要严格保持顺序（TTS 音频分片依赖它）。"""
    proc = _run(tmp_path)

    assert probe_value(proc.stdout, 'ORDERED_IN_ORDER') == 'True', (
        f'保序通道在负载下出现乱序：\n{proc.stdout}'
    )
