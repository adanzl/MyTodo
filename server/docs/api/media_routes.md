# 模块：core.api.media_routes（media_bp）

> 本模块路由定义于 `core/api/media_routes.py`。
>
> 统一响应结构：多数接口返回 `{"code": 0|非0, "msg": "...", "data": ...}`。部分接口直接返回文件流。

## 媒体文件服务

### GET `/api/media/getDuration`

- **用途**：获取媒体文件时长（秒）。
- **Query**
  - `path`：string，必填
- **返回**
  - 成功：`_ok({"duration": <float>, "path": "..."})`
  - 失败：`_err("...")`

### GET `/api/media/files/<path:filepath>`

- **用途**：按路径直接返回媒体文件（用于 DLNA 播放）。
- **Path**
  - `filepath`：string，必填
- **返回**：文件流（`send_file`）。

## 音频合成（merge）

### POST `/api/media/merge/create`

- **Body（JSON）**
  - `name`：string，可选（默认当前时间）
- **返回**：`_ok(task_info)`

### POST `/api/media/merge/upload`

- **说明**：multipart 上传文件到任务。
- **Query / Form**
  - `task_id`：string，必填
- **Form（multipart/form-data）**
  - `file`：file，必填
- **返回**：`_ok(file_info)` 或 `_err(...)`

### POST `/api/media/merge/addFileByPath`

- **Body（JSON 或 form）**
  - `task_id`：string，必填
  - `file_path`：string，必填
- **返回**：`_ok(file_info)` 或 `_err(...)`

### POST `/api/media/merge/deleteFile`

- **Body（JSON 或 form）**
  - `task_id`：string，必填
  - `file_index`：int，必填
- **返回**：`_ok({"message": "..."})` 或 `_err(...)`

### POST `/api/media/merge/reorderFiles`

- **Body（JSON 或 form）**
  - `task_id`：string，必填
  - `file_indices`：int[]，必填
- **返回**：`_ok(task_info)` 或 `_err(...)`

### POST `/api/media/merge/start`

- **Body（JSON 或 form）**
  - `task_id`：string，必填
- **返回**：`_ok(task_info)` 或 `_err(...)`

### POST `/api/media/merge/get`

- **Body（JSON 或 form）**
  - `task_id`：string，必填
- **返回**：`_ok(task_info)` 或 `_err(...)`

### GET `/api/media/merge/list`

- **返回**：`_ok({"tasks": [...]})` 或 `_err(...)`

### POST `/api/media/merge/delete`

- **Body（JSON 或 form）**
  - `task_id`：string，必填
- **返回**：`_ok({"message": "..."})` 或 `_err(...)`

### GET `/api/media/merge/download`

- **Query**
  - `task_id`：string，必填
- **返回**：文件流（默认下载名 `merged.mp3`）或 `_err(...)`

### POST `/api/media/merge/save`

- **Body（JSON 或 form）**
  - `task_id`：string，必填
  - `target_path`：string，必填（目标目录）
- **返回**：`_ok({"target_file": "...", "message": "转存成功"})` 或 `_err(...)`

## 音频转码（convert）

### GET `/api/media/convert/list`

- **返回**：`_ok({"tasks": [...]})` 或 `_err(...)`

### POST `/api/media/convert/create`

- **Body（JSON）**
  - `name`：string，可选（默认当前时间）
  - `output_dir`：string，可选
  - `overwrite`：bool，可选
- **返回**：`_ok(task_info)` 或 `_err(...)`

### POST `/api/media/convert/get`

- **Body（JSON 或 form）**
  - `task_id`：string，必填
- **返回**：`_ok(task_info)` 或 `_err(...)`

### POST `/api/media/convert/delete`

- **Body（JSON 或 form）**
  - `task_id`：string，必填
- **返回**：`_ok({"success": true})` 或 `_err(...)`

### POST `/api/media/convert/update`

- **Body（JSON 或 form）**
  - `task_id`：string，必填
  - `name`：string，可选
  - `directory`：string，可选
  - `output_dir`：string，可选
  - `overwrite`：bool，可选
- **返回**：`_ok(task_info)` 或 `_err(...)`

### POST `/api/media/convert/start`

- **Body（JSON 或 form）**
  - `task_id`：string，必填
- **返回**：`_ok(task_info)` 或 `_err(...)`
