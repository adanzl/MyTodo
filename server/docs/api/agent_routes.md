# 模块：core.api.agent_routes（agent_bp）

> 本模块路由定义于 `core/api/agent_routes.py`。
>
> 统一响应结构：所有接口返回 `{"code": 0|非0, "msg": "...", "data": ...}`（由 `core.utils._ok/_err` 封装）。

## POST `/api/agent/heartbeat`

- **用途**：设备 Agent 上报心跳，兼具注册与状态更新。
- **Body（JSON）**
  - `address`：string，必填
  - `name`：string，可选
  - `actions`：array，可选
- **行为**
  - 服务端会自动获取 `client_ip`（`X-Forwarded-For` / `X-Real-IP` / `remote_addr`）
  - 调用 `agent_mgr.handle_heartbeat(client_ip, address, name, actions)`
- **返回**：`_ok()` 或 `_err(...)`

## POST `/api/agent/event`

- **用途**：触发事件（由某个 Agent 上报/触发）。
- **Body（JSON）**
  - `key`：string，可选
  - `value`：any，可选
  - `action`：string，可选
- **行为**
  - 根据来源 IP 确定 Agent
  - 调用 `agent_mgr.handle_event(client_ip, key, value, action)`
- **返回**：成功 `_ok()`；失败 `_err(msg)`；Agent 未找到可能返回 `_err("agent not found")`

## GET `/api/agent/list`

- **用途**：获取所有已注册 Agent 设备列表（含在线状态推断）。
- **返回**：`_ok(device_list)`

## POST `/api/agent/mock`

- **用途**：模拟设备操作（调试/测试）。
- **Body（JSON）**
  - `agent_id`：string，必填
  - `action`：string，必填
  - `key`：string，可选
  - `value`：any，可选
- **行为**
  - `agent_mgr.get_agent(agent_id)` 获取实例
  - 调用 `agent.mock(action, key, value)`
- **返回**
  - 成功：`_ok(result.data)`
  - 失败：`_err(result.msg)`
