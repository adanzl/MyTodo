"""`ChatMgr` 的历史记录查询与导出单元测试。

覆盖：
- `get_messages` / `get_conversations`：单页查询、参数清洗、limit 收敛、错误语义；
- `collect_messages`：游标翻页拉全、早停、去重、上限；
- `export_messages` 及其私有纯函数：日期解析、过滤、CSV 生成。

Dify 的 `/messages` 只支持游标分页（`first_id` 指向更早的一页，页内按时间正序），
这里用假的 `AILocal.get_chat_messages` 复刻该语义。

日期按服务端本地时区解释，所以时间戳都用 `datetime` 反推，不写死绝对值。
"""

from datetime import datetime

import pytest
from flask import Response

from core.ai.ai_local import AILocal
from core.chat.chat_mgr import (
    DEFAULT_LIMIT,
    EXPORT_MAX_PAGES,
    EXPORT_PAGE_SIZE,
    MAX_LIMIT,
    ChatMgr,
)

T0 = 1759900000


def ts(text):
    """把 `YYYY-MM-DD HH:MM:SS` 按本地时区转成 epoch 秒，用于造数据。"""
    return int(datetime.strptime(text, '%Y-%m-%d %H:%M:%S').timestamp())


def make_messages(count):
    """按时间升序造 count 条消息。"""
    return [
        {'id': f'm{i:05d}', 'created_at': T0 + i * 60, 'query': f'q{i}', 'answer': f'a{i}'}
        for i in range(count)
    ]


def dify_page(all_messages, limit, first_id=None):
    """按 Dify 的语义切一页出来。"""
    end = len(all_messages)
    if first_id:
        end = [m['id'] for m in all_messages].index(first_id)
    start = max(0, end - limit)
    return {'has_more': start > 0, 'data': all_messages[start:end]}


def install_pager(monkeypatch, all_messages):
    """把 get_chat_messages 换成按游标翻页的假实现，并记录调用参数。"""
    calls = []

    def loader(conversation_id, limit, user, first_id=None):
        calls.append({'conversation_id': conversation_id, 'limit': limit,
                      'user': user, 'first_id': first_id})
        return dify_page(all_messages, limit, first_id)

    monkeypatch.setattr(AILocal, 'get_chat_messages', loader)
    return calls


@pytest.fixture
def mgr():
    return ChatMgr()


# ---------- get_messages ----------

def test_get_messages_ok(monkeypatch, mgr):
    payload = {"limit": 3, "has_more": True, "data": [{"id": "m1"}]}
    seen = {}

    def loader(conversation_id, limit, user, first_id=None):
        seen.update(conversation_id=conversation_id, limit=limit, user=user,
                    first_id=first_id)
        return payload

    monkeypatch.setattr(AILocal, 'get_chat_messages', loader)

    result = mgr.get_messages('c', '3', 'leo')

    assert result['code'] == 0
    assert result['data'] == payload
    # limit 已收敛成 int（字符串 '3' -> 3）
    assert seen == {'conversation_id': 'c', 'limit': 3, 'user': 'leo',
                    'first_id': None}


@pytest.mark.parametrize("raw_limit,expected", [
    (None, DEFAULT_LIMIT),   # 不传 -> 默认
    ("", DEFAULT_LIMIT),     # 空串 -> 默认
    ("abc", DEFAULT_LIMIT),  # 非法 -> 默认（否则会把 422 静默成 data:null）
    ("0", 1),                # 下界收敛
    ("-5", 1),
    (str(MAX_LIMIT + 899), MAX_LIMIT),  # 上界收敛（Dify 单页上限）
    ("50", 50),
    (3, 3),
])
def test_get_messages_limit_clamped(monkeypatch, mgr, raw_limit, expected):
    """与 get_conversations 一致：limit 必须先收敛再发给 Dify。

    不收敛的话，越界会被 Dify 422 拒绝，而 `AILocal.get_chat_messages` 会把它
    吞成 None，最终表现为 `code:0` + `data:null` —— 与「会话没有消息」无法区分。
    """
    seen = {}
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda c, limit, u, first_id=None: seen.update(limit=limit) or {})

    mgr.get_messages('c', raw_limit, 'leo')

    assert seen['limit'] == expected
    assert isinstance(seen['limit'], int)


