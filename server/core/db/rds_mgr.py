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
