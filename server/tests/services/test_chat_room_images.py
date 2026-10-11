"""聊天室图片消息的服务端解析测试。

聊天室的图片不经过 Dify：前端把图存到 pic 目录，消息里只带文件名，服务端原样
广播并落 Redis。这里守住的是「形状收敛」——广播之前必须把任意输入归一化，
否则一条畸形消息会被推给房间里所有人。
"""

import pytest

from core.chat.chat_mgr import MAX_ROOM_FILES, _parse_room_files


def test_parses_object_form():
    assert _parse_room_files([{'type': 'image', 'filename': 'chat-1-1.png'}]) == [
        {'type': 'image', 'filename': 'chat-1-1.png'}
    ]


def test_parses_string_form():
    assert _parse_room_files(['chat-1-1.png']) == [
        {'type': 'image', 'filename': 'chat-1-1.png'}
    ]


def test_single_value_is_tolerated():
    assert _parse_room_files('a.png') == [{'type': 'image', 'filename': 'a.png'}]
    assert _parse_room_files({'filename': 'a.png'}) == [
        {'type': 'image', 'filename': 'a.png'}
    ]


@pytest.mark.parametrize('raw', [None, [], '', {}, 0, [None, 42, [], '', '   ', {}]])
def test_unusable_input_yields_empty(raw):
    assert _parse_room_files(raw) == []


def test_strips_path_components():
    """前端只该传文件名；带上路径也要归一化，避免把路径广播出去。"""
    assert _parse_room_files(['../../etc/passwd']) == [
        {'type': 'image', 'filename': 'passwd'}
    ]
    assert _parse_room_files([{'filename': 'C:\\tmp\\a.png'}]) == [
        {'type': 'image', 'filename': 'a.png'}
    ]


def test_caps_the_number_of_files():
    """防滥用：一条消息最多带 MAX_ROOM_FILES 张。"""
    raw = [{'filename': f'chat-1-{i}.png'} for i in range(MAX_ROOM_FILES + 5)]

    assert len(_parse_room_files(raw)) == MAX_ROOM_FILES


def test_drops_overlong_filenames():
    too_long = 'a' * 256 + '.png'

    assert _parse_room_files([{'filename': too_long}]) == []
