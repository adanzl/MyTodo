import redis

rds = redis.Redis(
    host='192.168.50.171',  # Redis服务器地址，默认为localhost
    port=6379,  # Redis服务器端口，默认为6379
    db=0,  # 使用的数据库编号，默认为0
    password=None,  # 如果Redis设置了密码，则在这里填写
    # decode_responses=True  # 是否将返回的数据自动解码为字符串
)


def get_str(key) -> str:
    v = rds.get(key)
    if v is None:
        return ''
    return rds.get(key).decode('utf-8')


def get(key):
    return rds.get(key)


def set(key, value):
    rds.set(key, value)


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
    :param start: 起始索引
    :param end: 结束索引
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
