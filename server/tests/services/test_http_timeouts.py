"""上游 HTTP 调用的 `timeout=` 回归测试。

背景：本服务 `monkey.patch_all()` + `async_mode='gevent'`，所有 HTTP 请求都跑在同一个
hub 线程上，而 `requests` 的默认行为是**无限等待**：上游不回包（或连接半开）时该调用
永远不返回，用户界面一直停在「生成中」，问题只能靠重启解决。

所以这里逐个「掐住」上游调用点，断言 timeout 真的传下去了。这些用例是**反证式**的：
把被测代码里的 `timeout=` 删掉，对应用例必然失败。

另外区分两类调用：
- 非流式 JSON 接口：连接超时要短（快速失败），读超时够单次响应即可；
- 流式（SSE）：读超时是「两个 chunk 之间的最大间隔」，不能用小值，否则长回答被误杀。
"""

import base64
from unittest.mock import MagicMock

import core.ai.ai_file as ai_file
import core.ai.ai_local as ai_local
import core.ai.ai_mgr as ai_mgr
import core.tts.tts_doubao as tts_doubao

# 建连超时上限：本地/内网上游正常 <1s，超过这个数说明取值不合理。
_MAX_CONNECT_TIMEOUT = 10


class _FakeResponse:
    """最小可用的 requests 响应替身（支持 with / raise_for_status / json）。"""

    def __init__(self, payload=None):
        self._payload = payload if payload is not None else {}
        self.status_code = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload

    @property
    def text(self):
        return ""


class _FakeStreamResponse(_FakeResponse):
    """流式替身：iter_lines 直接结束（不触发重试逻辑）。"""

    def iter_lines(self):
        return iter([])


def _timeout_pair(timeout):
    """把传给 requests 的 timeout 归一成 (连接, 读)。

    requests 允许单个数字（连接与读共用）或 (连接, 读) 二元组。
    """
    assert timeout, "requests 调用缺少 timeout，上游不返回时会永久悬挂"
    if isinstance(timeout, (tuple, list)):
        assert len(timeout) == 2, f"timeout 元组应该是 (连接, 读)：{timeout!r}"
        return timeout[0], timeout[1]
    return timeout, timeout


def _assert_short_connect(timeout):
    """连接超时必须是「短值」，否则上游不可达时要等很久才失败。"""
    connect, _read = _timeout_pair(timeout)
    assert connect <= _MAX_CONNECT_TIMEOUT, f"连接超时过长：{connect}"


# ---------------- 豆包 / 火山方舟 ----------------

def test_doubao_chat_completion_passes_timeout(monkeypatch):
    """core/ai/ai_mgr.py 的 Ark Chat Completions 必须带超时。"""
    seen: dict = {}

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return _FakeResponse({"choices": []})

    monkeypatch.setattr(ai_mgr.requests, "post", fake_post)

    result = ai_mgr.call_doubao_api("你好")

    assert result == {"choices": []}
    assert "chat/completions" in seen["url"]
    _assert_short_connect(seen.get("timeout"))
    _connect, read = _timeout_pair(seen.get("timeout"))
    # 非流式：整段回答生成完才回包，读超时要足够宽容
    assert read >= 30, f"读超时过短，长回答会被掐断：{read}"


def test_doubao_tts_passes_timeout(monkeypatch):
    """core/tts/tts_doubao.py 的火山 TTS 必须带超时。"""
    seen: dict = {}
    audio = base64.b64encode(b"mp3-bytes").decode()

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return _FakeResponse({"data": audio})

    monkeypatch.setattr(tts_doubao.requests, "post", fake_post)

    assert tts_doubao.gen_tts("你好", "voice-x") == b"mp3-bytes"
    _assert_short_connect(seen.get("timeout"))
    _connect, read = _timeout_pair(seen.get("timeout"))
    # TTS 一次性返回整段音频，耗时随文本长度增长，读超时要留足余量
    assert read >= 60, f"读超时过短，长文本合成会被掐断：{read}"


# ---------------- Dify（core/ai/ai_local.py） ----------------

def test_stream_chat_uses_short_connect_plus_long_read_timeout(monkeypatch):
    """流式 SSE 对话：必须是「短建连 + 长读」，不能拿小读超时误杀长回答。"""
    seen: dict = {}

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return _FakeStreamResponse()

    monkeypatch.setattr(ai_local.requests, "post", fake_post)

    ai = ai_local.AILocal(lambda *a: None, lambda *a: None)
    ai.stream_msg("hi", client_request_id="rid-timeout")

    assert seen.get("stream") is True, "本用例针对流式请求"
    _assert_short_connect(seen.get("timeout"))
    _connect, read = _timeout_pair(seen.get("timeout"))
    assert read >= 60, (
        f"流式读超时是「两个 chunk 之间的最大间隔」，{read}s 太短会把正常长回答误杀"
    )


