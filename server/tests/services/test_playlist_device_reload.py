"""播放列表设备映射的 reload 健壮性回归。

故障现象（线上）：
    03:05:26 [ERROR] [playlist_mgr.py:330] [PlaylistMgr] Reload error: 'type'
    03:05:31 [ERROR] [playlist_mgr.py:330] [PlaylistMgr] Reload error: 'type'
每 5 秒重试一次、始终失败 —— 播放列表加载不出来。

根因：`PlaylistDevices.refresh_all` 把**原始** `device` 字典直接交给
`create_device`，而后者当时用 `node["type"]` 取值。某条播放列表没有配置输出设备
时传进去的是空 dict，于是抛 `KeyError: 'type'`（渲染出来就是 `'type'`）。
而 reload 是整体事务性的：**一条数据即可让整次加载失败**，并在 `_needs_reload`
下无限重试。

修复两处：
1. `refresh_all` 改用 `_build_device_spec` 归一化（与 `refresh_single` 一致）——
   该校验器会补默认类型、拦非法类型、无地址时返回 None；
2. `create_device` 用 `node.get("type")`，缺失类型与「未知类型」同样返回 obj=None，
   不再抛异常（防御任何调用方）。
"""

from unittest.mock import patch

import pytest

from core.device import create_device
from core.services.playlist.devices import DEVICE_TYPES, PlaylistDevices


@pytest.fixture
def linux_devices():
    """在非 Linux 上也能跑到实际重建逻辑（refresh_all 会提前返回）。"""
    with patch('core.services.playlist.devices._is_linux', return_value=True):
        yield PlaylistDevices()


class TestCreateDeviceToleratesMissingType:
    """`create_device` 不得因缺字段而抛异常。"""

    def test_empty_node_does_not_raise(self):
        """空 dict（相当于「没配置设备」）不能抛 KeyError。"""
        ret = create_device({})
        assert ret['obj'] is None, '缺类型时应返回 obj=None，与「未知类型」一致'

    def test_missing_type_with_address_does_not_raise(self):
        ret = create_device({'address': '192.168.1.9'})
        assert ret['obj'] is None

    def test_unknown_type_does_not_raise(self):
        ret = create_device({'type': 'bogus', 'address': '192.168.1.9'})
        assert ret['obj'] is None

    def test_known_type_still_creates_device(self):
        """正常输入的行为不能被上面几条改动影响。"""
        ret = create_device({'type': 'dlna', 'address': '192.168.1.9'})
        assert ret['obj'] is not None

    def test_node_is_preserved(self):
        node = {'type': 'dlna', 'address': '192.168.1.9'}
        assert create_device(node)['node'] is node


class TestRefreshAllToleratesMissingDevice:
    """`refresh_all` 遇到「没有设备」的数据不得让整次 reload 失败。"""

    def test_playlist_without_device_does_not_raise(self, linux_devices):
        """核心回归：这条数据以前会让 reload 整体失败。"""
        raw = {
            'pl-1': {'name': '没有设备的列表'},
            'pl-2': {'name': '有设备', 'device': {'type': 'dlna', 'address': '192.168.1.5'}},
        }
        linux_devices.refresh_all(raw)      # 不得抛异常

        assert linux_devices.get('pl-2') is not None, '正常的那条仍要映射上'
        assert linux_devices.get('pl-1') is None, '没有设备的列表应保持无映射'

    def test_empty_device_dict_does_not_raise(self, linux_devices):
        linux_devices.refresh_all({'pl-1': {'device': {}}})
        assert linux_devices.get('pl-1') is None

    def test_invalid_type_is_skipped_not_fatal(self, linux_devices):
        """非法类型只跳过该条，不影响同批其它播放列表。"""
        raw = {
            'bad': {'device': {'type': 'bogus', 'address': '192.168.1.6'}},
            'good': {'device': {'type': 'dlna', 'address': '192.168.1.5'}},
        }
        linux_devices.refresh_all(raw)
        assert linux_devices.get('bad') is None
        assert linux_devices.get('good') is not None

    def test_address_without_type_defaults_to_dlna(self, linux_devices):
        """有地址但缺类型：走默认类型，与 refresh_single 的既有行为一致。"""
        linux_devices.refresh_all({'pl-1': {'device': {'address': '192.168.1.7'}}})
        assert linux_devices.get('pl-1') is not None, (
            '有地址时应补默认类型建出设备（_build_device_spec 的约定）'
        )

    def test_callback_still_runs_for_mapped_playlists(self, linux_devices):
        """回调（刷新 cron）只对建出设备的播放列表触发，且不因跳过项中断。"""
        seen = []
        raw = {
            'no-dev': {'name': '无设备'},
            'with-dev': {'name': '有设备', 'device': {'type': 'dlna', 'address': '192.168.1.5'}},
        }
        linux_devices.refresh_all(raw, on_each_playlist=lambda pid, data: seen.append(pid))
        assert 'with-dev' in seen
        assert 'no-dev' not in seen

    def test_empty_input_is_noop(self, linux_devices):
        linux_devices.refresh_all({})
        assert linux_devices.get('anything') is None

    def test_many_playlists_all_rebuilt(self, linux_devices):
        """批量数据里混入若干「无设备」项，其余仍要全部映射上。"""
        raw = {f'pl-{i}': {'device': {'type': 'dlna', 'address': f'192.168.1.{i}'}}
               for i in range(1, 6)}
        raw['broken-a'] = {'name': '无设备'}
        raw['broken-b'] = {'device': {}}
        linux_devices.refresh_all(raw)

        for i in range(1, 6):
            assert linux_devices.get(f'pl-{i}') is not None, f'pl-{i} 未被映射'
        assert linux_devices.get('broken-a') is None
        assert linux_devices.get('broken-b') is None


