"""Redis 访问封装（带 gevent 超时保护）。

该模块提供一组轻量函数用于：
- 获取/设置简单 key-value；
- 操作列表（lrange/lpush/rpush/llen）；
并通过 `gevent.Timeout` 为部分操作提供超时保护，避免阻塞主 greenlet。

注意：当前 Redis 连接参数为静态配置（host/port/db），如需环境化可在后续收敛到 `core.config`。
"""

import redis
from gevent import Timeout

rds = redis.Redis(
    host='mini',  # Redis服务器地址，默认为localhost
    port=6379,  # Redis服务器端口，默认为6379
    db=0,  # 使用的数据库编号，默认为0
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
    return v.decode('utf-8')


def get(key: str):
    """获取 Redis 键值（带超时保护）。"""
    return _safe_redis_operation(lambda: rds.get(key), timeout=3.0)


def set(key: str, value) -> bool:
    """设置 Redis 键值（带超时保护）。"""
    return _safe_redis_operation(lambda: rds.set(key, value), timeout=3.0)


def append_value(key: str, value) -> int:
    """向字符串 key 追加内容。"""
    return rds.append(key, value)


def exists(key: str) -> int:
    """判断 key 是否存在。"""
    return rds.exists(key)


def llen(key: str) -> int:
    """获取列表长度。"""
    return rds.llen(key)


def lrange(key: str, start: int, end: int) -> list[str]:
    """获取列表指定范围的数据（bytes -> str）。"""
    data = rds.lrange(key, start, end)
    return [item.decode('utf-8') for item in data]


def lpush(key: str, value) -> int:
    """在列表头部插入数据。"""
    return rds.lpush(key, value)


def rpush(key: str, value) -> int:
    """在列表尾部插入数据。"""
    return rds.rpush(key, value)
