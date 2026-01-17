# 模块：core.api.pdf_routes（pdf_bp）

> 本模块路由定义于 `core/api/pdf_routes.py`。
>
> 统一响应结构：返回 `{"code": 0|非0, "msg": "...", "data": ...}`（由 `core.utils._ok/_err` 封装）。

## POST `/api/pdf/upload`

- **用途**：上传 PDF 文件。
- **Form（multipart/form-data）**
  - `file`：file，必填
- **返回**
  - 成功：`_ok(file_info)`
  - 失败：`_err("...")`
  - 文件过大：`_err("文件太大，超过服务器限制（最大 2000MB）")`

## POST `/api/pdf/decrypt`

- **用途**：提交 PDF 解密任务（异步）。
- **Body（JSON）**
  - `task_id`：string，必填（通常是上传后的文件名）
  - `password`：string，可选
- **返回**
  - 成功：`_ok({"message": "..."})`
  - 失败：`_err("...")`

## GET `/api/pdf/task/<path:task_id>`

- **用途**：获取 PDF 任务状态。
- **Path**
  - `task_id`：string，必填
- **返回**
  - 成功：`_ok(task_info)`
  - 失败：`_err("...")`

## GET `/api/pdf/list`

- **用途**：列出所有 PDF 文件（已上传和已解密）。
- **返回**
  - 成功：`_ok(result)`

## GET `/api/pdf/download/<path:filename>`

- **用途**：下载 PDF 文件。
- **Path**
  - `filename`：string，必填
- **Query**
  - `type`：string，可选，`uploaded` 或 `unlocked`（默认 `unlocked`）
- **返回**：文件流或 `_err("...")`

## POST `/api/pdf/delete`

- **用途**：删除 PDF 任务（包括上传和解密的文件）。
- **Body（JSON）**
  - `task_id`：string，必填
- **返回**
  - 成功：`_ok({"message": "..."})`
  - 失败：`_err("...")`
