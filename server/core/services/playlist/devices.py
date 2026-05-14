"""播放列表与设备实例的绑定（设备映射、单条刷新、音量、状态查询、停止）。"""

import sys
from typing import Any, Callable, Dict, Optional, Tuple

from core.device import create_device
from core.config import app_logger
from core.utils import time_to_seconds
from core.services.playlist.constants import DEVICE_TYPES

log = app_logger
_LOG = "[PlaylistDevices]"


def _is_linux() -> bool:
    return sys.platform == "linux"


class PlaylistDevices:
    """维护 ``playlist_id -> create_device(...)`` 结果；仅 Linux 下建连。"""

    def __init__(self, device_map: Optional[Dict[str, Any]] = None) -> None:
        self._device_map: Dict[str, Any] = device_map if device_map is not None else {}

    # ---------- dict-like 读 ----------

    def get(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """返回 ``{"obj": device, ...}`` 条目；不存在或非 dict 返回 None。"""
        entry = self._device_map.get(playlist_id)
        return entry if isinstance(entry, dict) else None

    def get_obj(self, playlist_id: str) -> Optional[Any]:
        """直接拿设备对象；不存在或条目非 dict 返回 None。"""
        entry = self._device_map.get(playlist_id)
        if not isinstance(entry, dict):
            return None
        return entry.get("obj")

    def __contains__(self, playlist_id: str) -> bool:
        return playlist_id in self._device_map

    # ---------- dict-like 写（主要给测试 / refresh_* 用） ----------

    def __setitem__(self, playlist_id: str, entry: Dict[str, Any]) -> None:
        self._device_map[playlist_id] = entry

    def clear(self) -> None:
        self._device_map.clear()

    def pop(self, playlist_id: str, default: Any = None) -> Any:
        return self._device_map.pop(playlist_id, default)

    # ---------- 全量 / 单条刷新 ----------

    def refresh_all(
        self,
        playlist_raw: Dict[str, Any],
        on_each_playlist: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        """清空映射后按 ``playlist_raw`` 全量重建；每条成功后可选回调（如刷新 cron）。"""
        self.clear()
        if not playlist_raw or not _is_linux():
            return
        for p_id, playlist_data in playlist_raw.items():
            self[p_id] = create_device(playlist_data.get("device", {}))
            if on_each_playlist is not None:
                on_each_playlist(p_id, playlist_data)

    def refresh_single(self, playlist_id: str, playlist_data: Dict[str, Any]) -> None:
        """只更新单个播放列表的设备映射；无效地址 / 类型则从映射中移除。"""
        if not _is_linux():
            return
        try:
            spec = self._build_device_spec(playlist_id, playlist_data)
            if spec is None:
                self.pop(playlist_id)
            else:
                self[playlist_id] = create_device(spec)
        except Exception as e:
            log.error(f"{_LOG} refresh_single error: id={playlist_id}, {e}", exc_info=True)
            raise

    @staticmethod
    def _build_device_spec(playlist_id: str, playlist_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从 playlist_data 构造 ``create_device`` 入参；缺地址或类型非法时返回 None。

        约定：单一来源是嵌套 ``device.{type,address,...}``，不再回退到根级 ``device_type``。
        """
        device = playlist_data.get("device") or {}
        address = device.get("address")
        if not address:
            return None

        device_type = device.get("type") or "dlna"
        if device_type not in DEVICE_TYPES:
            log.warning(f"{_LOG} 设备类型无效: {playlist_id}, type={device_type}")
            return None

        return {
            "type": device_type,
            "address": address,
            "did": device.get("did"),
            "name": device.get("name"),
        }

    # ---------- 与设备的通用 I/O ----------

    def read_progress(self, playlist_id: str) -> Tuple[str, int]:
        """读设备进度。返回 ``(state, remaining_seconds)``；设备不存在 / get_status 失败 / 异常时返回 ``("", 0)``
        （状态空串、剩余 0 秒——调用方对状态比较与 ``remaining >= N`` 判断都会自然落到「无需等待」分支）。

        remaining 已 clip 到 ``>= 0``；duration/position 解析失败时记 warning 并返回 0。
        """
        device = self.get_obj(playlist_id)
        if device is None:
            return "", 0
        try:
            code, status = device.get_status()
        except Exception as e:
            log.error(f"{_LOG} get_status error: {playlist_id}, {e}")
            return "", 0
        if code != 0:
            err = status.get("error", "未知错误") if isinstance(status, dict) else status
            log.warning(f"{_LOG} get_status failed: {playlist_id}, {err}")
            return "", 0
        # 协议上 code==0 时 status 必须是 dict，但仍兜底一层，避免下游 .get 抛异常。
        if not isinstance(status, dict):
            log.warning(f"{_LOG} get_status code=0 但 status 非 dict: {playlist_id}, status={status!r}")
            return "", 0

        state = status.get("state", "")
        duration_str = status.get("duration", "00:00:00")
        position_str = status.get("position", "00:00:00")
        try:
            remaining = max(0, time_to_seconds(duration_str) - time_to_seconds(position_str))
        except (ValueError, AttributeError) as e:
            log.warning(
                f"{_LOG} 计算 remaining 失败: {playlist_id}, "
                f"duration={duration_str}, position={position_str}, {e}"
            )
            remaining = 0
        return state, remaining

    def safe_stop(self, playlist_id: str) -> Tuple[int, str]:
        """吞异常的 stop。设备不存在视为 no-op 成功 ``(0, "")``；异常返 ``(-1, str(e))``；否则透传设备的 (code, msg)。

        若调用方需要区分「设备不存在」与「真正停止」，请先用 ``pid in self`` 做前置 guard。
        """
        device = self.get_obj(playlist_id)
        if device is None:
            return 0, ""
        try:
            code, msg = device.stop()
            return code, msg
        except Exception as e:
            log.warning(f"{_LOG} stop error: {playlist_id}, {e}")
            return -1, str(e)

    @staticmethod
    def apply_volume(playlist_id: str, device: Any, playlist_data: Dict[str, Any]) -> None:
        """若播放列表配置了 ``device_volume`` 且设备支持 ``set_volume``，则下发音量。"""
        device_volume = playlist_data.get("device_volume")
        if device_volume is None or not hasattr(device, "set_volume"):
            return
        try:
            code, msg = device.set_volume(device_volume)
        except Exception as e:
            log.warning(f"{_LOG} Set device volume error: id={playlist_id}, {e}")
            return
        if code == 0:
            log.info(f"{_LOG} Set device volume to {device_volume} for playlist {playlist_id}")
        else:
            log.warning(f"{_LOG} Set device volume failed: id={playlist_id}, code={code}, msg={msg}")
