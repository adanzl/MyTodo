"""混合负载下的 hub 响应性验证（子进程探针源码）。

对应「模拟 Redis 延迟，同时发文字、语音、取消和状态查询；让流长时间等待，
确认轻量请求仍能及时响应」这一验收目标。

与单点回归用例的区别：这里**并发**跑完整条链路，观察的是它们叠加之后 hub 是否
仍能被调度。任一环节残留原生阻塞等待，最大心跳间隔都会明显拉长。

探针内模拟的负载：
1. 长流：多条 Dify 流式回答同时进行（协作式等待数十秒）；
2. 状态查询：持续读写 chat 请求共享存储，并给 Redis 调用注入延迟；
3. 语音：从**真实线程**反复把 ASR 结果交回 hub；
4. 取消：并发触发请求取消与 TTS 取消；
5. 轻量探测：一个「像 /health 那样」的极短任务，测量它的响应延迟。

判据：
- 最大心跳间隔要小（hub 没有被谁长时间占住）；
- 轻量任务的最大响应延迟要小（这是用户可感知的指标）；
- 业务结果都要正确（长流跑完、状态转换不丢、取消生效、ASR 都回到 hub 线程）。
"""

MIXED_LOAD_PROBE = r'''
from gevent import monkey

monkey.patch_all(subprocess=True, thread=False, queue=False)

import os
import queue
import sys
import threading
import time

from gevent import sleep, spawn

# ---------- 心跳「证人」：hub 被占住多久，间隔就有多长 ----------
witness = []
stop = {'v': False}


def witness_loop():
    while not stop['v']:
        witness.append(time.monotonic())
        sleep(0.01)


spawn(witness_loop)
sleep(0.3)


def max_gap(t0, t1):
    ticks = [t for t in witness if t0 <= t <= t1]
    if len(ticks) < 2:
        return t1 - t0
    return max(b - a for a, b in zip(ticks, ticks[1:]))


now = time.monotonic()
BASE = max_gap(now - 1.0, now)
print('BASE_GAP=%.4f' % BASE, flush=True)

# ---------- 让 Redis 变慢：模拟网络延迟 ----------
import core.chat.chat_request_store as crs
import core.db.rds_mgr as rds

_orig_setex = rds.setex
_orig_get_str = rds.get_str
_orig_eval = getattr(rds, 'eval_lua', None)

REDIS_DELAY = 0.02


def slow_setex(key, ttl, value):
    sleep(REDIS_DELAY)
    return _orig_setex(key, ttl, value)


def slow_get_str(key):
    sleep(REDIS_DELAY)
    return _orig_get_str(key)


rds.setex = slow_setex
rds.get_str = slow_get_str
if _orig_eval is not None:
    rds.eval_lua = lambda *a, **k: (sleep(REDIS_DELAY), _orig_eval(*a, **k))[1]
crs.rds_mgr = rds

# ---------- 1) 长流：多条回答同时进行 ----------
STREAMS = 12
STREAM_STEPS = 30
stream_done = {'n': 0}


def stream_task(idx):
    # 模拟 AI 流式读取：分片之间协作式等待
    for _ in range(STREAM_STEPS):
        sleep(0.02)
    stream_done['n'] += 1


# ---------- 2) 状态查询：持续读写请求记录 ----------
status_ok = {'n': 0}
status_err = []


def status_task(idx):
    rid = 'rid-%d' % idx
    try:
        for i in range(20):
            crs.set_phase(rid, 'user-1', 'streaming')
            rec = crs.get_record(rid, 'user-1')
            if rec is None:
                status_err.append('record missing at %d' % i)
                return
            sleep(0.005)
        status_ok['n'] += 1
    except BaseException as e:  # noqa: BLE001
        status_err.append('%s: %s' % (type(e).__name__, str(e)))


# ---------- 3) 语音：真实线程把 ASR 结果交回 hub ----------
from core.tools.hub_dispatch import post_to_hub, post_to_hub_ordered

asr_seen = {'n': 0, 'off_hub': 0}
hub_ident = threading.get_ident()
ORDER = []


def _asr_handler(i):
    if threading.get_ident() != hub_ident:
        asr_seen['off_hub'] += 1
    asr_seen['n'] += 1


def asr_feeder():
    for i in range(30):
        post_to_hub(lambda i=i: _asr_handler(i))
        sleep(0.01)


def asr_inline():
    """模拟「回调本来就在 hub 上」的情形（on_asr_result 的路径）。"""
    for i in range(20):
        _asr_handler(i)
        sleep(0.01)


# ---------- 4) 取消：并发触发 ----------
from core.tts.tts_client import TTSClient

cancel_seen = {'n': 0}


def cancel_task(idx):
    tts = TTSClient()
    tts.streaming_cancel()          # 无连接时也应安全返回
    cancel_seen['n'] += 1


# ---------- 5) 轻量探测：等价于 /health 那种极短请求 ----------
probe_latency = []


def light_probe():
    while not stop['v']:
        t0 = time.monotonic()
        sleep(0)                     # 只做一次让出，测「能不能马上被调度」
        probe_latency.append(time.monotonic() - t0)
        sleep(0.02)


# ---------- 同时开跑 ----------
# 必须先启动 hub 消费循环（生产里由 main.py 调用）。不启动的话，
# `post_to_hub` / `post_to_hub_ordered` 投递的任务没有消费者，会一直堆在队列里，
# 探针只能干等到超时——既浪费时间又测不到真实行为。
from core.tools.hub_dispatch import start_hub_drain

start_hub_drain()
sleep(0.1)          # 让消费循环跑起来

t0 = time.monotonic()

for i in range(STREAMS):
    spawn(stream_task, i)
for i in range(6):
    spawn(status_task, i)
for i in range(5):
    spawn(cancel_task, i)

spawn(light_probe)
spawn(asr_feeder)
spawn(asr_inline)

# 有序通道也要一起压：模拟 TTS 音频分片 + 完成事件
ordered_seen = []


def ordered_feeder():
    for i in range(60):
        post_to_hub_ordered(lambda i=i: ordered_seen.append(i))
        sleep(0.005)


spawn(ordered_feeder)

# 等所有负载跑完（正常十几秒内就该齐；超时说明有环节没跑起来）
deadline = 25.0
while time.monotonic() - t0 < deadline:
    if (stream_done['n'] >= STREAMS and status_ok['n'] >= 6
            and len(ordered_seen) >= 60 and asr_seen['n'] >= 50
            and cancel_seen['n'] >= 5):
        break
    sleep(0.05)

t1 = time.monotonic()
sleep(0.5)          # 留出余量让残余回调跑完
stop['v'] = True

# 明确报告「是否真的跑齐了」：否则超时只会表现为数字偏小，
# 看不出是负载没跑起来还是 hub 慢。
print('CONVERGED=%s' % (
    stream_done['n'] >= STREAMS and status_ok['n'] >= 6
    and len(ordered_seen) >= 60 and asr_seen['n'] >= 50
    and cancel_seen['n'] >= 5))

print('ELAPSED=%.2f' % (t1 - t0))
print('MAX_GAP=%.4f' % max_gap(t0, t1))
print('STREAMS_DONE=%d' % stream_done['n'])
print('STATUS_OK=%d' % status_ok['n'])
print('STATUS_ERR=%s' % ('|'.join(status_err[:2]) if status_err else 'None'))
print('ASR_ON_HUB=%d' % asr_seen['n'])
print('ASR_OFF_HUB=%d' % asr_seen['off_hub'])
print('ORDERED=%d' % len(ordered_seen))
print('ORDERED_IN_ORDER=%s' % ('True' if ordered_seen == list(range(len(ordered_seen))) else 'False'))
print('CANCELS=%d' % cancel_seen['n'])
if probe_latency:
    lat = sorted(probe_latency)
    print('LIGHT_P95=%.4f' % lat[int(len(lat) * 0.95) - 1])
    print('LIGHT_MAX=%.4f' % lat[-1])
print('DONE', flush=True)

# 必须硬退出：`start_hub_drain()` 起的消费循环是**无限 greenlet**，主 greenlet
# 结束后 gevent 的 hub 会等待所有 greenlet 结束，于是进程永不退出 —— 输出都打印
# 完了，subprocess 仍会一直等到超时（这正是本探针「卡住」的原因）。
sys.stdout.flush()
os._exit(0)
'''
