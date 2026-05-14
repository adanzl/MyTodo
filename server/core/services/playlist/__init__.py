"""播放列表服务包。

> 重构计划见 `docs/playlist_重构_todo.md`。
> P0–P6 已完成；编排层不再直接调 Redis / ffprobe / ffmpeg / APScheduler / 设备 socket。

后续阶段会把 `core/services/playlist_mgr.py` 中的逻辑逐步迁入本包；
对外 import 路径 (`from core.services.playlist_mgr import playlist_mgr`)
将通过 P8 的薄壳保持兼容。
"""
