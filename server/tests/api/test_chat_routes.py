"""chat_routes（Dify 对话 HTTP 接口）单元测试。

对外路径是 `/api/chat/*`，`/api` 前缀由 `main.py` 的 `DispatcherMiddleware` 补上；
测试里直接以 `url_prefix='/chat'` 注册，所以请求 `/chat/*`。

业务逻辑都在 `ChatMgr`（`core/chat/chat_mgr.py`，由
`tests/services/test_chat_mgr_history.py` 覆盖），所以这里 mock 掉 `chat_mgr`，
只测路由层职责：把请求参数交给 mgr、原样透出 mgr 的返回、异常兜底、
以及导出时把结果包成文件响应。
"""

from unittest.mock import MagicMock

import pytest
from flask import Flask

import core.api.chat_routes as chat_routes


@pytest.fixture
def app(monkeypatch):
    """搭一个只挂 chat_bp 的 Flask 应用，并把 chat_mgr 换成 mock。"""
    monkeypatch.setattr(chat_routes, 'chat_mgr', MagicMock())

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(chat_routes.chat_bp, url_prefix='/chat')
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------- /chat/messages ----------

def test_messages_ok(client):
    payload = {"limit": 3, "has_more": True, "data": [{"id": "m1"}]}
    chat_routes.chat_mgr.get_messages.return_value = {
        "code": 0, "msg": "ok", "data": payload}

    resp = client.get('/chat/messages?conversation_id=c&user=leo&limit=3')

    assert resp.status_code == 200
    assert resp.json["code"] == 0
    assert resp.json["data"] == payload
    # limit 以字符串原样交给 mgr（是否收敛由 mgr 决定），与迁移前行为一致
    chat_routes.chat_mgr.get_messages.assert_called_once_with('c', '3', 'leo', None)


def test_messages_first_id_passed(client):
    chat_routes.chat_mgr.get_messages.return_value = {"code": 0, "msg": "ok",
                                                     "data": {"data": []}}

    resp = client.get('/chat/messages?conversation_id=c&user=leo&first_id=old-1')

    assert resp.json["code"] == 0
    chat_routes.chat_mgr.get_messages.assert_called_once_with(
        'c', None, 'leo', 'old-1')


def test_messages_missing_params_passed_as_none(client):
    chat_routes.chat_mgr.get_messages.return_value = {"code": 0, "msg": "ok",
                                                     "data": None}

    client.get('/chat/messages')

    chat_routes.chat_mgr.get_messages.assert_called_once_with(None, None, None, None)


def test_messages_data_null_passthrough(client):
    """底层取数失败时是 `code:0` + `data:null`，路由不能把它改成报错。

    这是既有行为（移动端历史加载依赖该形状），排查该「静默失败」是另一件事。
    """
    chat_routes.chat_mgr.get_messages.return_value = {"code": 0, "msg": "ok",
                                                     "data": None}

    resp = client.get('/chat/messages?conversation_id=c&user=leo')

    assert resp.status_code == 200
    assert resp.json["code"] == 0
    assert resp.json["data"] is None


def test_messages_mgr_error_passthrough(client):
    chat_routes.chat_mgr.get_messages.return_value = {"code": -1, "msg": "上游炸了",
                                                     "data": None}

    resp = client.get('/chat/messages?conversation_id=c&user=leo')

    assert resp.json["code"] == -1
    assert resp.json["msg"] == "上游炸了"


def test_messages_exception_returns_negative_code(client):
    chat_routes.chat_mgr.get_messages.side_effect = RuntimeError("boom")

    resp = client.get('/chat/messages?conversation_id=c')

    assert resp.status_code == 200
    assert resp.json["code"] == -1
    assert 'boom' in resp.json["msg"]


# ---------- /chat/conversations ----------

def test_conversations_ok(client):
    payload = {"limit": 20, "has_more": True, "data": [{"id": "conv-1"}]}
    chat_routes.chat_mgr.get_conversations.return_value = {
        "code": 0, "msg": "ok", "data": payload}

    resp = client.get('/chat/conversations?user=leo&limit=20')

    assert resp.status_code == 200
    assert resp.json["code"] == 0
    assert resp.json["data"] == payload
    chat_routes.chat_mgr.get_conversations.assert_called_once_with('leo', '20', None)


def test_conversations_missing_user(client):
    """user 缺失时由 mgr 报错，路由原样透出。"""
    chat_routes.chat_mgr.get_conversations.return_value = {"code": -1,
                                                          "msg": "user is required"}
    resp = client.get('/chat/conversations')

    assert resp.json["code"] == -1
    assert 'user is required' in resp.json["msg"]
    # 参数校验在 mgr，所以这里必须已经调用过
    chat_routes.chat_mgr.get_conversations.assert_called_once_with(None, None, None)


