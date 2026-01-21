import asyncio
import types
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def fast_bluetooth_mgr_runtime(monkeypatch):
    """Make bluetooth_mgr tests fast/stable by disabling any real gevent/subprocess behavior."""
    import core.services.bluetooth_mgr as bm

    # Never spawn real greenlets in unit tests
    class _FakeGreenlet:

        def __init__(self, result):
            self._result = result

        def get(self, timeout=None):
            return self._result

    monkeypatch.setattr(bm, "spawn", lambda fn: _FakeGreenlet(fn()))

    # Prevent touching the real filesystem PATH lookup for commands
    monkeypatch.setattr(bm.shutil, "which", lambda name: None)


@pytest.fixture
def mock_bluetooth_dev(monkeypatch):
    """Patches the BluetoothDev class to avoid its internal logic."""
    import core.services.bluetooth_mgr as bm

    class FakeDev:

        def __init__(self, address=None, name=None, metadata=None):
            self.address = address
            self.name = name
            self.metadata = metadata
            self.connected = False
            self.client = None

        def to_dict(self):
            return {"address": self.address, "name": self.name, "connected": self.connected}

    monkeypatch.setattr(bm, "BluetoothDev", FakeDev)
    return FakeDev


def test_update_or_create_device_creates_and_updates(mock_bluetooth_dev):
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    dev1 = mgr._update_or_create_device("aa:bb", "n1", {"k": 1})
    assert dev1.address == "AA:BB"
    assert mgr.devices["AA:BB"].name == "n1"

    dev2 = mgr._update_or_create_device("AA:BB", "n2", {"k": 2})
    assert dev2 is dev1
    assert mgr.devices["AA:BB"].name == "n2"
    assert mgr.devices["AA:BB"].metadata == {"k": 2}


def test_get_friendly_name_priority():
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    device = types.SimpleNamespace(address="11:22:33:44:55:66", name="DevName")

    adv = types.SimpleNamespace(local_name="AdvName")
    assert mgr._get_friendly_name(device, adv) == "AdvName"

    adv = types.SimpleNamespace(local_name=None)
    assert mgr._get_friendly_name(device, adv) == "DevName"

    device2 = types.SimpleNamespace(address="11:22:33:44:55:66", name=None)
    name = mgr._get_friendly_name(device2, adv)
    assert name.startswith("Unknown Device")
    assert "55:66" in name


def test_build_ble_metadata_bytes_decode_path():
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    adv = types.SimpleNamespace(
        manufacturer_data={1: b"Hello World"},
        service_data={"uuid": b"\x01\x02"},
        service_uuids=["u1", "u2"],
        local_name="LN",
        tx_power=-5,
    )

    meta = mgr._build_ble_metadata(adv)

    assert meta["local_name"] == "LN"
    assert meta["tx_power"] == -5
    assert meta["service_uuids"] == ["u1", "u2"]
    assert meta["service_data"]["uuid"]["hex"] == "0102"

    m = meta["manufacturer_data"][1]
    assert m["hex"] == b"Hello World".hex()
    assert m["length"] == len(b"Hello World")
    assert "decoded" in m


def test_build_ble_metadata_no_adv_returns_empty():
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()
    assert mgr._build_ble_metadata(None) == {}


def test_scan_ble_devices_updates_cache_and_returns_list(monkeypatch, mock_bluetooth_dev):
    import core.services.bluetooth_mgr as bm
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    device = types.SimpleNamespace(address="11:22", name="Dev")
    adv = types.SimpleNamespace(
        local_name="Adv",
        manufacturer_data={},
        service_data={},
        service_uuids=[],
        tx_power=None,
    )

    async def fake_discover(timeout, return_adv):
        assert return_adv is True
        return {"k": (device, adv)}

    monkeypatch.setattr(bm.BleakScanner, "discover", fake_discover)

    devices = asyncio.run(mgr.scan_ble_devices(timeout=0.01))

    assert len(devices) == 1
    assert devices[0]["address"] == "11:22"
    assert devices[0]["name"] == "Adv"

    assert "11:22".upper() in mgr.devices


def test_scan_ble_devices_already_scanning_returns_empty():
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()
    mgr.scanning = True

    devices = asyncio.run(mgr.scan_ble_devices(timeout=0.01))
    assert devices == []


def test_scan_ble_devices_exception_returns_empty_and_resets_flag(monkeypatch):
    import core.services.bluetooth_mgr as bm
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    async def fake_discover(timeout, return_adv):
        raise Exception("boom")

    monkeypatch.setattr(bm.BleakScanner, "discover", fake_discover)

    devices = asyncio.run(mgr.scan_ble_devices(timeout=0.01))
    assert devices == []
    assert mgr.scanning is False


def test_connect_device_already_connected(mock_bluetooth_dev):
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()
    dev = mgr._update_or_create_device("AA:BB", "n1", {})
    dev.connected = True

    result = asyncio.run(mgr.connect_device("aa:bb"))
    assert result["code"] == 0
    assert "Already connected" in result["msg"]


def test_connect_device_success_and_failure(monkeypatch, mock_bluetooth_dev):
    import core.services.bluetooth_mgr as bm
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()
    mgr._update_or_create_device("AA:BB", "AA:BB", {})

    mock_client = MagicMock()

    async def fake_connect():
        return None

    async def fake_read_gatt(*args, **kwargs):
        return b"GattName"

    mock_client.connect = fake_connect
    mock_client.read_gatt_char = fake_read_gatt

    with patch.object(bm, "BleakClient", return_value=mock_client):
        result = asyncio.run(mgr.connect_device("aa:bb"))
        assert result["code"] == 0
        assert mgr.devices["AA:BB"].name == "GattName"
        assert mgr.devices["AA:BB"].connected is True

    with patch.object(bm, "BleakClient", side_effect=Exception("Connection Error")):
        mgr.devices["AA:BB"].connected = False
        result = asyncio.run(mgr.connect_device("aa:bb"))
        assert result["code"] == -1
        assert "Connection Error" in result["msg"]


