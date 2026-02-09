# 模块：core.api.pic_routes（pic_bp）

> 本模块路由定义于 `core/api/pic_routes.py`。
>
> 图片相关 API，路径统一以 `/pic/` 为前缀。上传的图片保存在 `DEFAULT_BASE_DIR/pic` 目录下。

## 数据库图片（兼容旧接口）

### GET `/pic/viewPic`

- **Query**
  - `id`：string，必填
- **行为**
  - `db_mgr.get_data_idx(db_mgr.TABLE_PIC, id)`
  - 成功：渲染 `image.html`
  - 失败：`404` + `{"error":"Image not found"}`

## 文件系统图片（上传/删除/查看）

### POST `/pic/upload`

- **请求**：multipart/form-data，字段 `file` 为图片文件
- **限制**：支持 jpg/jpeg/png/gif/webp/bmp
- **返回**
  - 成功：`{"code":0,"msg":"ok","data":{"filename":"...","path":"..."}}`
  - 失败：`{"code":-1,"msg":"..."}`

### POST `/pic/delete`

- **Body（JSON）** 或 **Query**
  - `name`：string，必填，文件名
- **返回**
  - 成功：`{"code":0,"msg":"ok","data":{"filename":"..."}}`
  - 失败：`{"code":-1,"msg":"..."}`

### GET `/pic/view`

- **Query**
  - `name`：string，必填，文件名
- **行为**
  - 按文件名返回图片文件流
  - 成功：图片二进制
  - 失败：`400` 或 `404` + `{"error":"..."}`