def test_conversations_params_passed_raw(client):
    """user / limit / last_id 都原样交给 mgr，清洗与收敛由 mgr 负责。"""
    chat_routes.chat_mgr.get_conversations.return_value = {"code": 0, "msg": "ok",
                                                          "data": {"data": []}}

    client.get('/chat/conversations?user=%20leo%20&limit=abc&last_id=conv-9')

    chat_routes.chat_mgr.get_conversations.assert_called_once_with(
        ' leo ', 'abc', 'conv-9')


def test_conversations_error_propagates_upstream_message(client):
    """上游错误要透出，不能被前端误判成「没有会话」。"""
    chat_routes.chat_mgr.get_conversations.return_value = {
        "code": -1, "msg": "401 Client Error: UNAUTHORIZED"}

    resp = client.get('/chat/conversations?user=leo')

    assert resp.status_code == 200
    assert resp.json["code"] == -1
    assert "401" in resp.json["msg"]


def test_conversations_exception_returns_negative_code(client):
    chat_routes.chat_mgr.get_conversations.side_effect = RuntimeError("boom")

    resp = client.get('/chat/conversations?user=leo')

    assert resp.status_code == 200
    assert resp.json["code"] == -1
    assert 'boom' in resp.json["msg"]


# ---------- /chat/export ----------
# 导出逻辑整体在 ChatMgr.export_messages（含参数校验、CSV、响应头），
# 由 tests/services/test_chat_mgr_history.py 覆盖。这里只测路由的转发职责。

def test_export_forwards_raw_params(client, monkeypatch):
    """query 原样转给 mgr（strip/校验都在 mgr 内），不在此加工。"""
    chat_routes.chat_mgr.export_messages.return_value = {"code": -1, "msg": "x"}

    client.get('/chat/export?conversation_id=%20c%20&user=%20leo%20'
               '&start=2026-10-01&end=2026-10-08')

    chat_routes.chat_mgr.export_messages.assert_called_once_with(
        ' c ', ' leo ', start='2026-10-01', end='2026-10-08')


def test_export_missing_dates_forwarded_as_none(client, monkeypatch):
    chat_routes.chat_mgr.export_messages.return_value = {"code": -1, "msg": "x"}

    client.get('/chat/export?conversation_id=c&user=leo')

    chat_routes.chat_mgr.export_messages.assert_called_once_with(
        'c', 'leo', start=None, end=None)


def test_export_missing_params_forwarded_as_none(client, monkeypatch):
    """缺参不在此拦截，交给 mgr 统一校验。"""
    chat_routes.chat_mgr.export_messages.return_value = {"code": -1, "msg": "x"}

    client.get('/chat/export')

    chat_routes.chat_mgr.export_messages.assert_called_once_with(
        None, None, start=None, end=None)


def test_export_response_returned_as_is(client, monkeypatch):
    """mgr 返回的 Response 要原样成为 HTTP 响应（路由不再包装）。"""
    from flask import Response

    def fake(conversation_id, user, start=None, end=None):
        resp = Response('\ufeff序号\r\n1\r\n', content_type='text/csv; charset=utf-8')
        resp.headers['Content-Disposition'] = 'attachment; filename="a.csv"'
        resp.headers['X-Export-Count'] = '7'
        return resp

    chat_routes.chat_mgr.export_messages.side_effect = fake

    resp = client.get('/chat/export?conversation_id=c&user=leo')

    assert resp.status_code == 200
    assert resp.headers['Content-Type'].startswith('text/csv')
    assert resp.headers['X-Export-Count'] == '7'
    assert resp.get_data().startswith(b'\xef\xbb\xbf')


def test_export_error_is_json(client, monkeypatch):
    """失败时 mgr 返回 _err dict，Flask 会序列化成 JSON（前端靠此区分）。"""
    chat_routes.chat_mgr.export_messages.return_value = {
        "code": -1, "msg": "所选时间范围内没有数据"}

    resp = client.get('/chat/export?conversation_id=c&user=leo')

    assert resp.headers['Content-Type'].startswith('application/json')
    assert resp.json["code"] == -1
    assert resp.json["msg"] == "所选时间范围内没有数据"


def test_export_mgr_exception_returns_err(client, monkeypatch):
    chat_routes.chat_mgr.export_messages.side_effect = RuntimeError("boom")

    resp = client.get('/chat/export?conversation_id=c&user=leo')

    assert resp.status_code == 200
    assert resp.json["code"] == -1
    assert 'boom' in resp.json["msg"]