def test_get_messages_first_id_forwarded(monkeypatch, mgr):
    seen = {}
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda c, limit, u, first_id=None: seen.update(first_id=first_id) or {})

    mgr.get_messages('c', None, 'leo', 'old-1')

    assert seen['first_id'] == 'old-1'


def test_get_messages_failure_is_silent_none(monkeypatch, mgr):
    """取数失败时保持 `code:0` + `data:null`（既有行为，不要改成报错）。"""
    monkeypatch.setattr(AILocal, 'get_chat_messages', lambda *a, **kw: None)

    result = mgr.get_messages('c', '3', 'leo')

    assert result['code'] == 0
    assert result['data'] is None


def test_get_messages_exception_becomes_err(monkeypatch, mgr):
    def boom(*a, **kw):
        raise RuntimeError('boom')

    monkeypatch.setattr(AILocal, 'get_chat_messages', boom)

    result = mgr.get_messages('c', '3', 'leo')

    assert result['code'] == -1
    assert 'boom' in result['msg']


# ---------- get_conversations ----------

def test_get_conversations_ok(monkeypatch, mgr):
    payload = {"limit": 20, "has_more": True, "data": [{"id": "conv-1"}]}
    seen = {}

    def loader(user, limit=None, last_id=None):
        seen.update(user=user, limit=limit, last_id=last_id)
        return payload

    monkeypatch.setattr(AILocal, 'get_conversations', loader)

    result = mgr.get_conversations('leo', 20)

    assert result['code'] == 0
    assert result['data'] == payload
    assert seen == {'user': 'leo', 'limit': 20, 'last_id': None}


@pytest.mark.parametrize('bad_user', [None, '', '   ', '\t'])
def test_get_conversations_requires_user(monkeypatch, mgr, bad_user):
    monkeypatch.setattr(AILocal, 'get_conversations',
                        lambda *a, **kw: pytest.fail('不应触发取数'))

    result = mgr.get_conversations(bad_user)

    assert result['code'] == -1
    assert result['msg'] == 'user is required'


def test_get_conversations_user_is_trimmed(monkeypatch, mgr):
    seen = {}
    monkeypatch.setattr(AILocal, 'get_conversations',
                        lambda user, limit=None, last_id=None: seen.update(user=user) or {})

    result = mgr.get_conversations('  leo  ')

    assert result['code'] == 0
    assert seen['user'] == 'leo'


def test_get_conversations_last_id_forwarded(monkeypatch, mgr):
    seen = {}
    monkeypatch.setattr(AILocal, 'get_conversations',
                        lambda user, limit=None, last_id=None: seen.update(last_id=last_id) or {})

    mgr.get_conversations('leo', None, 'conv-9')

    assert seen['last_id'] == 'conv-9'


@pytest.mark.parametrize('blank', ['', '   ', None])
def test_get_conversations_blank_last_id_becomes_none(monkeypatch, mgr, blank):
    seen = {}
    monkeypatch.setattr(AILocal, 'get_conversations',
                        lambda user, limit=None, last_id=None: seen.update(last_id=last_id) or {})

    mgr.get_conversations('leo', None, blank)

    assert seen['last_id'] is None


@pytest.mark.parametrize("raw_limit,expected", [
    (None, DEFAULT_LIMIT),   # 不传 -> 默认
    ("", DEFAULT_LIMIT),     # 空串 -> 默认
    ("abc", DEFAULT_LIMIT),  # 非法 -> 默认
    ("0", 1),                # 下界收敛
    ("-5", 1),
    (str(MAX_LIMIT + 899), MAX_LIMIT),  # 上界收敛（Dify 单页上限）
    ("50", 50),
])
def test_get_conversations_limit_clamped(monkeypatch, mgr, raw_limit, expected):
    seen = {}
    monkeypatch.setattr(AILocal, 'get_conversations',
                        lambda user, limit=None, last_id=None: seen.update(limit=limit) or {})

    mgr.get_conversations('leo', raw_limit)

    assert seen['limit'] == expected


