"""Redis 访问封装（带 gevent 超时保护）。

该模块提供一组轻量函数用于：
- 获取/设置简单 key-value；
- 操作列表（lrange/lpush/rpush/llen）；
并通过 `gevent.Timeout` 为部分操作提供超时保护，避免阻塞主 greenlet。

注意：当前 Redis 连接参数为静态配置（host/port/db），如需环境化可在后续收敛到 `core.config`。
"""

import os
import redis
from gevent import Timeout

rds = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),  # Redis服务器地址，默认为localhost
    port=int(os.environ.get('REDIS_PORT', 6379)),  # Redis服务器端口，默认为6379
    db=int(os.environ.get('REDIS_DB', 0)),  # 使用的数据库编号，默认为0
    password=None,  # 如果Redis设置了密码，则在这里填写
    socket_connect_timeout=5,  # 连接超时时间（秒）
    socket_timeout=5,  # 操作超时时间（秒）
    # decode_responses=True  # 是否将返回的数据自动解码为字符串
)


def _safe_redis_operation(operation, timeout: float = 3.0):
    """安全执行 Redis 操作，带超时保护。

    Args:
        operation: 一个无参可调用对象，用于实际执行 Redis 调用。
        timeout (float): 超时秒数。

    Returns:
        Any: operation 的返回值。

    Raises:
        redis.TimeoutError: 当 gevent 超时触发。
        Exception: 透传 operation 抛出的异常。
    """
    try:
        with Timeout(timeout):
            return operation()
    except Timeout:
        raise redis.TimeoutError(f"Redis operation timeout after {timeout} seconds")


def get_str(key: str) -> str:
    """获取字符串值（bytes -> str），不存在时返回空字符串。"""
    v = rds.get(key)
    if v is None:
        return ''
    return v.decode('utf-8')  # pyright: ignore[reportAttributeAccessIssue]


def get(key: str):
    """获取 Redis 键值（带超时保护）。"""
    return _safe_redis_operation(lambda: rds.get(key), timeout=3.0)


def set(key: str, value) -> bool:
    """设置 Redis 键值（带超时保护）。"""
    return _safe_redis_operation(lambda: rds.set(key, value), timeout=3.0)  # pyright: ignore[reportReturnType]


def append_value(key: str, value) -> int:
    """向字符串 key 追加内容。"""
    return rds.append(key, value)  # pyright: ignore[reportReturnType]


def exists(key: str) -> int:
    """判断 key 是否存在。"""
    return rds.exists(key)  # pyright: ignore[reportReturnType]


def llen(key: str) -> int:
    """获取列表长度。"""
    return rds.llen(key)  # pyright: ignore[reportReturnType]


def lrange(key: str, start: int, end: int) -> list[str]:
    """获取列表指定范围的数据（bytes -> str）。"""
    data = rds.lrange(key, start, end)  # pyright: ignore[reportReturnType]
    return [item.decode('utf-8') for item in data]  # pyright: ignore[reportGeneralTypeIssues]


def lpush(key: str, value) -> int:
    """在列表头部插入数据。"""
    return rds.lpush(key, value)  # pyright: ignore[reportReturnType]


def rpush(key: str, value) -> int:
    """在列表尾部插入数据。"""
    return rds.rpush(key, value)  # pyright: ignore[reportReturnType]


def hset(key: str, field: str, value) -> int:
    """设置 Hash 字段的值（带超时保护）。"""
    return _safe_redis_operation(lambda: rds.hset(key, field, value), timeout=3.0)  # pyright: ignore[reportReturnType]


def hget(key: str, field: str):
    """获取 Hash 字段的值（带超时保护）。"""
    return _safe_redis_operation(lambda: rds.hget(key, field), timeout=3.0)


def hgetall(key: str) -> dict:
    """获取 Hash 所有字段和值（带超时保护）。"""
    result = _safe_redis_operation(lambda: rds.hgetall(key), timeout=3.0)
    if result is None:
        return {}
    # 将 bytes key/value 转换为 str
    return {
        k.decode('utf-8') if isinstance(k, bytes) else k: v.decode('utf-8') if isinstance(v, bytes) else v
        for k, v in result.items()  # pyright: ignore[reportAttributeAccessIssue]
    }


def hdel(key: str, *fields) -> int:
    """删除 Hash 中的一个或多个字段（带超时保护）。"""
    return _safe_redis_operation(lambda: rds.hdel(key, *fields), timeout=3.0)  # pyright: ignore[reportReturnType]


def hlen(key: str) -> int:
    """获取 Hash 字段数量（带超时保护）。"""
    return _safe_redis_operation(lambda: rds.hlen(key), timeout=3.0)  # pyright: ignore[reportReturnType]
