# 模块：core.api.playlist_routes（playlist_bp）

> 本模块路由定义于 `core/api/playlist_routes.py`。
>
> 统一响应结构：返回 `{"code": 0|非0, "msg": "...", "data": ...}`（由 `core.utils._ok/_err` 封装）。

## GET `/api/playlist/get`

- **用途**：获取播放列表集合；可选按 `id` 获取单个播放列表。
- **Query**
  - `id`：string，可选
    - `null` / `None` / 空字符串：返回整个集合
- **返回**：`_ok(playlist)` 或 `_err(...)`

## GET `/api/playlist/history`

- **用途**：获取播放列表更新历史。
- **Query**
  - `limit`：int，可选，默认10，范围1-10
    - 返回的历史记录数量
- **返回**：`_ok({timestamp: json_str, ...})` 或 `_err(...)`
  - 返回格式为字典，key 为时间戳（格式：`YYYY-MM-DD HH:MM:SS`），value 为该时刻的完整播放列表 JSON 字符串
  - 按时间倒序排列（最新的在前）
  - 最多保留10条历史记录
- **存储方式**：使用 Redis Hash 结构存储，key 为 `schedule_play:playlist_collection_history`，field 为时间戳，value 为 JSON 字符串

## POST `/api/playlist/update`

- **用途**：更新单个播放列表（必须包含 `id`）。
- **Body（JSON）**
  - `id`：string，必填
  - 其他字段：按 `playlist_mgr` 需要
- **返回**：成功 `_ok()`；失败 `_err(...)`

## POST `/api/playlist/updateAll`

- **用途**：覆盖更新整个播放列表集合。
- **Body（JSON）**
  - 字典结构 `{playlist_id: playlist_data, ...}`
- **返回**：成功 `_ok()`；失败 `_err(...)`

## POST `/api/playlist/play`

- **用途**：播放播放列表。
- **Body（JSON）**
  - `id`：string，必填
- **返回**：成功 `_ok()`；失败 `_err("播放播放列表 {id} 失败: {msg}")`

## POST `/api/playlist/playNext`

- **用途**：播放下一首。
- **Body（JSON）**
  - `id`：string，必填
- **返回**：成功 `_ok()`；失败 `_err("播放下一首失败: {msg}")`

## POST `/api/playlist/playPre`

- **用途**：播放上一首。
- **Body（JSON）**
  - `id`：string，必填
- **返回**：成功 `_ok()`；失败 `_err("播放上一首失败: {msg}")`

## POST `/api/playlist/stop`

- **用途**：停止播放。
- **Body（JSON）**
  - `id`：string，必填
- **返回**：成功 `_ok()`；失败 `_err("停止播放失败: {msg}")`

## POST `/api/playlist/reload`

- **用途**：从 RDS 重新加载播放列表数据。
- **返回**：成功 `_ok()`；失败 `_err(...)`