def test_stream_chat_read_timeout_can_be_overridden(monkeypatch):
    """调用方显式传的读超时仍然生效（连接超时保持短值）。"""
    seen: dict = {}

    def fake_post(url, **kwargs):
        seen.update(kwargs)
        return _FakeStreamResponse()

    monkeypatch.setattr(ai_local.requests, "post", fake_post)

    ai = ai_local.AILocal(lambda *a: None, lambda *a: None)
    ai.stream_msg("hi", timeout=90, client_request_id="rid-override")

    _assert_short_connect(seen.get("timeout"))
    assert _timeout_pair(seen.get("timeout")) == (ai_local.CONNECT_TIMEOUT, 90)


def test_get_chat_messages_passes_timeout(monkeypatch):
    seen: dict = {}

    def fake_get(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return _FakeResponse({"data": []})

    monkeypatch.setattr(ai_local.requests, "get", fake_get)

    assert ai_local.AILocal.get_chat_messages("conv-1", 20, "leo") == {"data": []}
    _assert_short_connect(seen.get("timeout"))
    assert _timeout_pair(seen.get("timeout"))[1] >= 30


def test_get_conversations_passes_timeout(monkeypatch):
    seen: dict = {}

    def fake_get(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return _FakeResponse({"data": []})

    monkeypatch.setattr(ai_local.requests, "get", fake_get)

    assert ai_local.AILocal.get_conversations("leo") == {"data": []}
    _assert_short_connect(seen.get("timeout"))
    assert _timeout_pair(seen.get("timeout"))[1] >= 15


def test_stop_streaming_task_passes_timeout(monkeypatch):
    """取消流式任务（用户等结果时触发）不能悬挂。"""
    seen: dict = {}

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return _FakeResponse({})

    monkeypatch.setattr(ai_local.requests, "post", fake_post)

    ai = ai_local.AILocal(lambda *a: None, lambda *a: None)
    ai._post_stop_task("rid-1", "task-1")

    assert seen["url"].endswith("/chat-messages/task-1/stop")
    _assert_short_connect(seen.get("timeout"))
    assert _timeout_pair(seen.get("timeout"))[1] >= 15


# ---------------- Dify 图片链路（core/ai/ai_file.py） ----------------
#
# 这两个调用用的是单个数字（连接/读共用 `REQUEST_TIMEOUT`，见该模块注释），
# 所以这里只断言「有超时且有界」；改成 (连接, 读) 二元组属于另一件事。


def test_image_capability_probe_passes_timeout(monkeypatch):
    seen: dict = {}

    def fake_get(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return _FakeResponse({"file_upload": {"enabled": True}})

    monkeypatch.setattr(ai_file.requests, "get", fake_get)

    assert ai_file._fetch_capability("leo") == (True, 0)
    assert seen["url"].endswith("/parameters")
    assert seen.get("timeout"), "requests 调用缺少 timeout，Dify 不响应时会一直等"
    assert max(_timeout_pair(seen["timeout"])) <= 60


def test_image_upload_passes_timeout(monkeypatch, tmp_path):
    from core.ai import ai_file as _ai_file

    seen: dict = {}
    pic = tmp_path / "chat-1.png"
    pic.write_bytes(b"png-bytes")

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return _FakeResponse({"id": "file-id-1"})

    monkeypatch.setattr(_ai_file.requests, "post", fake_post)
    monkeypatch.setattr(_ai_file, "_read_pic_file", lambda name: (b"png-bytes", "image/png"))
    _ai_file._id_cache.clear()

    assert _ai_file.upload_image("chat-1.png", "leo") == "file-id-1"
    assert seen["url"].endswith("/files/upload")
    assert seen.get("timeout"), "requests 调用缺少 timeout，大图上传会一直挂着"
    assert max(_timeout_pair(seen["timeout"])) <= 60


# ---------------- 设备 Agent（core/device/agent.py） ----------------

def test_device_agent_request_passes_timeout(monkeypatch):
    """DeviceAgent 的 _request 也必须带超时（内网设备不在线时快速失败）。

    这里用的是单个数字（连接/读共用 `DEVICE_AGENT_TIMEOUT`），所以只断言「有超时且有界」，
    不断言建连必须很短——改成 (连接, 读) 二元组属于另一件事。
    """
    from core.device.agent import DeviceAgent

    seen: dict = {}

    def fake_request(method, url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return MagicMock(**{"raise_for_status.return_value": None, "json.return_value": {"code": 0}})

    monkeypatch.setattr("core.device.agent.requests.request", fake_request)

    result = DeviceAgent(address="127.0.0.1:8000").bluetooth_get_devices()

    assert result == {"code": 0}
    assert seen["url"].endswith("/bluetooth/devices")
    timeout = seen.get("timeout")
    assert timeout, "requests 调用缺少 timeout，设备不可达时会一直等"
    assert max(_timeout_pair(timeout)) <= 60