def test_get_conversations_limit_already_valid(monkeypatch, mgr):
    seen = {}
    monkeypatch.setattr(AILocal, 'get_conversations',
                        lambda user, limit=None, last_id=None: seen.update(limit=limit) or {})

    mgr.get_conversations('leo', 20)

    assert seen['limit'] == 20


def test_get_conversations_error_propagates_upstream_message(monkeypatch, mgr):
    """上游错误要透出，不能被前端误判成「没有会话」。"""
    def boom(user, limit=None, last_id=None):
        raise RuntimeError('401 Client Error: UNAUTHORIZED')

    monkeypatch.setattr(AILocal, 'get_conversations', boom)

    result = mgr.get_conversations('leo')

    assert result['code'] == -1
    assert '401' in result['msg']


# ---------- collect_messages ----------

def test_collect_single_page(monkeypatch, mgr):
    messages = make_messages(7)
    install_pager(monkeypatch, messages)

    collected, truncated = mgr.collect_messages('conv-1', 'leo')

    assert [m['id'] for m in collected] == [m['id'] for m in messages]
    assert truncated is False


def test_collect_walks_all_pages_without_loss(monkeypatch, mgr):
    messages = make_messages(250)
    calls = install_pager(monkeypatch, messages)

    collected, truncated = mgr.collect_messages('conv-1', 'leo')

    assert len(collected) == 250
    assert truncated is False
    assert {m['id'] for m in collected} == {m['id'] for m in messages}
    assert len(calls) == 3
    # 第一页不带游标，之后用上一页最旧一条的 id
    assert calls[0]['first_id'] is None
    assert calls[1]['first_id'] == 'm00150'
    assert calls[2]['first_id'] == 'm00050'


def test_collect_forwards_conversation_user_and_limit(monkeypatch, mgr):
    calls = install_pager(monkeypatch, make_messages(5))

    mgr.collect_messages('conv-9', '灿灿')

    assert calls[0]['conversation_id'] == 'conv-9'
    assert calls[0]['user'] == '灿灿'
    assert calls[0]['limit'] == EXPORT_PAGE_SIZE


def test_collect_stops_early_before_start_date(monkeypatch, mgr):
    """起始日期作为下界：某页最旧一条已早于它就可以停，不用拉全。"""
    calls = install_pager(monkeypatch, make_messages(1000))
    stop_before = T0 + 650 * 60 + 30  # 落在 m00650 与 m00651 之间

    collected, truncated = mgr.collect_messages('conv-1', 'leo', stop_before=stop_before)

    # 页1 m0900-、页2 m0800-、页3 m0700-、页4 m0600-（含更早 -> 停）
    assert len(calls) == 4
    assert truncated is False
    assert len(collected) == 400
    kept = [m for m in collected if m['created_at'] >= stop_before]
    assert len(kept) == 349
    assert min(m['created_at'] for m in kept) == T0 + 651 * 60


def test_collect_keeps_messages_equal_to_boundary(monkeypatch, mgr):
    """下界是闭区间：正好等于 stop_before 的消息必须保留。"""
    messages = make_messages(100)
    install_pager(monkeypatch, messages)
    boundary = messages[50]['created_at']

    collected, _ = mgr.collect_messages('conv-1', 'leo', stop_before=boundary)

    assert boundary in {m['created_at'] for m in collected}


def test_collect_empty_conversation(monkeypatch, mgr):
    install_pager(monkeypatch, [])

    collected, truncated = mgr.collect_messages('conv-1', 'leo')

    assert collected == []
    assert truncated is False


def test_collect_dedupes_repeated_items(monkeypatch, mgr):
    """上游重复返回同一条时不能重复计入。"""
    messages = make_messages(150)

    def loader(conversation_id, limit, user, first_id=None):
        if first_id is None:
            return {'has_more': True, 'data': messages[100:150]}
        # 故意重复 messages[100]，并往前取
        return {'has_more': False, 'data': messages[50:101]}

    monkeypatch.setattr(AILocal, 'get_chat_messages', loader)

    collected, truncated = mgr.collect_messages('conv-1', 'leo')

    assert len(collected) == 100
    assert len({m['id'] for m in collected}) == 100
    assert truncated is False


