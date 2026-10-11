"""请求路径的鉴权策略。

抽成独立的纯字符串模块，原因有二：

1. `_is_whitelisted` 原本是 `create_app()` 里的闭包，无法单独测试；
2. 需要明确表达「有些接口必须始终要求 JWT」，而不是靠环境变量开关决定。

关于路径形态：WSGI 通过 `DispatcherMiddleware` 把 app 挂在 `/api` 下，此时
`/api` 会被放进 `SCRIPT_NAME`，因此 **`request.path` 是 `/pic/delete` 而不是
`/api/pic/delete`**（已实测）。两种形态都做归一化，避免将来换挂载方式时静默失效。

注意：放一个接口进 `ALWAYS_AUTH_PATHS` 的前提是**凭证能随请求携带**。
`fetch`/`axios` 可以带 `Authorization` 头，所以 `/pic/delete`、`/pic/upload` 这类
可以要求鉴权；而 `/pic/view` 是被 `<img src>` 直接引用的，浏览器不会带 JWT，
必须留在白名单里，否则图片全部裂开。
"""

from __future__ import annotations

# 必须始终要求 JWT 的路径（归一化后的形态）。
# 不受 AUTH_WHITELIST_ALL_API 与 AUTH_API_WHITELIST* 影响。
ALWAYS_AUTH_PATHS: frozenset[str] = frozenset({
    # 列表类查询，历史上已单独移出白名单
    '/getAll',
    # 会真实删除磁盘文件：未鉴权时任何人只要知道文件名就能删图
    '/pic/delete',
    # 会写入磁盘：未鉴权时任何人都能上传（可能被用来塞满磁盘）
    '/pic/upload',
})


def normalize_path(path: str) -> str:
    """归一化请求路径：去掉可能的 `/api` 前缀与结尾斜杠。"""
    p = (path or '').strip()
    if not p:
        return '/'
    if p != '/':
        p = p.rstrip('/') or '/'
    if p == '/api':
        return '/'
    if p.startswith('/api/'):
        p = p[len('/api'):]
    return p


def always_requires_auth(path: str) -> bool:
    """该路径是否必须始终走 JWT 验证（不受全局白名单开关影响）。"""
    return normalize_path(path) in ALWAYS_AUTH_PATHS
