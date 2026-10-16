"""抖音播放地址选择。不访问外网。"""
from core.services.tools.video_dump_douyin_media import (
    is_note,
    media_title,
    netscape_cookies,
    open_url,
    play_urls,
)


def test_open_url_keeps_douyin_video_and_drops_other_sites():
    assert open_url("https://www.douyin.com/video/7623413914059447144") == (
        "https://www.douyin.com/video/7623413914059447144"
    )
    assert open_url("https://www.bilibili.com/video/BV1xx411c7mD") == ""
    assert open_url("http://www.douyin.com/video/1") == ""


def test_note_url_is_rewritten_before_open():
    raw = "https://www.douyin.com/note/7696783380364742760?previous_page=app_code_link"
    assert open_url(raw) == "https://www.douyin.com/video/7696783380364742760"


def test_play_urls_prefer_h264_mp4_and_skip_dash():
    detail = {
        "desc": "标题",
        "video": {
            "bit_rate": [
                {
                    "format": "mp4",
                    "is_h265": 1,
                    "quality_type": 2,
                    "play_addr": {"url_list": ["https://cdn.example/h265.mp4"]},
                },
                {
                    "format": "dash",
                    "is_h265": 0,
                    "quality_type": 1,
                    "play_addr": {"url_list": ["https://cdn.example/dash.mp4"]},
                },
                {
                    "format": "mp4",
                    "is_h265": 0,
                    "quality_type": 10,
                    "play_addr": {"url_list": ["https://cdn.example/720.mp4"]},
                },
                {
                    "format": "mp4",
                    "is_h265": 0,
                    "quality_type": 1,
                    "play_addr": {"url_list": ["https://cdn.example/1080.mp4"]},
                },
            ],
            "play_addr": {"url_list": ["https://cdn.example/fallback.mp4"]},
        },
    }
    assert play_urls(detail) == [
        "https://cdn.example/1080.mp4",
        "https://cdn.example/720.mp4",
        "https://cdn.example/fallback.mp4",
    ]
    assert media_title(detail) == "标题"
    assert is_note(detail) is False


def test_image_post_without_play_url_is_a_note():
    detail = {"images": [{"url": "https://cdn.example/a.jpg"}], "video": {}}
    assert is_note(detail) is True


def test_netscape_cookies_keep_douyin_rows():
    text = "\n".join([
        "# Netscape HTTP Cookie File",
        ".douyin.com\tTRUE\t/\tTRUE\t1893456000\ts_v_web_id\tabc",
        ".bilibili.com\tTRUE\t/\tTRUE\t1893456000\tSESSDATA\tnope",
        ".douyin.com\tTRUE\t/\tFALSE\t0\tttwid\tdef",
    ])
    rows = netscape_cookies(text)
    assert [row["name"] for row in rows] == ["s_v_web_id", "ttwid"]
    assert rows[0]["expires"] == 1893456000
    assert "expires" not in rows[1]
