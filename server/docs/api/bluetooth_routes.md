# 模块：core.api.bluetooth_routes（bluetooth_bp）

> 本模块路由定义于 `core/api/bluetooth_routes.py`。
>
> 统一响应结构：所有接口返回 `{"code": 0|非0, "msg": "...", "data": ...}`（由 `core.utils._ok/_err` 封装）。
>
> 注意：实际能力依赖 `bluetooth_mgr` 以及其背后的 `device_agent` 服务。

## GET `/api/bluetooth/scan`

- **用途**：扫描蓝牙设备。
- **Query**
  - `timeout`：float，可选，默认 `5.0`
- **返回**：`_ok(devices)` 或 `_err(...)`

## GET `/api/bluetooth/device`

- **用途**：获取某个蓝牙设备信息。
- **Query**
  - `address`：string，必填
- **返回**
  - 成功：`_ok(device)`
  - 失败：`_err("device not found")` 或 `_err("address is required")`

## POST `/api/bluetooth/connect`

- **用途**：连接蓝牙设备。
- **Body（JSON）**
  - `address`：string，必填
- **返回**
  - 若 `bluetooth_mgr.connect_device_sync` 已返回标准 `{code,msg,data}`，则原样返回
  - 否则返回 `_ok(result)`

## POST `/api/bluetooth/disconnect`

- **用途**：断开蓝牙设备。
- **Body（JSON）**
  - `address`：string，必填
- **返回**：同 `/bluetooth/connect`

## GET `/api/bluetooth/paired`

- **用途**：获取系统已配对蓝牙设备列表。
- **返回**：`_ok(devices)` 或 `_err(...)`
