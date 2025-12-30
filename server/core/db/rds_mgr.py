import redis
from gevent import Timeout

rds = redis.Redis(
    host='mini',  # Redis服务器地址，默认为localhost
    port=6379,  # Redis服务器端口，默认为6379
    db=0,  # 使用的数据库编号，默认为0
    password=None,  # 如果Redis设置了密码，则在这里填写
    socket_connect_timeout=5,  # 连接超时时间（秒）
    socket_timeout=5,  # 操作超时时间（秒）
    retry_on_timeout=True,  # 超时后重试
    # decode_responses=True  # 是否将返回的数据自动解码为字符串
)


def _safe_redis_operation(operation, timeout=3.0):
    """安全执行 Redis 操作，带超时保护"""
    try:
        with Timeout(timeout):
            return operation()
    except Timeout:
        raise redis.TimeoutError(f"Redis operation timeout after {timeout} seconds")
    except Exception as e:
        raise


def get_str(key) -> str:
    v = rds.get(key)
    if v is None:
        return ''
    return v.decode('utf-8')


def get(key):
    """获取 Redis 键值，带超时保护"""
    return _safe_redis_operation(lambda: rds.get(key), timeout=3.0)


def set(key, value):
    """设置 Redis 键值，带超时保护"""
    return _safe_redis_operation(lambda: rds.set(key, value), timeout=3.0)


def append_value(key, value):
    rds.append(key, value)


def exists(key):
    return rds.exists(key)


def llen(key):
    """
    获取列表长度
    :param key: Redis键名
    :return: 列表长度
    """
    return rds.llen(key)


def lrange(key, start, end):
    """
    获取列表指定范围的数据
    :param key: Redis键名
    :param start: 起始索引 include
    :param end: 结束索引 include
    :return: 列表数据
    """
    data = rds.lrange(key, start, end)
    return [item.decode('utf-8') for item in data]


def lpush(key, value):
    """
    在列表头部插入数据
    :param key: Redis键名
    :param value: 要插入的值
    :return: 插入后列表的长度
    """
    return rds.lpush(key, value)


def rpush(key, value):
    """
    在列表尾部插入数据
    :param key: Redis键名
    :param value: 要插入的值
    :return: 插入后列表的长度
    """
    return rds.rpush(key, value)
