"""Redis 访问封装（带 gevent 超时保护）。

该模块提供一组轻量函数用于：
- 获取/设置简单 key-value；
- 操作列表（lrange/lpush/rpush/llen）；
- 操作 Hash（hset/hget/hgetall/hdel/hlen）；  # cSpell: disable-line
并通过 `gevent.Timeout` 为部分操作提供超时保护，避免阻塞主 greenlet。

当未配置 Redis（`REDIS_ENABLED=false` 或 `REDIS_HOST` 为空）或连接失败时，
自动降级为本地 JSON 文件存储（默认 `rds_local.json`）。
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Optional

import redis
from gevent import Timeout

from core.config import app_logger

log = app_logger

_DEFAULT_LOCAL_FILE = 'rds_local.json'


def _redis_enabled_by_config() -> bool:
    """根据环境变量判断是否应尝试连接 Redis。"""
    enabled = os.environ.get('REDIS_ENABLED', '').strip().lower()
    if enabled in ('0', 'false', 'no', 'off'):
        return False
    if enabled in ('1', 'true', 'yes', 'on'):
        return True
    host = os.environ.get('REDIS_HOST', 'localhost').strip()
    return bool(host)


def _local_file_path() -> str:
    return os.environ.get('RDS_LOCAL_FILE', _DEFAULT_LOCAL_FILE)


def _to_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if value is None:
        return b''
    return str(value).encode('utf-8')


def _to_str(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode('utf-8')
    if value is None:
        return ''
    return str(value)


class _LocalJsonStore:
    """用单个 JSON 文件模拟 Redis 的 string / list / hash 操作。"""

    def __init__(self, path: str):
        self._path = path
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, Any]] = {
            'strings': {},
            'lists': {},
            'hashes': {},
        }
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            log.warning('Failed to load local Redis fallback file %s: %s', self._path, e)
            return
        if isinstance(loaded, dict):
            for bucket in ('strings', 'lists', 'hashes'):
                if isinstance(loaded.get(bucket), dict):
                    self._data[bucket] = loaded[bucket]

    def _persist(self) -> None:
        directory = os.path.dirname(os.path.abspath(self._path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = f'{self._path}.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._path)

    @staticmethod
    def _list_slice(items: list[str], start: int, end: int) -> list[str]:
        n = len(items)
        if n == 0:
            return []
        if start < 0:
            start = n + start
        if end < 0:
            end = n + end
        start = max(0, start)
        end = min(n - 1, end)
        if start > end:
            return []
        return items[start:end + 1]

    def get(self, key: str):
        with self._lock:
            value = self._data['strings'].get(key)
            if value is None:
                return None
            return _to_bytes(value)

    def set(self, key: str, value) -> bool:
        with self._lock:
            self._data['strings'][key] = _to_str(value)
            self._persist()
            return True

    def append_value(self, key: str, value) -> int:
        with self._lock:
            current = self._data['strings'].get(key, '')
            new_value = _to_str(current) + _to_str(value)
            self._data['strings'][key] = new_value
            self._persist()
            return len(new_value)

    def exists(self, key: str) -> int:
        with self._lock:
            if key in self._data['strings'] or key in self._data['lists'] or key in self._data['hashes']:
                return 1
            return 0

    def llen(self, key: str) -> int:
        with self._lock:
            return len(self._data['lists'].get(key, []))

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        with self._lock:
            items = list(self._data['lists'].get(key, []))
            return self._list_slice(items, start, end)

    def lpush(self, key: str, value) -> int:
        with self._lock:
            items = self._data['lists'].setdefault(key, [])
            items.insert(0, _to_str(value))
            self._persist()
            return len(items)

    def rpush(self, key: str, value) -> int:
        with self._lock:
            items = self._data['lists'].setdefault(key, [])
            items.append(_to_str(value))
            self._persist()
            return len(items)

    def hset(self, key: str, field: str, value) -> int:
        with self._lock:
            bucket = self._data['hashes'].setdefault(key, {})
            is_new = field not in bucket
            bucket[field] = _to_str(value)
            self._persist()
            return 1 if is_new else 0

    def hget(self, key: str, field: str):
        with self._lock:
            bucket = self._data['hashes'].get(key, {})
            value = bucket.get(field)
            if value is None:
                return None
            return _to_bytes(value)

    def hgetall(self, key: str) -> dict[str, str]:
        with self._lock:
            bucket = self._data['hashes'].get(key, {})
            return {str(k): _to_str(v) for k, v in bucket.items()}

    def hdel(self, key: str, *fields) -> int:
        with self._lock:
            bucket = self._data['hashes'].get(key)
            if not bucket:
                return 0
            removed = 0
            for field in fields:
                if field in bucket:
                    del bucket[field]
                    removed += 1
            if not bucket:
                self._data['hashes'].pop(key, None)
            if removed:
                self._persist()
            return removed

    def hlen(self, key: str) -> int:
        with self._lock:
            return len(self._data['hashes'].get(key, {}))


def _create_redis_client() -> redis.Redis:
    return redis.Redis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        db=int(os.environ.get('REDIS_DB', 0)),
        password=os.environ.get('REDIS_PASSWORD') or None,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def _init_storage() -> tuple[Optional[redis.Redis], Optional[_LocalJsonStore], bool]:
    if not _redis_enabled_by_config():
        local_store = _LocalJsonStore(_local_file_path())
        log.info('Redis disabled or not configured, using local JSON fallback: %s', local_store._path)
        return None, local_store, True

    client = _create_redis_client()
    try:
        client.ping()
        log.info(
            'Redis connected: %s:%s/%s',
            os.environ.get('REDIS_HOST', 'localhost'),
            os.environ.get('REDIS_PORT', 6379),
            os.environ.get('REDIS_DB', 0),
        )
        return client, None, False
    except redis.RedisError as e:
        local_store = _LocalJsonStore(_local_file_path())
        log.warning('Redis unavailable (%s), falling back to local JSON: %s', e, local_store._path)
        return None, local_store, True


rds, _local_store, is_local_fallback = _init_storage()


def _safe_redis_operation(operation, timeout: float = 3.0):
    """安全执行 Redis 操作，带超时保护。"""
    try:
        with Timeout(timeout):
            return operation()
    except Timeout:
        raise redis.TimeoutError(f"Redis operation timeout after {timeout} seconds")


def get_str(key: str) -> str:
    """获取字符串值（bytes -> str），不存在时返回空字符串。"""
    if _local_store is not None:
        return _to_str(_local_store.get(key))
    v = rds.get(key)  # pyright: ignore[reportOptionalMemberAccess]
    if v is None:
        return ''
    return v.decode('utf-8')  # pyright: ignore[reportAttributeAccessIssue]


def get(key: str):
    """获取 Redis 键值（带超时保护）。"""
    if _local_store is not None:
        return _local_store.get(key)
    return _safe_redis_operation(lambda: rds.get(key), timeout=3.0)  # pyright: ignore[reportOptionalMemberAccess]


def set(key: str, value) -> bool:
    """设置 Redis 键值（带超时保护）。"""
    if _local_store is not None:
        return _local_store.set(key, value)
    return _safe_redis_operation(lambda: rds.set(key, value), timeout=3.0)  # pyright: ignore[reportReturnType, reportOptionalMemberAccess]


def append_value(key: str, value) -> int:
    """向字符串 key 追加内容。"""
    if _local_store is not None:
        return _local_store.append_value(key, value)
    return rds.append(key, value)  # pyright: ignore[reportReturnType, reportOptionalMemberAccess]


def exists(key: str) -> int:
    """判断 key 是否存在。"""
    if _local_store is not None:
        return _local_store.exists(key)
    return rds.exists(key)  # pyright: ignore[reportReturnType, reportOptionalMemberAccess]


def llen(key: str) -> int:
    """获取列表长度。"""
    if _local_store is not None:
        return _local_store.llen(key)
    return rds.llen(key)  # pyright: ignore[reportReturnType, reportOptionalMemberAccess]


def lrange(key: str, start: int, end: int) -> list[str]:
    """获取列表指定范围的数据（bytes -> str）。"""
    if _local_store is not None:
        return _local_store.lrange(key, start, end)
    data = rds.lrange(key, start, end)  # pyright: ignore[reportReturnType, reportOptionalMemberAccess]
    return [item.decode('utf-8') for item in data]  # pyright: ignore[reportGeneralTypeIssues]


def lpush(key: str, value) -> int:
    """在列表头部插入数据。"""
    if _local_store is not None:
        return _local_store.lpush(key, value)
    return rds.lpush(key, value)  # pyright: ignore[reportReturnType, reportOptionalMemberAccess]


def rpush(key: str, value) -> int:
    """在列表尾部插入数据。"""
    if _local_store is not None:
        return _local_store.rpush(key, value)
    return rds.rpush(key, value)  # pyright: ignore[reportReturnType, reportOptionalMemberAccess]


def hset(key: str, field: str, value) -> int:
    """设置 Hash 字段的值（带超时保护）。"""
    if _local_store is not None:
        return _local_store.hset(key, field, value)
    return _safe_redis_operation(lambda: rds.hset(key, field, value), timeout=3.0)  # pyright: ignore[reportReturnType, reportOptionalMemberAccess]


def hget(key: str, field: str):
    """获取 Hash 字段的值（带超时保护）。"""
    if _local_store is not None:
        return _local_store.hget(key, field)
    return _safe_redis_operation(lambda: rds.hget(key, field), timeout=3.0)  # pyright: ignore[reportOptionalMemberAccess]


def hgetall(key: str) -> dict:
    """获取 Hash 所有字段和值（带超时保护）。"""
    if _local_store is not None:
        return _local_store.hgetall(key)
    result = _safe_redis_operation(lambda: rds.hgetall(key), timeout=3.0)  # pyright: ignore[reportOptionalMemberAccess]
    if result is None:
        return {}
    return {
        k.decode('utf-8') if isinstance(k, bytes) else k: v.decode('utf-8') if isinstance(v, bytes) else v
        for k, v in result.items()  # pyright: ignore[reportAttributeAccessIssue]
    }


def hdel(key: str, *fields) -> int:
    """删除 Hash 中的一个或多个字段（带超时保护）。"""
    if _local_store is not None:
        return _local_store.hdel(key, *fields)
    return _safe_redis_operation(lambda: rds.hdel(key, *fields), timeout=3.0)  # pyright: ignore[reportReturnType, reportOptionalMemberAccess]


def hlen(key: str) -> int:
    """获取 Hash 字段数量（带超时保护）。"""
    if _local_store is not None:
        return _local_store.hlen(key)
    return _safe_redis_operation(lambda: rds.hlen(key), timeout=3.0)  # pyright: ignore[reportReturnType, reportOptionalMemberAccess]