def test_disconnect_device(mock_bluetooth_dev):
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()
    dev = mgr._update_or_create_device("AA:BB", "n1", {})

    mock_client = MagicMock()

    async def fake_disconnect():
        return None

    mock_client.disconnect = fake_disconnect
    dev.client = mock_client
    dev.connected = True

    result = asyncio.run(mgr.disconnect_device("aa:bb"))
    assert result["code"] == 0
    assert dev.connected is False


def test_get_paired_devices_success_and_failure(monkeypatch):
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    def _run_side_effect(cmd, timeout=10, env=None):
        if cmd[:3] == ["bluetoothctl", "devices", "Connected"]:
            return 0, "Device AA:BB:CC:DD:EE:FF PairedDevice1\n", ""
        if cmd[:3] == ["bluetoothctl", "devices", "Paired"]:
            return 0, "Device AA:BB:CC:DD:EE:FF PairedDevice1\nDevice 11:22:33:44:55:66 PairedDevice2\n", ""
        return -2, "", "not found"

    monkeypatch.setattr(mgr, "_run_subprocess_safe", _run_side_effect)

    devices = mgr.get_paired_devices()
    assert len(devices) == 2

    # Failure: command not found
    monkeypatch.setattr(mgr, "_run_subprocess_safe", lambda *a, **kw: (-2, "", "not found"))
    assert mgr.get_paired_devices() == []


def test_find_command_fallback_searches_common_paths(monkeypatch):
    import core.services.bluetooth_mgr as bm
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    # shutil.which is patched to None by the autouse fixture; exercise common path fallback
    monkeypatch.setattr(bm.os.path, "exists", lambda p: p.endswith("/usr/bin/bluetoothctl"))
    monkeypatch.setattr(bm.os, "access", lambda p, mode: True)

    assert mgr._find_command("bluetoothctl") == "/usr/bin/bluetoothctl"


def test_parse_bluetoothctl_output_handles_name_missing():
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    # Second line has no name, should fall back to address
    stdout = "Device AA:BB:CC:DD:EE:FF DevName\nDevice 11:22:33:44:55:66\n"
    parsed = mgr._parse_bluetoothctl_output(stdout)

    assert parsed["AA:BB:CC:DD:EE:FF"] == "DevName"
    assert parsed["11:22:33:44:55:66"] == "11:22:33:44:55:66"


def test_run_subprocess_safe_sets_path_and_resolves_command(monkeypatch):
    import core.services.bluetooth_mgr as bm
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    monkeypatch.setattr(mgr, "_find_command", lambda name: "/usr/bin/" + name)

    captured = {}

    class _CapturePopen:

        def __init__(self, cmd, stdout, stderr, text, env):
            captured["cmd"] = cmd
            captured["env"] = env
            self.returncode = 0

        def communicate(self, timeout=None):
            return ("out", "err")

    monkeypatch.setattr(bm.subprocess, "Popen", _CapturePopen)

    code, out, err = mgr._run_subprocess_safe(["bluetoothctl", "devices"], timeout=1, env={"PATH": ""})

    assert code == 0
    assert out == "out"
    assert err == "err"
    assert captured["cmd"][0] == "/usr/bin/bluetoothctl"
    assert "PATH" in captured["env"]
    assert bm.DEFAULT_PATH in captured["env"]["PATH"]


def test_extract_metadata_covers_optional_fields():
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    adv = types.SimpleNamespace(
        manufacturer_data={1: b"\x01\x02"},
        service_data={"uuid": b"\x03"},
        service_uuids=["u1"],
        local_name="LN",
        tx_power=3,
    )

    meta = mgr._extract_metadata(adv)
    assert meta["manufacturer_data"]["1"]["hex"] == "0102"
    assert meta["service_data"]["uuid"]["hex"] == "03"
    assert meta["service_uuids"] == ["u1"]
    assert meta["local_name"] == "LN"
    assert meta["tx_power"] == 3


def test_scan_devices_sync_timeout(monkeypatch):
    import core.services.bluetooth_mgr as bm
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    def _raise_timeout(coro, timeout=None):
        coro.close()
        raise asyncio.TimeoutError()

    monkeypatch.setattr(bm, "run_async", _raise_timeout)

    assert mgr.scan_devices_sync(timeout=0.01) == []


def test_connect_device_sync_exception(monkeypatch):
    import core.services.bluetooth_mgr as bm
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    def _raise(coro, timeout=None):
        coro.close()
        raise Exception("boom")

    monkeypatch.setattr(bm, "run_async", _raise)

    res = mgr.connect_device_sync("aa:bb", timeout=0.01)
    assert res["code"] == -1


def test_disconnect_device_sync_timeout(monkeypatch):
    import core.services.bluetooth_mgr as bm
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()

    def _raise_timeout(coro, timeout=None):
        coro.close()
        raise asyncio.TimeoutError()

    monkeypatch.setattr(bm, "run_async", _raise_timeout)

    res = mgr.disconnect_device_sync("aa:bb", timeout=0.01)
    assert res["code"] == -1


def test_get_device(mock_bluetooth_dev):
    from core.services.bluetooth_mgr import BluetoothMgr

    mgr = BluetoothMgr()
    mgr._update_or_create_device("AA:BB", "n1", {})

    assert mgr.get_device("aa:bb") is not None
    assert mgr.get_device("xx:yy") is None
