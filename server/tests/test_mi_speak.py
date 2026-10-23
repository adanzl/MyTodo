"""小米文字播报（miot Play Text 通道）单元测试。

覆盖三件事：
- `Play Text` 的 aiid 必须按型号解析（各型号动作顺序不同，写死会错发动作）；
- 型号未在实测表里时，能从 miot-spec 解析并缓存；
- `speak()` 在通道失败时直接报错，不回退到 ubus 的 text_to_speech。
"""
import asyncio
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.device.mi_device as mi_device
from core.device.mi_device import MiDevice, _resolve_play_text_aiid


def _spec_with_actions(model: str,
                       actions: List[Tuple[int, str]],
                       siid: int = 5) -> Dict[str, Any]:
    """构造一个最小可用的 miot spec。"""
    return {
        "type": f"urn:miot-spec-v2:device:speaker:0000A015:{model}:2",
        "services": [{
            "iid": siid,
            "description": "Intelligent Speaker",
            "actions": [{
                "iid": aiid,
                "description": desc,
                "in": [1] if "Text" in desc else [],
            } for aiid, desc in actions],
            "properties": [{
                "iid": 1,
                "description": "Text Content",
                "format": "string",
            }],
        }],
    }


class _FakeService:
    """假的 MiIOService，只实现 speak 用到的三个方法。"""

    def __init__(self,
                 model: Optional[str] = "xiaomi.wifispeaker.l05c",
                 action_code: int = 0,
                 spec: Optional[Dict[str, Any]] = None) -> None:
        self.model = model
        self.action_code = action_code
        self.spec = spec
        self.actions: List[Tuple[str, List[int], List[Any]]] = []
        self.spec_queries: List[str] = []

    async def miot_get_props(self, did: str, iids: List[Tuple[int, int]]):
        assert iids == [mi_device.MIOT_PROP_DEVICE_MODEL]
        return [self.model]

    async def miot_spec(self, model: str, fmt: Optional[str] = None):
        self.spec_queries.append(model)
        if self.spec is None:
            raise RuntimeError("no spec")
        return self.spec

    async def miot_action(self, did: str, iid: List[int], args: List[Any]):
        self.actions.append((did, iid, args))
        return self.action_code


@pytest.fixture(autouse=True)
def _clean_aiid_cache(monkeypatch):
    """每个用例用干净的 aiid 缓存，避免用例之间互相污染。"""
    monkeypatch.setattr(mi_device, "MIOT_PLAY_TEXT_AIID", dict(
        mi_device.MIOT_PLAY_TEXT_AIID))
    yield


class _FakeSession:

    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def _run_coro(value):
    """跑协程；若已被 run_async 替身同步求值过则原样返回。"""
    if not asyncio.iscoroutine(value):
        return value
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(value)
    finally:
        loop.close()


def _fake_run_async(coro, timeout=None):
    """替身：直接在新事件循环里跑协程，等价于 run_async 的求值语义。"""
    return _run_coro(coro)


def _patch_speak_deps(monkeypatch, service: _FakeService) -> _FakeSession:
    """把 _login_xiaomiio 与 MiIOService 换成假实现。"""
    session = _FakeSession()

    async def fake_login(_self, force_refresh=False):
        return object(), session, ""

    monkeypatch.setattr(MiDevice, "_login_xiaomiio", fake_login)
    monkeypatch.setattr(mi_device, "MiIOService", lambda account: service)
    monkeypatch.setattr(mi_device, "run_async", _fake_run_async)
    return session


@pytest.mark.parametrize("model,expected_aiid", [
    ("xiaomi.wifispeaker.l05c", 3),
    ("xiaomi.wifispeaker.x08a", 1),
    ("xiaomi.wifispeaker.lx06", 1),
])
def test_speak_uses_model_specific_aiid(monkeypatch, model, expected_aiid):
    """同一段代码在不同型号上必须发出不同的 aiid。"""
    service = _FakeService(model=model)
    _patch_speak_deps(monkeypatch, service)

    code, msg = _run_coro(MiDevice(address="dev", did="did").speak("你好"))

    assert code == 0, msg
    assert msg == "播报成功"
    assert len(service.actions) == 1
    did, iid, args = service.actions[0]
    assert did == "did"
    assert iid == [mi_device.MIOT_INTELLIGENT_SPEAKER_SIID, expected_aiid]
    assert args == ["你好"]


