# 模块：core.api.mi_routes（mi_bp）

> 本模块路由定义于 `core/api/mi_routes.py`。
>
> 统一响应结构：返回 `{"code": 0|非0, "msg": "...", "data": ...}`（由 `core.utils._ok/_err` 封装）。

## GET `/api/mi/scan`

- **用途**：扫描小米设备。
- **Query**
  - `timeout`：float，可选，默认 `5.0`
- **返回**：`_ok(devices)` 或 `_err(...)`

## GET|POST `/api/mi/volume`

- **用途**：获取或设置小米设备音量。
- **参数**
  - `device_id`：string，必填（GET 用 query；POST 可用 JSON body）
- **GET 行为**
  - `device.get_volume()`
  - 成功：`_ok({"volume": <0-100>})`
- **POST Body（JSON）**
  - `device_id`：string，必填
  - `volume`：int，必填（0-100）
- **POST 行为**
  - `device.set_volume(volume)`
  - 成功：`_ok({"volume": volume})`

## GET `/api/mi/status`

- **用途**：获取小米设备播放状态。
- **Query**
  - `device_id`：string，必填
- **返回**
  - 成功：`_ok(status)`
  - 失败：`_err("获取状态失败")` 或 `_err(status.error)`

## POST `/api/mi/stop`

- **用途**：停止小米设备播放。
- **Body（JSON）**
  - `device_id`：string，必填
- **返回**
  - 成功：`_ok({"message": "停止成功"})`
  - 失败：`_err("停止失败")` 或 `_err(msg)`
