"""跨 Socket 的 AI 请求 phase 与回复快照（user + clientRequestId）。"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Optional

import core.db.rds_mgr as rds_mgr

TTL_SECONDS = 900

TERMINAL = frozenset({'done', 'cancelled', 'failed'})
RETRYABLE = frozenset({'failed', 'cancelled'})

_store_lock = threading.Lock()

# Redis 上单次 GET+校验+SETEX，避免多 worker / 多连接交错「读-改-写」。
_PHASE_TRANSITION_LUA = """
local raw = redis.call('GET', KEYS[1])
local current = nil
if raw then
  local ok, data = pcall(cjson.decode, raw)
  if ok and type(data) == 'table' and data['phase'] then
    current = data['phase']
  elseif not ok then
    current = raw
  end
end
local mode = ARGV[1]
local new_phase = ARGV[2]
local ttl = tonumber(ARGV[3])
local exp = tonumber(ARGV[4])
local allowed = cjson.decode(ARGV[5])

if mode == 'create' then
  if current ~= nil then return 0 end
else
  local ok_from = false
  for _, p in ipairs(allowed) do
    if p == current then ok_from = true break end
  end
  if not ok_from then return 0 end
end

local rec = {}
if raw then
  local ok, data = pcall(cjson.decode, raw)
  if ok and type(data) == 'table' then rec = data end
end
rec['phase'] = new_phase
rec['exp'] = exp
if new_phase == 'accepted' and (current == 'failed' or current == 'cancelled') then
  rec['error'] = nil
  rec['reply_text'] = nil
  local attempt = tonumber(rec['attempt']) or 0
  rec['attempt'] = attempt + 1
end
redis.call('SETEX', KEYS[1], ttl, cjson.encode(rec))
return 1
"""


def _key(user: str, request_id: str) -> str:
    u = (user or 'user').strip().replace(':', '_') or 'user'
    return f"chat:req:{u}:{request_id}"


def _parse_raw(raw: str) -> Optional[dict[str, Any]]:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {'phase': raw, 'exp': time.time() + TTL_SECONDS}
    if not isinstance(data, dict):
        return None
    exp = float(data.get('exp') or 0)
    if exp and time.time() > exp:
        return None
    return data


def _load_unlocked(user: str, request_id: str) -> Optional[dict[str, Any]]:
    raw = rds_mgr.get_str(_key(user, request_id))
    return _parse_raw(raw)


def _save_unlocked(user: str, request_id: str, data: dict[str, Any]) -> None:
    data = {**data, 'exp': time.time() + TTL_SECONDS}
    payload = json.dumps(data, ensure_ascii=False)
    rds_mgr.setex(_key(user, request_id), TTL_SECONDS, payload)


def get_record(user: str, request_id: str) -> Optional[dict[str, Any]]:
    if not request_id:
        return None
    with _store_lock:
        return _load_unlocked(user, request_id)


def get_attempt(user: str, request_id: str) -> int:
    rec = get_record(user, request_id)
    if not rec:
        return 0
    return int(rec.get('attempt') or 0)


def matches_attempt(user: str, request_id: str, attempt: int) -> bool:
    if not request_id:
        return True
    return get_attempt(user, request_id) == int(attempt or 0)


def get_phase(user: str, request_id: str) -> str | None:
    rec = get_record(user, request_id)
    if not rec:
        return None
    phase = rec.get('phase')
    return str(phase) if phase else None


def set_phase(user: str, request_id: str, phase: str) -> None:
    if not request_id or not phase:
        return
    with _store_lock:
        rec = _load_unlocked(user, request_id) or {}
        rec['phase'] = phase
        _save_unlocked(user, request_id, rec)


def _try_transition_locked(
    user: str,
    request_id: str,
    allowed_from: frozenset[str] | None,
    new_phase: str,
) -> bool:
    rec = _load_unlocked(user, request_id)
    current = rec.get('phase') if rec else None
    if allowed_from is None:
        if current is not None:
            return False
        rec = {}
    elif current not in allowed_from:
        return False
    else:
        rec = rec or {}
    rec['phase'] = new_phase
    if new_phase == 'accepted' and current in RETRYABLE:
        rec.pop('error', None)
        rec.pop('reply_text', None)
        rec['attempt'] = int(rec.get('attempt') or 0) + 1
    _save_unlocked(user, request_id, rec)
    return True


def try_transition(
    user: str,
    request_id: str,
    allowed_from: frozenset[str] | None,
    new_phase: str,
) -> bool:
    """在共享存储上原子转换 phase。allowed_from=None 表示仅允许从「无记录」创建。"""
    if not request_id or not new_phase:
        return False
    key = _key(user, request_id)
    exp = time.time() + TTL_SECONDS
    mode = 'create' if allowed_from is None else 'transition'
    allowed_json = json.dumps(
        sorted(allowed_from) if allowed_from is not None else [],
        ensure_ascii=False,
    )
    redis_ok = rds_mgr.eval_lua(
        _PHASE_TRANSITION_LUA,
        [key],
        [mode, new_phase, str(TTL_SECONDS), str(exp), allowed_json],
    )
    if redis_ok is not None:
        return int(redis_ok) == 1
    with _store_lock:
        return _try_transition_locked(user, request_id, allowed_from, new_phase)


def append_reply_text(
    user: str,
    request_id: str,
    chunk: str,
    attempt: int = 0,
) -> bool:
    if not request_id or not chunk:
        return False
    with _store_lock:
        rec = _load_unlocked(user, request_id) or {'phase': 'ai'}
        if int(rec.get('attempt') or 0) != int(attempt or 0):
            return False
        prev = rec.get('reply_text') or ''
        rec['reply_text'] = prev + chunk
        _save_unlocked(user, request_id, rec)
        return True


def mark_failed(
    user: str,
    request_id: str,
    error: str,
    attempt: int = 0,
) -> bool:
    if not request_id:
        return False
    with _store_lock:
        rec = _load_unlocked(user, request_id) or {}
        if rec.get('phase') and int(rec.get('attempt') or 0) != int(attempt or 0):
            return False
        rec['phase'] = 'failed'
        rec['error'] = (error or '')[:2000]
        _save_unlocked(user, request_id, rec)
        return True


def mark_done(user: str, request_id: str, attempt: int = 0) -> bool:
    if not request_id:
        return False
    with _store_lock:
        rec = _load_unlocked(user, request_id)
        if not rec:
            return False
        if rec.get('phase') == 'cancelled':
            return False
        if int(rec.get('attempt') or 0) != int(attempt or 0):
            return False
        rec['phase'] = 'done'
        _save_unlocked(user, request_id, rec)
        return True


def record_to_client_item(request_id: str, rec: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not rec:
        return {'clientRequestId': request_id, 'phase': None}
    item: dict[str, Any] = {
        'clientRequestId': request_id,
        'phase': rec.get('phase'),
    }
    reply = rec.get('reply_text')
    if isinstance(reply, str) and reply:
        item['replyText'] = reply
    err = rec.get('error')
    if isinstance(err, str) and err:
        item['errorMessage'] = err
    item['attempt'] = int(rec.get('attempt') or 0)
    return item