def test_collect_stops_when_cursor_does_not_advance(monkeypatch, mgr):
    """has_more 恒真但游标不变时必须停，否则死循环。"""
    calls = []

    def loader(conversation_id, limit, user, first_id=None):
        calls.append(first_id)
        return {'has_more': True, 'data': [
            {'id': 'same', 'created_at': T0, 'query': 'x', 'answer': 'y'}]}

    monkeypatch.setattr(AILocal, 'get_chat_messages', loader)

    collected, _ = mgr.collect_messages('conv-1', 'leo')

    assert len(calls) <= 2
    assert len(collected) == 1


def test_collect_stops_when_has_more_but_no_id(monkeypatch, mgr):
    def loader(conversation_id, limit, user, first_id=None):
        return {'has_more': True, 'data': [{'created_at': T0, 'query': 'x'}]}

    monkeypatch.setattr(AILocal, 'get_chat_messages', loader)

    collected, truncated = mgr.collect_messages('conv-1', 'leo')

    assert len(collected) == 1
    assert truncated is False


def test_collect_raises_when_upstream_fails(monkeypatch, mgr):
    """`get_chat_messages` 吞异常返回 None 时，必须抛错而不是当成空结果。"""
    monkeypatch.setattr(AILocal, 'get_chat_messages', lambda *a, **kw: None)

    with pytest.raises(RuntimeError, match='获取会话消息失败'):
        mgr.collect_messages('conv-1', 'leo')


def test_collect_marks_truncated_when_pages_exhausted(monkeypatch, mgr):
    """翻页走满上限时如实标记 truncated，交由调用方决定怎么处理。"""
    all_messages = make_messages(100000)

    def loader(conversation_id, limit, user, first_id=None):
        return dify_page(all_messages, limit, first_id) | {'has_more': True}

    monkeypatch.setattr(AILocal, 'get_chat_messages', loader)

    collected, truncated = mgr.collect_messages('conv-1', 'leo')

    assert truncated is True
    assert len(collected) == EXPORT_PAGE_SIZE * EXPORT_MAX_PAGES


def test_collect_ignores_unparsable_created_at_for_early_stop(monkeypatch, mgr):
    """created_at 异常时不能因早停判断而中断，应继续翻页。"""
    calls = []

    def loader(conversation_id, limit, user, first_id=None):
        calls.append(first_id)
        if first_id is None:
            return {'has_more': True, 'data': [
                {'id': 'bad', 'created_at': 'abc'}, {'id': 'm2', 'created_at': T0}]}
        return {'has_more': False, 'data': [{'id': 'm1', 'created_at': T0 - 60}]}

    monkeypatch.setattr(AILocal, 'get_chat_messages', loader)

    collected, truncated = mgr.collect_messages('conv-1', 'leo', stop_before=T0 + 10)

    assert len(calls) == 2
    assert len(collected) == 3
    assert truncated is False


# ---------- _parse_date_range ----------
# 下面是纯函数，直接测边界比绕 export_messages 更清楚

def test_parse_date_range_empty_means_unbounded():
    assert ChatMgr._parse_date_range(None, None) == (None, None)
    assert ChatMgr._parse_date_range('', '') == (None, None)
    assert ChatMgr._parse_date_range('  ', '  ') == (None, None)


def test_parse_date_range_start_is_start_of_day():
    start_ts, end_ts = ChatMgr._parse_date_range('2026-10-08', None)

    assert start_ts == ts('2026-10-08 00:00:00')
    assert end_ts is None


def test_parse_date_range_end_is_end_of_day():
    """结束日期必须覆盖当天最后一秒，否则「含当天」会漏掉大部分数据。"""
    start_ts, end_ts = ChatMgr._parse_date_range(None, '2026-10-08')

    assert start_ts is None
    assert end_ts == ts('2026-10-08 23:59:59')


