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

## POST `/api/mi/speak`

- **用途**：让小爱音箱播报文字（走 miot 动作 `Intelligent Speaker → Play Text`）。
- **Body（JSON）**
  - `device_id`：string，必填（NAS deviceId）
  - `device_did`：string，必填（米家 DID，与其它 mi 接口一致）
  - `text`：string，必填，去首尾空白后非空，最长 500 字
- **实现要点**
  - 不用 ubus 的 `mibrain.text_to_speech`：新固件（L05C / X08A 等）会静默丢弃该消息，接口却仍返回转发成功，无法判断是否真的出声。
  - `Play Text` 的 aiid 因型号而异（l05c→3、x08a→1、lx06→1），代码按型号解析，见 `core/device/mi_device.py` 的 `MIOT_PLAY_TEXT_AIID`。
  - 需要 `xiaomiio` 凭据；登录时先刷新 `micoapi` 的 passToken，再另开 session 登 `xiaomiio`。
  - 通道失败直接报错，不回退到 `text_to_speech`。
- **返回**
  - 成功：`_ok({"message": "播报成功"})`
  - 失败：`_err(msg)`，msg 可能是 `登录验证失败，请检查账号密码是否正确`、`无法获取设备型号`、`型号 xxx 不支持文字播报`、`播报失败: miot 返回 <code>`

## POST `/api/mi/stop`

- **用途**：停止小米设备播放。
- **Body（JSON）**
  - `device_id`：string，必填
- **返回**
  - 成功：`_ok({"message": "停止成功"})`
  - 失败：`_err("停止失败")` 或 `_err(msg)`
