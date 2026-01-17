# 模块：core.api.dlna_routes（dlna_bp）

> 本模块路由定义于 `core/api/dlna_routes.py`。
>
> 统一响应结构：返回 `{"code": 0|非0, "msg": "...", "data": ...}`（由 `core.utils._ok/_err` 封装）。

## GET `/api/dlna/scan`

- **用途**：扫描 DLNA 设备。
- **Query**
  - `timeout`：float，可选，默认 `5.0`
- **返回**：`_ok(devices)` 或 `_err(...)`

## GET|POST `/api/dlna/volume`

- **用途**：获取或设置 DLNA 设备音量。
- **参数**
  - `location`：string，必填（GET 用 query；POST 可用 JSON body）
- **GET 行为**
  - `device.get_volume()`
  - 成功：`_ok({"volume": <0-100>})`
- **POST Body（JSON）**
  - `location`：string，必填
  - `volume`：int，必填（0-100）
- **POST 行为**
  - `device.set_volume(volume)`
  - 成功：`_ok({"volume": volume})`

## POST `/api/dlna/stop`

- **用途**：停止 DLNA 设备播放。
- **Body（JSON）**
  - `location`：string，必填
- **返回**
  - 成功：`_ok({"message": "停止成功"})`
  - 失败：`_err("停止失败")` 或 `_err(msg)`
