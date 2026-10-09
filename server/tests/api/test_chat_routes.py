"""chat_routes（Dify 对话 HTTP 代理）单元测试。

对外路径是 `/api/chat/*`，`/api` 前缀由 `main.py` 的 `DispatcherMiddleware` 补上；
测试里直接以 `url_prefix='/chat'` 注册，所以请求 `/chat/*`。
"""

from unittest.mock import MagicMock

import pytest
from flask import Flask

import core.api.chat_routes as chat_routes


@pytest.fixture
def app(monkeypatch):
    """搭一个只挂 chat_bp 的 Flask 应用，并把 AILocal 换成 mock。"""
    monkeypatch.setattr(chat_routes, 'AILocal', MagicMock())

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
    chat_routes.AILocal.get_chat_messages.return_value = payload

    resp = client.get('/chat/messages?conversation_id=c&user=leo&limit=3')

    assert resp.status_code == 200
    assert resp.json["code"] == 0
    assert resp.json["data"] == payload
    # limit 保持原样透传（字符串），与迁移前行为一致
    chat_routes.AILocal.get_chat_messages.assert_called_once_with('c', '3', 'leo', None)


def test_messages_first_id_passed(client):
    chat_routes.AILocal.get_chat_messages.return_value = {"data": []}

    resp = client.get('/chat/messages?conversation_id=c&user=leo&first_id=old-1')

    assert resp.json["code"] == 0
    chat_routes.AILocal.get_chat_messages.assert_called_once_with(
        'c', None, 'leo', 'old-1'
    )


def test_messages_exception_returns_negative_code(client):
    chat_routes.AILocal.get_chat_messages.side_effect = RuntimeError("boom")

    resp = client.get('/chat/messages?conversation_id=c')

    assert resp.status_code == 200
    assert resp.json["code"] == -1


# ---------- /chat/conversations ----------

def test_conversations_ok(client):
    payload = {"limit": 20, "has_more": True, "data": [{"id": "conv-1"}]}
    chat_routes.AILocal.get_conversations.return_value = payload

    resp = client.get('/chat/conversations?user=leo&limit=20')

    assert resp.status_code == 200
    assert resp.json["code"] == 0
    assert resp.json["data"] == payload
    chat_routes.AILocal.get_conversations.assert_called_once_with('leo', 20, None)


def test_conversations_missing_user(client):
    resp = client.get('/chat/conversations')

    assert resp.json["code"] == -1
    assert 'user is required' in resp.json["msg"]
    chat_routes.AILocal.get_conversations.assert_not_called()


def test_conversations_blank_user(client):
    resp = client.get('/chat/conversations?user=%20%20')

    assert resp.json["code"] == -1
    chat_routes.AILocal.get_conversations.assert_not_called()


def test_conversations_user_is_trimmed(client):
    chat_routes.AILocal.get_conversations.return_value = {"data": []}

    resp = client.get('/chat/conversations?user=%20leo%20')

    assert resp.json["code"] == 0
    chat_routes.AILocal.get_conversations.assert_called_once_with('leo', 20, None)


def test_conversations_last_id_passed(client):
    chat_routes.AILocal.get_conversations.return_value = {"data": []}

    resp = client.get('/chat/conversations?user=leo&last_id=conv-9')

    assert resp.json["code"] == 0
    chat_routes.AILocal.get_conversations.assert_called_once_with('leo', 20, 'conv-9')


def test_conversations_blank_last_id_becomes_none(client):
    chat_routes.AILocal.get_conversations.return_value = {"data": []}

    client.get('/chat/conversations?user=leo&last_id=')

    chat_routes.AILocal.get_conversations.assert_called_once_with('leo', 20, None)


@pytest.mark.parametrize("raw_limit,expected", [
    (None, 20),      # 不传 -> 默认
    ("", 20),        # 空串 -> 默认
    ("abc", 20),     # 非法 -> 默认
    ("0", 1),        # 下界收敛
    ("-5", 1),
    ("999", 100),    # 上界收敛（Dify 单页上限）
    ("50", 50),
])
def test_conversations_limit_clamped(client, raw_limit, expected):
    chat_routes.AILocal.get_conversations.return_value = {"data": []}

    url = '/chat/conversations?user=leo'
    if raw_limit is not None:
        url += f'&limit={raw_limit}'
    resp = client.get(url)

    assert resp.json["code"] == 0
    chat_routes.AILocal.get_conversations.assert_called_once_with('leo', expected, None)


def test_conversations_error_propagates_upstream_message(client):
    """上游错误要透出，不能被前端误判成「没有会话」。"""
    chat_routes.AILocal.get_conversations.side_effect = RuntimeError(
        "401 Client Error: UNAUTHORIZED"
    )

    resp = client.get('/chat/conversations?user=leo')

    assert resp.status_code == 200
    assert resp.json["code"] == -1
    assert "401" in resp.json["msg"]