def test_parse_date_range_both():
    start_ts, end_ts = ChatMgr._parse_date_range('2026-10-01', '2026-10-08')

    assert start_ts == ts('2026-10-01 00:00:00')
    assert end_ts == ts('2026-10-08 23:59:59')


def test_parse_date_range_same_day_covers_whole_day():
    start_ts, end_ts = ChatMgr._parse_date_range('2026-10-08', '2026-10-08')

    assert start_ts < end_ts
    assert end_ts - start_ts >= 86399


def test_parse_date_range_start_after_end_raises():
    with pytest.raises(ValueError, match='开始日期不能晚于结束日期'):
        ChatMgr._parse_date_range('2026-10-09', '2026-10-08')


@pytest.mark.parametrize('bad', ['2026/10/08', '20261008', '2026-13-01', 'abc'])
def test_parse_date_range_bad_format_raises(bad):
    with pytest.raises(ValueError, match='日期格式'):
        ChatMgr._parse_date_range(bad, None)


# ---------- _format_ts ----------

def test_format_ts_ok():
    assert ChatMgr._format_ts(ts('2026-10-08 19:40:26')) == '2026-10-08 19:40:26'


def test_format_ts_accepts_numeric_string():
    assert ChatMgr._format_ts(str(ts('2026-10-08 19:40:26'))) == '2026-10-08 19:40:26'


@pytest.mark.parametrize('bad', [None, '', 'abc', '1.2.3'])
def test_format_ts_invalid_returns_dash(bad):
    assert ChatMgr._format_ts(bad) == '-'


# ---------- _filter_messages ----------

def test_filter_messages_includes_both_boundaries():
    start_ts, end_ts = ChatMgr._parse_date_range('2026-10-08', '2026-10-08')
    messages = [
        {'id': 'before', 'created_at': start_ts - 1},
        {'id': 'first', 'created_at': start_ts},
        {'id': 'last', 'created_at': end_ts},
        {'id': 'after', 'created_at': end_ts + 1},
    ]

    picked = ChatMgr._filter_messages(messages, start_ts, end_ts)

    assert [m['id'] for m in picked] == ['first', 'last']


def test_filter_messages_sorts_ascending():
    messages = [
        {'id': 'c', 'created_at': ts('2026-10-08 12:00:00')},
        {'id': 'a', 'created_at': ts('2026-10-08 10:00:00')},
        {'id': 'b', 'created_at': ts('2026-10-08 11:00:00')},
    ]

    assert [m['id'] for m in ChatMgr._filter_messages(messages)] == ['a', 'b', 'c']


def test_filter_messages_unbounded_keeps_all_valid():
    messages = [{'id': 'a', 'created_at': 1}, {'id': 'b', 'created_at': 2}]

    assert len(ChatMgr._filter_messages(messages)) == 2


@pytest.mark.parametrize('bad', [
    {'id': 'no-ts'},
    {'id': 'none', 'created_at': None},
    {'id': 'text', 'created_at': 'abc'},
    'not-a-dict',
])
def test_filter_messages_drops_unusable(bad):
    assert ChatMgr._filter_messages([bad]) == []


def test_filter_messages_handles_empty_and_none():
    assert ChatMgr._filter_messages([]) == []
    assert ChatMgr._filter_messages(None) == []


# ---------- _build_csv ----------

def test_build_csv_starts_with_bom_and_uses_crlf():
    csv_text = ChatMgr._build_csv([{'created_at': 1, 'query': 'q', 'answer': 'a'}], '昭昭')

    assert csv_text.startswith('\ufeff')
    assert '\r\n' in csv_text
    assert '\n' not in csv_text.replace('\r\n', '')


def test_build_csv_header_uses_user_label():
    csv_text = ChatMgr._build_csv([], '灿灿')

    assert csv_text.split('\r\n')[0] == '\ufeff序号,时间,灿灿说的话,回答'