def test_build_device_spec_is_the_single_normalizer(linux_devices):
    """`refresh_all` 与 `refresh_single` 必须用同一套归一化，行为才一致。

    直接对比两者对同一份数据的处理结果。
    """
    playlist = {'device': {'address': '192.168.1.7'}}      # 有地址、无类型

    linux_devices.refresh_all({'p': playlist})
    via_all = linux_devices.get('p')

    other = PlaylistDevices()
    with patch('core.services.playlist.devices._is_linux', return_value=True):
        other.refresh_single('p', playlist)
    via_single = other.get('p')

    assert (via_all is None) == (via_single is None), (
        'refresh_all 与 refresh_single 对同一数据的判断必须一致'
    )


def test_device_types_matches_what_frontend_writes():
    """`DEVICE_TYPES` 必须与前端写入的取值一致。

    前端常量：server/frontend/src/constants/device.ts
              export const DEVICE_TYPES = ["agent", "dlna", "bluetooth", "mi"]

    这里曾写成 "device_agent"（笔误），导致 agent 设备在 `_build_device_spec`
    校验时被判为非法而丢弃：该播放列表拿不到设备、播放永不开始，且只在日志里留
    一行 warning。`create_device` 也是按 "agent" 分派的，两处必须一致。
    """
    assert 'agent' in DEVICE_TYPES, (
        'DEVICE_TYPES 缺少 "agent" —— 前端保存的就是这个值，'
        '写成 "device_agent" 会让 agent 设备被判为无效并静默丢弃'
    )
    assert 'device_agent' not in DEVICE_TYPES, (
        '"device_agent" 不是前端写入的值；它只应作为服务名出现'
    )
    assert {'bluetooth', 'dlna', 'mi'} <= set(DEVICE_TYPES)


def test_agent_playlist_gets_a_device(linux_devices):
    """agent 类型的播放列表必须能建出设备对象（回归：此前被静默丢弃）。"""
    raw = {'pl-agent': {'device': {'type': 'agent', 'address': 'http://192.168.1.9:5000'}}}
    linux_devices.refresh_all(raw)

    mapped = linux_devices.get('pl-agent')
    assert mapped is not None, 'agent 设备被丢弃了 —— 播放永远不会开始'
    assert mapped['obj'] is not None, 'agent 设备没有建出对象'
    assert type(mapped['obj']).__name__ == 'DeviceAgent'


def test_every_supported_type_can_be_built(linux_devices):
    """`DEVICE_TYPES` 里的每种类型都要真能建出对象。

    防止常量与实际分派再次漂移：只要常量里写了一个 `create_device` 不认识的
    值，那条播放列表就会被静默丢弃。
    """
    addresses = {
        'agent': 'http://192.168.1.9:5000',
        'dlna': '192.168.1.5',
        'bluetooth': 'AA:BB:CC:DD:EE:FF',
        'mi': '192.168.1.6',
    }
    raw = {
        f'pl-{t}': {'device': {'type': t, 'address': addresses[t], 'did': 'x'}}
        for t in DEVICE_TYPES
    }
    linux_devices.refresh_all(raw)

    for t in DEVICE_TYPES:
        mapped = linux_devices.get(f'pl-{t}')
        assert mapped is not None and mapped['obj'] is not None, (
            f'类型 {t!r} 在 DEVICE_TYPES 里，但建不出设备对象 —— 该类型的播放列表会被丢弃'
        )
