"""HTTP 子进程 worker：仅依赖 requests，避免 spawn 时加载 Flask/gevent 应用栈。"""


def http_request_worker(
    out_q: object,
    method: str,
    url: str,
    timeout: float,
    headers: dict[str, str] | None,
) -> None:
    import requests as req

    try:
        resp = req.request(method.upper(), url, timeout=timeout, headers=headers or {})
        out_q.put(("ok", resp.status_code, resp.content))  # type: ignore[union-attr]
    except Exception as exc:
        out_q.put(("err", str(exc)))  # type: ignore[union-attr]