def test_build_csv_numbers_rows_from_one():
    messages = [
        {'created_at': ts('2026-10-08 10:00:00'), 'query': 'q1', 'answer': 'a1'},
        {'created_at': ts('2026-10-08 10:01:00'), 'query': 'q2', 'answer': 'a2'},
    ]

    rows = ChatMgr._build_csv(messages, '昭昭').split('\r\n')

    assert rows[1].startswith('1,2026-10-08 10:00:00,')
    assert rows[2].startswith('2,2026-10-08 10:01:00,')


def test_build_csv_quotes_comma_quote_and_newline():
    messages = [{
        'created_at': ts('2026-10-08 10:00:00'),
        'query': '有,逗号',
        'answer': '他说"好"\n第二行',
    }]

    csv_text = ChatMgr._build_csv(messages, '昭昭')

    assert '"有,逗号"' in csv_text
    # 内部引号翻倍，整段被引号包裹
    assert '"他说""好""' in csv_text


def test_build_csv_falls_back_to_error_message():
    """生成失败时回答列为空，必须回填失败原因，否则导出会丢信息。"""
    messages = [{
        'created_at': ts('2026-10-08 10:00:00'),
        'query': '喵', 'answer': '', 'error': 'Run failed: x',
    }]

    assert '失败：Run failed: x' in ChatMgr._build_csv(messages, '昭昭')


def test_build_csv_prefers_answer_over_error():
    messages = [{
        'created_at': ts('2026-10-08 10:00:00'),
        'query': 'q', 'answer': '正常回答', 'error': '不应出现',
    }]

    csv_text = ChatMgr._build_csv(messages, '昭昭')

    assert '正常回答' in csv_text
    assert '不应出现' not in csv_text


def test_build_csv_handles_missing_fields():
    csv_text = ChatMgr._build_csv([{'created_at': ts('2026-10-08 10:00:00')}], '昭昭')

    assert csv_text.split('\r\n')[1].startswith('1,2026-10-08 10:00:00,,')


# ---------- export_messages ----------
# 成功时返回 flask.Response（文件流），失败时返回 _err dict —— 两种形状都要断言

def _body(resp):
    """取 Response 的正文字符串（去掉 BOM 便于比对首行）。"""
    return resp.get_data().decode('utf-8')


def test_export_ok_returns_csv_response(monkeypatch, mgr):
    messages = [
        {'id': 'm1', 'created_at': ts('2026-10-08 10:00:00'),
         'query': '想你了', 'answer': '嗯，我也刚想你。'},
        {'id': 'm2', 'created_at': ts('2026-10-08 10:01:00'),
         'query': '在吗', 'answer': '', 'error': 'Run failed: x'},
    ]
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: {'has_more': False, 'data': messages})

    resp = mgr.export_messages('conv-1', '昭昭')

    assert isinstance(resp, Response)
    assert resp.status_code == 200
    assert resp.headers['Content-Type'].startswith('text/csv')
    assert resp.headers['X-Export-Count'] == '2'
    body = _body(resp)
    assert body.split('\r\n')[0] == '\ufeff序号,时间,昭昭说的话,回答'
    assert '想你了' in body
    # 生成失败的行回填失败原因
    assert '失败：Run failed: x' in body


def test_export_response_has_bom_bytes(monkeypatch, mgr):
    """原始字节必须是 EF BB BF，Excel 才会认 UTF-8。"""
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: {'has_more': False, 'data': [
                            {'id': 'm1', 'created_at': ts('2026-10-08 10:00:00'),
                             'query': 'q', 'answer': 'a'}]})

    resp = mgr.export_messages('conv-1', 'leo')

    assert resp.get_data()[:3] == b'\xef\xbb\xbf'


def test_export_response_headers_complete(monkeypatch, mgr):
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: {'has_more': False, 'data': [
                            {'id': 'm1', 'created_at': ts('2026-10-08 10:00:00'),
                             'query': 'q', 'answer': 'a'}]})

    resp = mgr.export_messages('conv-1', 'leo')

    assert resp.headers['Cache-Control'] == 'no-store'
    assert resp.headers['X-Content-Type-Options'] == 'nosniff'


