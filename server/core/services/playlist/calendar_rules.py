"""Canonical Shanghai scheduling rules shared by storage, calendars and playback."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta
import math
import json
import pytz
from apscheduler.triggers.cron import CronTrigger
from core.services.playlist.constants import DEVICE_TYPES

TZ = pytz.timezone('Asia/Shanghai')
RUNTIME_FIELDS = {'isPlaying', 'current_index', 'pre_index', 'in_pre_files',
                  'play_in_pre_files', 'play_pre_index', 'duration_timer_at', 'file_timer_at'}


def cron_trigger(expression):
    from core.utils import convert_standard_cron_weekday_to_apscheduler
    parts = expression.strip().split()
    if len(parts) == 5:
        minute, hour, day, month, weekday = parts
        second = '0'
    elif len(parts) == 6:
        second, minute, hour, day, month, weekday = parts
    else:
        raise ValueError('cron 必须包含 5 或 6 个字段')
    return CronTrigger(second=second, minute=minute, hour=hour, day=day, month=month,
                       day_of_week=convert_standard_cron_weekday_to_apscheduler(weekday), timezone=TZ)


def device_key(device):
    device = device or {}
    kind = device.get('type') or 'dlna'
    identity = device.get('did') if kind == 'mi' else device.get('address')
    if identity is None or not str(identity).strip():
        return None
    return json.dumps([kind, str(identity).strip()], ensure_ascii=False, separators=(',', ':'))


def playback_length(row, weekday):
    duration = row.get('schedule', {}).get('duration', 0) or 0
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0:
        raise ValueError('持续时间必须是非负分钟数')
    if duration > 0:
        return float(duration) * 60
    pre = row.get('pre_list', []) if row.get('mode') == 'calendar' else row.get('pre_lists', [[] for _ in range(7)])[weekday]
    items = pre + row.get('playlist', [])
    if not items:
        return None
    lengths = [item.get('duration') for item in items]
    if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or n <= 0 for n in lengths):
        return None
    return float(sum(lengths))


def normalize(raw, previous=None, *, importing=False):
    previous = previous or {}
    row = deepcopy(previous)
    row.update(deepcopy(raw))
    schedule = {**previous.get('schedule', {}), **raw.get('schedule', {})}
    supplied_status = raw.get('status')
    supplied_enabled = raw.get('schedule', {}).get('enabled')
    status = supplied_status if supplied_status is not None else supplied_enabled
    if status is None:
        status = previous.get('status', schedule.get('enabled', 0))
    if type(status) is not int or status not in (0, 1):
        raise ValueError('status 必须是整数 0 或 1')
    schedule.update(enabled=status, duration=schedule.get('duration', 0) or 0)
    row.update(mode=row.get('mode', 'weekly'), status=status, schedule=schedule)
    if row['mode'] not in ('weekly', 'calendar'):
        raise ValueError('不支持的播放列表模式')
    if not isinstance(row.get('playlist', []), list):
        raise ValueError('playlist 必须是数组')
    row.setdefault('pre_lists', [[] for _ in range(7)])
    if not isinstance(row['pre_lists'], list) or len(row['pre_lists']) != 7 or any(not isinstance(v, list) for v in row['pre_lists']):
        raise ValueError('pre_lists 必须是 7 天数组')
    row['device_key'] = device_key(row.get('device'))
    if row['mode'] == 'calendar':
        if not isinstance(row.get('pre_list', []), list):
            raise ValueError('pre_list 必须是数组')
        try:
            start = date.fromisoformat(row['start_date'])
            end = date.fromisoformat(row['end_date'])
            clock = time.fromisoformat(row['start_time'])
            if clock.tzinfo or start > end or end == date.max:
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise ValueError('calendar 需要有效起止日期和本地开始时间') from None
        row['start_time'] = clock.strftime('%H:%M:%S')
        row['length_seconds'] = playback_length(row, 0)
        if status and start < end and row['length_seconds'] is not None and row['length_seconds'] > 86400:
            raise ValueError('calendar 每日播放不能与自身次日排期重叠')
        device = row.get('device') or {}
        if status and (not row['device_key'] or not str(device.get('address') or '').strip()
                       or (device.get('type') or 'dlna') not in DEVICE_TYPES or row['length_seconds'] is None):
            raise ValueError('启用 calendar 前需要设备和完整曲目时长，或设置持续时间')
    else:
        expression = schedule.get('cron', '').strip()
        row.update(start_date='1970-01-01', end_date='2099-12-31', start_time=None)
        if expression:
            cron_trigger(expression)
            parts = expression.split()
            fields = ['0', *parts[:2]] if len(parts) == 5 else parts[:3]
            if all(v.isdigit() for v in fields):
                row['start_time'] = time(int(fields[2]), int(fields[1]), int(fields[0])).strftime('%H:%M:%S')
        row['weekday_lengths'] = [playback_length(row, d) for d in range(7)]
        # A single value is only meaningful if every weekday has the same length.
        row['length_seconds'] = row['weekday_lengths'][0] if len(set(row['weekday_lengths'])) == 1 else None
    return row


def occurrences(row, lower, upper):
    """Starts in [lower, upper); callers extend lower for cross-day occupancy."""
    if not row.get('status'):
        return
    if row['mode'] == 'calendar':
        day = max(date.fromisoformat(row['start_date']), lower.date())
        end = min(date.fromisoformat(row['end_date']), upper.date())
        clock = time.fromisoformat(row['start_time'])
        while day <= end:
            start = TZ.localize(datetime.combine(day, clock))
            if lower <= start < upper:
                yield start
            day += timedelta(days=1)
    else:
        if not row['schedule'].get('cron', '').strip():
            return
        # Date columns bound cron expansion as well as the DB candidate query.
        if row.get('start_date'):
            lower = max(lower, TZ.localize(datetime.combine(date.fromisoformat(row['start_date']), time.min)))
        if row.get('end_date'):
            upper = min(upper, TZ.localize(datetime.combine(date.fromisoformat(row['end_date']) + timedelta(days=1), time.min)))
        if lower >= upper:
            return
        trigger = cron_trigger(row['schedule']['cron'])
        start = trigger.get_next_fire_time(None, lower)
        count = 0
        while start is not None and start < upper:
            yield start
            count += 1
            if count > 100000:
                raise ValueError('该 cron 在检查区间内过于密集，请缩小日期范围或降低触发频率')
            start = trigger.get_next_fire_time(start, start + timedelta(microseconds=1))


def validate_conflicts(collection):
    enabled = [v for v in collection.values() if v.get('status')]
    for calendar in enabled:
        if calendar['mode'] != 'calendar':
            continue
        for other in enabled:
            if other['id'] == calendar['id'] or other.get('device_key') != calendar['device_key']:
                continue
            lengths = [playback_length(other, d) for d in range(7)]
            known = [v for v in lengths if v is not None]
            # Unknown weekly durations cannot establish a safe shared-device schedule.
            if other['mode'] == 'weekly' and other['schedule'].get('cron'):
                weekday_field = next(f for f in cron_trigger(other['schedule']['cron']).fields if f.name == 'day_of_week')
                monday = datetime(2026, 1, 5)
                if any(length is None and weekday_field.get_next_value(monday + timedelta(days=d)) == d
                       for d, length in enumerate(lengths)):
                    raise ValueError('同设备 weekly 存在未知曲目时长，请先补齐时长或设置持续时间')
            longest = max(known, default=0)
            lower = TZ.localize(datetime.combine(date.fromisoformat(calendar['start_date']), time.min))
            upper = TZ.localize(datetime.combine(date.fromisoformat(calendar['end_date']) + timedelta(days=1), time.min))
            for start in occurrences(calendar, lower, upper):
                finish = start + timedelta(seconds=calendar['length_seconds'])
                for peer in occurrences(other, start - timedelta(seconds=longest), finish):
                    length = playback_length(other, peer.weekday())
                    if length is None:
                        raise ValueError(f"{other.get('name', other['id'])} 的曲目时长未知，无法确认设备档期")
                    if peer + timedelta(seconds=length) > start:
                        raise ValueError(f"同设备播放时间重叠：{calendar.get('name', calendar['id'])} / {other.get('name', other['id'])}，{start.isoformat()}")


def calendar_range(start_date, end_date):
    try:
        first, last = date.fromisoformat(start_date), date.fromisoformat(end_date)
        if not 1 <= (last - first).days + 1 <= 62 or last == date.max:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('日历查询范围必须为有效日期且在 1–62 天内') from None
    return (TZ.localize(datetime.combine(first, time.min)),
            TZ.localize(datetime.combine(last + timedelta(days=1), time.min)))


def calendar_events(collection, start_date, end_date):
    """Render persisted date/time columns; cron is intentionally ignored here."""
    lower, upper = calendar_range(start_date, end_date)
    events = []
    for row in collection.values():
        if not row.get('status') or not row.get('start_time'):
            continue
        clock = time.fromisoformat(row['start_time'])
        lengths = row.get('weekday_lengths')
        if row.get('mode') != 'weekly' or not isinstance(lengths, list) or len(lengths) != 7:
            lengths = [row.get('length_seconds')] * 7
        longest = max((length or 0 for length in lengths), default=0)
        day = max(date.fromisoformat(row['start_date']), (lower - timedelta(seconds=longest)).date())
        final_day = min(date.fromisoformat(row['end_date']), (upper - timedelta(microseconds=1)).date())
        device = {key: (row.get('device') or {}).get(key) for key in ('type', 'address', 'did', 'name')}
        while day <= final_day:
            start = TZ.localize(datetime.combine(day, clock))
            length = lengths[day.weekday()]
            finish = start + timedelta(seconds=length or 0)
            if start < upper and ((length is None and start >= lower) or (length is not None and finish > lower)):
                events.append({'id': row['id'], 'name': row.get('name', ''), 'mode': row['mode'],
                    'start': start.isoformat(), 'end': finish.isoformat() if length is not None else None,
                    'length_seconds': length, 'device_key': row.get('device_key'),
                    'device': device, 'occurrence_count': 1})
            day += timedelta(days=1)
    return sorted(events, key=lambda event: event['start'])
