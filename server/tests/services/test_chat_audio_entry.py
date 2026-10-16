"""语音入口（`handle_message` 的 audio 分支）回归。

这类缺陷只在**真实入口**上暴露：处理器是 `_register_events` 里的嵌套函数，
`self` 是 `ChatMgr`，而每个连接的状态在 `ctx`（`ClientContext`）上。
写错成 `self.xxx` 时单元测试不易发现（不经过入口就碰不到那一行），
但真实首包会直接抛异常、功能完全不可用。

因此这里全部通过 `_register_events` 注册出来的真实处理器驱动，
不直接调用 `ctx` 上的方法。
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from core.chat.chat_mgr import EVENT_MESSAGE, ChatMgr, ClientContext


@pytest.fixture
def chat_entry():
    """返回 (mgr, socketio, handlers)：handlers 里是真实注册的 socket.io 处理器。"""
    handlers: dict = {}

    def register(event):
        def decorator(fn):
            handlers[event] = fn
            return fn

        return decorator

    socketio = MagicMock()
    socketio.on = register
    mgr = ChatMgr()
    mgr.init(socketio)
    return mgr, socketio, handlers


def _audio_msg(**overrides):
    msg = {
        'type': 'audio',
        'content': '',
        'sample': 16000,
        'finish': False,
        'clientRequestId': 'rid-audio-1',
        'chatType': '',
        'roomId': '',
    }
    msg.update(overrides)
    return json.dumps(msg)


def test_first_audio_packet_opens_a_session(chat_entry):
    """带 clientRequestId 的新语音请求，首包必须能建立起 ASR 会话。

    回归：这里曾写成 `self.ai.user`（self 是 ChatMgr，没有 ai 属性），
    首包直接抛 `AttributeError: 'ChatMgr' object has no attribute 'ai'`，
    语音功能整体不可用。
    """
    mgr, socketio, handlers = chat_entry
    sid = 'sid-audio-open'
    ctx = ClientContext(sid, socketio)
    mgr.clients[sid] = ctx
    ctx.asr = MagicMock()
    ctx.note_audio_request = MagicMock(return_value='new')
    mgr.handle_audio = MagicMock()

    with patch('core.chat.chat_mgr.request', new=MagicMock(sid=sid)):
        handlers[EVENT_MESSAGE](_audio_msg())      # 不得抛异常

    assert ctx.asr.begin_session.called, '首包没有开启 ASR 会话'
    rid = ctx.asr.begin_session.call_args[0][0]
    assert rid == 'rid-audio-1'


def test_first_audio_packet_binds_the_current_attempt(chat_entry):
    """首包建立会话时必须带上请求代次，供错误回调绑定使用。

    代次取的是 `ctx.ai.user` 下的记录。若取错对象（或漏传），
    后续错误回调就无法判断自己属于哪一轮，重试后旧错误会击中新请求。
    """
    mgr, socketio, handlers = chat_entry
    sid = 'sid-audio-attempt'
    ctx = ClientContext(sid, socketio)
    mgr.clients[sid] = ctx
    ctx.asr = MagicMock()
    ctx.note_audio_request = MagicMock(return_value='new')
    mgr.handle_audio = MagicMock()

    with patch('core.chat.chat_mgr.request', new=MagicMock(sid=sid)), \
         patch('core.chat.chat_mgr.chat_request_store.get_attempt',
               return_value=7) as get_attempt:
        handlers[EVENT_MESSAGE](_audio_msg(clientRequestId='rid-a7'))

    assert ctx.asr.begin_session.call_args[0][0] == 'rid-a7'
    assert ctx.asr.begin_session.call_args[0][1] == 7, (
        f'首包没有绑定当前代次: {ctx.asr.begin_session.call_args[0]!r}'
    )
    # 代次要按连接自己的用户去查（ctx.ai.user），不能是别的对象
    assert get_attempt.call_args[0][0] == ctx.ai.user


def test_audio_packet_without_request_id_does_not_open_session(chat_entry):
    """没有 clientRequestId 的音频包不该开启新会话（保持原有语义）。"""
    mgr, socketio, handlers = chat_entry
    sid = 'sid-audio-norid'
    ctx = ClientContext(sid, socketio)
    mgr.clients[sid] = ctx
    ctx.asr = MagicMock()
    ctx.note_audio_request = MagicMock(return_value='new')
    mgr.handle_audio = MagicMock()

    with patch('core.chat.chat_mgr.request', new=MagicMock(sid=sid)):
        handlers[EVENT_MESSAGE](_audio_msg(clientRequestId=''))

    assert not ctx.asr.begin_session.called, '没有请求 id 时不该开启会话'
    assert mgr.handle_audio.called, '音频仍应被处理'


def test_audio_continue_does_not_open_session_again(chat_entry):
    """同一请求的后续音频包（continue）不应重复开启会话。"""
    mgr, socketio, handlers = chat_entry
    sid = 'sid-audio-cont'
    ctx = ClientContext(sid, socketio)
    mgr.clients[sid] = ctx
    ctx.asr = MagicMock()
    ctx.note_audio_request = MagicMock(return_value='continue')
    mgr.handle_audio = MagicMock()

    with patch('core.chat.chat_mgr.request', new=MagicMock(sid=sid)):
        handlers[EVENT_MESSAGE](_audio_msg())

    assert not ctx.asr.begin_session.called, 'continue 不该重新开会话'


def test_audio_from_unknown_client_is_ignored(chat_entry):
    """未握手的连接发来的音频要被忽略，不能抛异常。"""
    mgr, socketio, handlers = chat_entry
    with patch('core.chat.chat_mgr.request', new=MagicMock(sid='sid-unknown')):
        handlers[EVENT_MESSAGE](_audio_msg())      # 不得抛异常


def test_audio_finish_closes_the_session(chat_entry):
    """finish 包要走到 end_asr（收尾链路不能被入口改动破坏）。"""
    mgr, socketio, handlers = chat_entry
    sid = 'sid-audio-fin'
    ctx = ClientContext(sid, socketio)
    mgr.clients[sid] = ctx
    ctx.asr = MagicMock()
    ctx.note_audio_request = MagicMock(return_value='continue')
    mgr.handle_audio = MagicMock()

    with patch('core.chat.chat_mgr.request', new=MagicMock(sid=sid)):
        handlers[EVENT_MESSAGE](_audio_msg(finish=True))

    assert ctx.asr.end_asr.called, 'finish 包没有结束 ASR'


def test_audio_cancel_cancels_the_session(chat_entry):
    """cancel 包要取消对应会话并标记请求已取消。"""
    mgr, socketio, handlers = chat_entry
    sid = 'sid-audio-cancel'
    ctx = ClientContext(sid, socketio)
    mgr.clients[sid] = ctx
    ctx.asr = MagicMock()
    ctx.note_audio_request = MagicMock(return_value='continue')
    ctx.mark_request_cancelled = MagicMock()
    mgr.handle_audio = MagicMock()

    with patch('core.chat.chat_mgr.request', new=MagicMock(sid=sid)):
        handlers[EVENT_MESSAGE](_audio_msg(cancel=True))

    assert ctx.asr.cancel_session.called, 'cancel 包没有取消 ASR 会话'
    assert ctx.mark_request_cancelled.called, 'cancel 包没有标记请求已取消'