def test_export_disposition_has_ascii_fallback_and_rfc5987(monkeypatch, mgr):
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: {'has_more': False, 'data': [
                            {'id': 'm1', 'created_at': ts('2026-10-08 10:00:00'),
                             'query': 'q', 'answer': 'a'}]})

    resp = mgr.export_messages('conv-1', '昭昭')

    disp = resp.headers['Content-Disposition']
    assert disp.startswith('attachment;')
    assert "filename*=UTF-8''" in disp
    # ASCII 回退里不能出现非 ASCII 字符（旧浏览器直接用它）
    ascii_part = disp.split('filename="')[1].split('"')[0]
    assert ascii_part.isascii()
    assert ascii_part.endswith('.csv')
    # 中文名要能在 RFC 5987 部分还原出来
    from urllib.parse import unquote
    encoded = disp.split("filename*=UTF-8''")[1]
    assert unquote(encoded).startswith('AI对话-昭昭-')


def test_content_disposition_ascii_name_used_directly():
    from core.chat.chat_mgr import ChatMgr

    disp = ChatMgr._content_disposition('chat.csv')

    assert 'filename="chat.csv"' in disp
    assert "filename*=UTF-8''chat.csv" in disp


def test_content_disposition_replaces_non_ascii_in_fallback():
    """中文名要退化成 ASCII 下划线，且保留扩展名（旧浏览器只会读 filename=）。"""
    from core.chat.chat_mgr import ChatMgr

    disp = ChatMgr._content_disposition('对话.csv')

    assert 'filename="__.csv"' in disp
    # 中文名本身仍通过 RFC 5987 完整保留
    from urllib.parse import unquote
    assert unquote(disp.split("filename*=UTF-8''")[1]) == '对话.csv'


@pytest.mark.parametrize('blank', ['', '   '])
def test_content_disposition_falls_back_when_name_blank(blank):
    """文件名全空时回退名不能是空串，否则部分浏览器不触发下载。"""
    from core.chat.chat_mgr import ChatMgr

    disp = ChatMgr._content_disposition(blank)

    assert 'filename="chat.csv"' in disp


def test_csv_response_content_type_and_count():
    from core.chat.chat_mgr import ChatMgr

    resp = ChatMgr._csv_response('a,b\r\n', 'x.csv', 5)

    assert resp.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert resp.headers['X-Export-Count'] == '5'


def test_export_requires_conversation_id(monkeypatch, mgr):
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: pytest.fail('不应触发取数'))

    for bad in (None, '', '   '):
        result = mgr.export_messages(bad, 'leo')
        assert result['code'] == -1
        assert result['msg'] == 'conversation_id is required'


def test_export_requires_user(monkeypatch, mgr):
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: pytest.fail('不应触发取数'))

    for bad in (None, '', '   '):
        result = mgr.export_messages('conv-1', bad)
        assert result['code'] == -1
        assert result['msg'] == 'user is required'


def test_export_params_are_trimmed(monkeypatch, mgr):
    seen = {}

    def spy(conversation_id, user, stop_before=None, **kw):
        seen.update(conversation_id=conversation_id, user=user)
        return [], False

    monkeypatch.setattr(mgr, 'collect_messages', spy)

    result = mgr.export_messages('  conv-1  ', '  昭昭  ')

    # 空数据会走到 _err，但能证明参数已被 strip 后再使用
    assert result['code'] == -1
    assert seen == {'conversation_id': 'conv-1', 'user': '昭昭'}


def test_export_passes_start_as_stop_before(monkeypatch, mgr):
    """起始日期要作为早停下界传给翻页，否则会把整个会话拉全。"""
    called = {}

    def spy(conversation_id, user, stop_before=None, **kw):
        called['stop_before'] = stop_before
        called['args'] = (conversation_id, user)
        return [], False

    monkeypatch.setattr(mgr, 'collect_messages', spy)

    mgr.export_messages('conv-1', '昭昭', start='2026-10-08')

    assert called['stop_before'] == ts('2026-10-08 00:00:00')
    assert called['args'] == ('conv-1', '昭昭')