def test_resolve_play_text_aiid_from_spec_and_cache(monkeypatch):
    """未实测的型号要回落到 spec 查询，并把结果缓存下来。"""
    spec = _spec_with_actions("xiaomi.wifispeaker.newone", [(1, "Wake Up"),
                                                            (2, "Play Text")])
    service = _FakeService(spec=spec)
    monkeypatch.setattr(mi_device, "MIOT_PLAY_TEXT_AIID", {})

    aiid = _run_coro(
        _resolve_play_text_aiid(service, "xiaomi.wifispeaker.newone"))
    assert aiid == 2
    assert mi_device.MIOT_PLAY_TEXT_AIID["xiaomi.wifispeaker.newone"] == 2

    # 第二次应命中缓存，不再查 spec
    again = _run_coro(
        _resolve_play_text_aiid(service, "xiaomi.wifispeaker.newone"))
    assert again == 2
    assert service.spec_queries == ["xiaomi.wifispeaker.newone"]


def test_resolve_play_text_aiid_without_action(monkeypatch):
    """spec 里没有 Play Text 动作时返回 None。"""
    spec = _spec_with_actions("xiaomi.wifispeaker.odd", [(1, "Wake Up")])
    service = _FakeService(spec=spec)
    monkeypatch.setattr(mi_device, "MIOT_PLAY_TEXT_AIID", {})

    assert _run_coro(
        _resolve_play_text_aiid(service,
                                "xiaomi.wifispeaker.odd")) is None


def test_speak_reports_error_when_action_fails(monkeypatch):
    """miot 返回非 0 时必须报错，不能假报成功。"""
    service = _FakeService(action_code=-704220025)
    _patch_speak_deps(monkeypatch, service)

    code, msg = _run_coro(MiDevice(address="dev", did="did").speak("你好"))

    assert code != 0
    assert "-704220025" in msg


def test_speak_never_falls_back_to_text_to_speech(monkeypatch):
    """失败路径不允许回退到 ubus text_to_speech。"""
    service = _FakeService(action_code=1)
    _patch_speak_deps(monkeypatch, service)

    called = []
    monkeypatch.setattr(mi_device, "MiNAService",
                        lambda account: called.append(account) or object())

    code, _msg = _run_coro(MiDevice(address="dev", did="did").speak("你好"))

    assert code != 0
    assert called == []


def test_speak_requires_text():
    code, msg = _run_coro(MiDevice(address="dev", did="did").speak("   "))
    assert code != 0
    assert msg == "text is required"


def test_speak_reports_login_failure(monkeypatch):
    """miot 通道拿不到凭据时给出登录相关错误。"""

    async def fake_login(_self, force_refresh=False):
        return None, None, "登录验证失败，请检查账号密码是否正确"

    monkeypatch.setattr(MiDevice, "_login_xiaomiio", fake_login)
    monkeypatch.setattr(mi_device, "run_async", _fake_run_async)

    code, msg = _run_coro(MiDevice(address="dev", did="did").speak("你好"))
    assert code != 0
    assert "登录验证失败" in msg


def test_login_reuses_cached_xiaomiio_token(monkeypatch):
    """token 文件里已有 xiaomiio 时必须直接复用，不能去重新登录。

    实测重新 `login("xiaomiio")` 会触发密码通道，返回 `securityStatus: 16`
    且缺 `nonce`，反而把原本可用的凭据搞坏。
    """
    calls: List[str] = []

    class _Acc:

        def __init__(self, token: Optional[Dict[str, Any]]) -> None:
            self.token = token

        async def login(self, sid: str) -> bool:
            calls.append(sid)
            return False

    fake_acc = _Acc({"userId": 1, "passToken": "x", "xiaomiio": ["a", "b"]})
    monkeypatch.setattr(MiDevice, "_create_account", lambda _self, _s: fake_acc)
    monkeypatch.setattr(mi_device, "ClientSession", _FakeSession)

    account, session, err = _run_coro(
        MiDevice(address="dev", did="did")._login_xiaomiio())

    assert err == ""
    assert account is fake_acc
    assert session is not None
    assert calls == [], "命中缓存时不应该发起任何登录"


