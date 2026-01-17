# API 文档

> 说明：本文档根据当前代码自动梳理生成。

## 访问前缀与挂载

- 实际服务通过 `DispatcherMiddleware` 挂载：
  - `/api`：后端 Flask API
  - `/web`：静态资源（`static` 目录）
- 因此：代码里声明的路由是 `/xxx`，实际访问路径为 `/api/xxx`。

## 通用响应处理

- 全局 `after_request` 会追加 CORS Header：
  - `Access-Control-Allow-Origin: *`
  - `Access-Control-Allow-Methods: *`
  - `Access-Control-Allow-Headers: *`
- 开发环境（`ENV != production`）会额外禁用浏览器缓存。

## 探活接口

- `GET /api/`：`<p>Hello, World!</p>`

---

## 模块文档索引（按蓝图/模块拆分）

- [core.api.routes](./routes.md)
- [core.api.agent_routes](./agent_routes.md)
- [core.api.bluetooth_routes](./bluetooth_routes.md)
- [core.api.media_routes](./media_routes.md)
- [core.api.playlist_routes](./playlist_routes.md)
- [core.api.dlna_routes](./dlna_routes.md)
- [core.api.mi_routes](./mi_routes.md)
- [core.api.pdf_routes](./pdf_routes.md)