def test_export_no_dates_passes_none_stop_before(monkeypatch, mgr):
    called = {}

    def spy(conversation_id, user, stop_before=None, **kw):
        called['stop_before'] = stop_before
        return [], False

    monkeypatch.setattr(mgr, 'collect_messages', spy)

    mgr.export_messages('conv-1', 'leo')

    assert called['stop_before'] is None


def test_export_bad_date_returns_err_without_fetching(monkeypatch, mgr):
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: pytest.fail('不应触发取数'))

    result = mgr.export_messages('conv-1', 'leo', start='2026/10/08')

    assert result['code'] == -1
    assert '日期格式' in result['msg']


def test_export_start_after_end_returns_err(monkeypatch, mgr):
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: pytest.fail('不应触发取数'))

    result = mgr.export_messages('conv-1', 'leo', start='2026-10-09', end='2026-10-08')

    assert result['code'] == -1
    assert '开始日期不能晚于结束日期' in result['msg']


def test_export_filters_out_of_range(monkeypatch, mgr):
    messages = [{'id': 'm1', 'created_at': ts('2026-10-08 10:00:00'),
                 'query': 'q', 'answer': 'a'}]
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: {'has_more': False, 'data': messages})

    result = mgr.export_messages('conv-1', 'leo', start='2026-10-09', end='2026-10-09')

    assert result['code'] == -1
    assert '没有数据' in result['msg']


def test_export_empty_conversation_returns_err(monkeypatch, mgr):
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: {'has_more': False, 'data': []})

    result = mgr.export_messages('conv-1', 'leo')

    assert result['code'] == -1
    assert '没有可导出的数据' in result['msg']


def test_export_truncated_reports_err_instead_of_partial(monkeypatch, mgr):
    """超出翻页上限时必须报错，不能悄悄给一份不完整的数据。"""
    all_messages = make_messages(100000)

    def loader(conversation_id, limit, user, first_id=None):
        return dify_page(all_messages, limit, first_id) | {'has_more': True}

    monkeypatch.setattr(AILocal, 'get_chat_messages', loader)

    result = mgr.export_messages('conv-1', 'leo')

    assert result['code'] == -1
    assert '缩小时间范围' in result['msg']


def test_export_upstream_error_propagates_message(monkeypatch, mgr):
    monkeypatch.setattr(AILocal, 'get_chat_messages', lambda *a, **kw: None)

    result = mgr.export_messages('conv-1', 'leo')

    assert result['code'] == -1
    assert '获取会话消息失败' in result['msg']


def test_export_csv_matches_filtered_window(monkeypatch, mgr):
    """端到端：日期窗口内的条数与 CSV 行数必须一致。"""
    start = ts('2026-10-08 00:00:00')
    messages = [
        {'id': 'out', 'created_at': start - 1, 'query': 'OUT', 'answer': 'x'},
        {'id': 'in1', 'created_at': start, 'query': 'IN1', 'answer': 'y'},
        {'id': 'in2', 'created_at': start + 60, 'query': 'IN2', 'answer': 'z'},
    ]
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: {'has_more': False, 'data': messages})

    resp = mgr.export_messages('conv-1', 'leo', start='2026-10-08', end='2026-10-08')

    assert isinstance(resp, Response)
    assert resp.headers['X-Export-Count'] == '2'
    body = _body(resp)
    assert 'IN1' in body and 'IN2' in body
    assert 'OUT' not in body
    # 表头 1 行 + 2 条数据（末尾有空行）
    assert len([r for r in body.split('\r\n') if r.strip()]) == 3


def test_export_error_shape_is_err_dict_not_response(monkeypatch, mgr):
    """失败时必须是 _err dict，路由才能把它序列化成 JSON。"""
    monkeypatch.setattr(AILocal, 'get_chat_messages',
                        lambda *a, **kw: {'has_more': False, 'data': []})

    result = mgr.export_messages('conv-1', 'leo')

    assert not isinstance(result, Response)
    assert result['code'] == -1 and result['msg']