def test_login_falls_back_to_micoapi_then_xiaomiio(monkeypatch):
    """缺 xiaomiio 时才走 micoapi 刷新 → 新实例登 xiaomiio 的慢路径。"""

    calls: List[str] = []

    class _Acc:

        def __init__(self, token: Dict[str, Any]) -> None:
            self.token = token

        async def login(self, sid: str) -> bool:
            calls.append(sid)
            if sid == "xiaomiio":
                self.token["xiaomiio"] = ["a", "b"]
            return True

    # 快路径拿到的 token 里没有 xiaomiio，慢路径才有
    accounts = [_Acc({"userId": 1, "passToken": "x"}), _Acc({"userId": 1}),
                _Acc({"userId": 1})]
    monkeypatch.setattr(MiDevice, "_create_account",
                        lambda _self, _s: accounts.pop(0))
    monkeypatch.setattr(mi_device, "ClientSession", _FakeSession)

    account, session, err = _run_coro(
        MiDevice(address="dev", did="did")._login_xiaomiio())

    assert err == ""
    assert account is not None
    assert session is not None
    assert calls == ["micoapi", "xiaomiio"]


def test_speak_reports_missing_model(monkeypatch):
    """拿不到设备型号时报错，不要瞎猜 aiid。"""
    service = _FakeService(model=None)
    _patch_speak_deps(monkeypatch, service)

    code, msg = _run_coro(MiDevice(address="dev", did="did").speak("你好"))

    assert code != 0
    assert "型号" in msg
    assert service.actions == []


def test_speak_retries_once_with_forced_refresh(monkeypatch):
    """缓存的 xiaomiio serviceToken 过期时，应强制刷新一次再重试。

    miot 请求拿到 `Login failed` 说明 serviceToken 失效；token 文件里的
    xiaomiio 需要重建，否则必须重启进程才能恢复。
    """
    attempts: List[bool] = []

    class _ExpiringService:

        def __init__(self) -> None:
            self.calls = 0

        async def miot_get_props(self, _did, _iids):
            self.calls += 1
            if self.calls == 1:
                raise Exception(
                    "Error https://api.io.mi.com/app/miotspec/prop/get: Login failed")
            return ["xiaomi.wifispeaker.l05c"]

        async def miot_spec(self, _model, _fmt=None):
            raise RuntimeError("should not be called")

        async def miot_action(self, _did, iid, _args):
            return 0 if iid[1] == 3 else -704220025

    service = _ExpiringService()
    session = _FakeSession()

    async def fake_login(_self, force_refresh=False):
        attempts.append(force_refresh)
        return object(), session, ""

    monkeypatch.setattr(MiDevice, "_login_xiaomiio", fake_login)
    monkeypatch.setattr(mi_device, "MiIOService", lambda account: service)
    monkeypatch.setattr(mi_device, "run_async", _fake_run_async)

    code, msg = _run_coro(MiDevice(address="dev", did="did").speak("你好"))

    assert code == 0, msg
    assert attempts == [False, True], "第一次失败后应带着 force_refresh 重试一次"


def test_speak_does_not_retry_on_plain_action_error(monkeypatch):
    """普通动作失败（非登录问题）不该触发刷新重试。"""
    attempts: List[bool] = []
    service = _FakeService(action_code=-704220025)
    session = _FakeSession()

    async def fake_login(_self, force_refresh=False):
        attempts.append(force_refresh)
        return object(), session, ""

    monkeypatch.setattr(MiDevice, "_login_xiaomiio", fake_login)
    monkeypatch.setattr(mi_device, "MiIOService", lambda account: service)
    monkeypatch.setattr(mi_device, "run_async", _fake_run_async)

    code, msg = _run_coro(MiDevice(address="dev", did="did").speak("你好"))

    assert code != 0
    assert attempts == [False]
