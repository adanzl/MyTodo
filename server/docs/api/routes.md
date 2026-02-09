# 模块：core.api.routes（api_bp）

> 本模块路由定义于 `core/api/routes.py`。
>
> 统一响应结构：多数接口返回 `{"code": 0|非0, "msg": "...", "data": ...}`（由 `core.utils._ok/_err` 或各 mgr 返回决定）。本模块部分接口直接返回 HTML。

## 日志/页面类

### GET `/api/natapp`

- **用途**：读取并展示 `/opt/natapp/logs/natapp_web.log`
- **返回**：`text/html`

### GET `/api/log`

- **用途**：读取 `logs/app.log` 并倒序展示，渲染模板 `server_log.html`
- **返回**：`text/html`

### POST `/api/write_log`

- **用途**：将请求 body（按 `utf-8` 解码）写入应用日志
- **请求体**：任意文本（非 JSON）
- **返回**：`{}`

> 图片展示接口已迁移至 `core/api/pic_routes.py`（路径 `/pic/viewPic`），参见 [pic_routes.md](./pic_routes.md)。应用挂载在 `/api` 下时，完整路径为 `/api/pic/...`。

## Save 存储

### GET `/api/getSave`

- **Query**
  - `id`：string，必填
- **返回**：`db_mgr.get_save(id)` 原样返回

### POST `/api/setSave`

- **Body（JSON）**
  - `id`：string，必填
  - `user`：string，可选（是否必填取决于 `db_mgr` 实现）
  - `data`：any，必填（服务端会 `json.dumps`）
- **返回**：`db_mgr.set_save(id, user, data)` 原样返回

## 通用数据库 CRUD

### GET `/api/getAll`

- **Query**
  - `table`：string，必填
  - `pageSize`：int，默认 20
  - `pageNum`：int，默认 1
  - `fields`：string，默认 `*`（示例：`id,name,score`）
  - `conditions`：string(JSON)，可选（示例：`{"enable":1}`）
- **返回**：`db_mgr.get_list(table, page_num, page_size, fields, conditions)`

### GET `/api/getData`

- **Query**
  - `table`：string，必填
  - `id`：string，可选
  - `idx`：int，可选
  - `fields`：string，可选
- **行为**
  - `fields` 为空：`db_mgr.get_data_idx(table, id, idx)`
  - `fields` 非空：`db_mgr.get_data(table, id, fields)`
- **返回**：对应 `db_mgr` 结果

### POST `/api/setData`

- **Body（JSON）**
  - `table`：string，必填
  - `data`：object 或 array，必填
- **返回**：`db_mgr.set_data(table, data)`

### POST `/api/delData`

- **Body（JSON）**
  - `table`：string，必填
  - `id`：string/int，必填
- **返回**：`db_mgr.del_data(table, id)`

### POST `/api/query`

- **Body（JSON）**
  - `sql`：string，必填
- **返回**：`db_mgr.query(sql)`

## Redis 读写

### GET `/api/getRdsData`

- **Query**
  - `table`：string，必填
  - `id`：string，必填
- **行为**
  - Redis key：`{table}:{id}`
- **返回**
  - 成功：`{"code":0,"msg":"ok","data":"<string>"}`

### GET `/api/getRdsList`

- **Query**
  - `key`：string，必填
  - `pageSize`：int，默认 10
  - `startId`：int，默认 -1
- **返回**
  - `{"code":0,"msg":"ok","data":{"totalCount":0,"totalPage":0,"startId":-1,"pageSize":10,"data":[]}}`

### POST `/api/setRdsData`

- **Body（JSON）**
  - `table`：string，必填
  - `data`：object，必填
    - `id`：string/int，必填
    - `value`：string，必填
- **行为**
  - Redis key：`{table}:{id}`
- **返回**
  - 成功：`{"code":0,"msg":"ok","data":<id>}`

### POST `/api/addRdsList`

- **Body（JSON）**
  - `key`：string，必填
  - `value`：string，必填
- **行为**：`rds_mgr.rpush(key, value)`
- **返回**：`{"code":0,"msg":"ok","data":<value>}`

## 聊天消息查询

### GET `/api/chatMessages`

- **Query**
  - `conversation_id`：string，必填
  - `limit`：string/int，可选
  - `first_id`：string/int，可选
  - `user`：string，可选
- **返回**：`{"code":0,"msg":"ok","data": AILocal.get_chat_messages(...)}`

## 积分/抽奖

### POST `/api/addScore`

- **Body（JSON）**
  - `user`：string，必填
  - `value`：number，必填
  - `action`：string，必填
  - `msg`：string，可选
- **返回**：`db_mgr.add_score(user, value, action, msg)`

### POST `/api/doLottery`

- **Body（JSON）**
  - `user_id`：string/int，必填
  - `cate_id`：int，必填
- **返回**
  - 成功：`{"code":0,"msg":"抽奖成功","data":{"gift":{...},"fee":<cost>}}`
  - 失败：`{"code":-1,"msg":"..."}`

## 文件系统浏览/信息

### GET `/api/listDirectory`

- **Query**
  - `path`：string，可选（默认 `/mnt`）
  - `extensions`：string，默认 `audio`（可选：`audio`/`video`/`all`/`.mp3,.wav`）
- **安全限制**
  - 禁止 `..`、`~`
  - 最终路径必须在 `/mnt` 下
- **返回**
  - 成功：`{"code":0,"msg":"ok","data":[...],"currentPath":"..."}`

### GET `/api/getFileInfo`

- **Query**
  - `path`：string，必填
- **行为**
  - 规范化并限制在 `/mnt` 下
  - 媒体文件会尝试读取时长（`ffprobe`）
- **返回**
  - `{"code":0,"msg":"ok","data":{"name":"...","path":"...","size":0,"modified":0,"isDirectory":false,"isMediaFile":true,"duration":0}}`
