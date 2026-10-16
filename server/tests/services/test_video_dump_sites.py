"""从分享文案里取出视频链接。"""
from core.services.tools.video_dump_sites import extract_url, match_site

_SHARE = (
    "7.64 复制打开抖音，看看【格格爸的作品】初章到中章过渡 # 原版娃# ket # pet ... "
    "https://v.douyin.com/byj1wNE4A20/ :8pm 08/28 Ljp:/ z@T.yg \n\n还有这个"
)


def test_douyin_share_text_keeps_only_the_short_link():
    url = extract_url(_SHARE)
    assert url == "https://v.douyin.com/byj1wNE4A20/"
    site = match_site(url)
    assert site is not None and site.id == "douyin"


def test_plain_url_is_unchanged():
    url = "https://www.bilibili.com/video/BV1xx411c7mD"
    assert extract_url(url) == url
    assert match_site(url).id == "bilibili"


def test_text_without_link_is_empty():
    assert extract_url("复制打开抖音，看看作品") == ""


def test_douyin_note_url_becomes_video_url():
    raw = "https://www.douyin.com/note/7696783380364742760?previous_page=app_code_link"
    assert extract_url(raw) == "https://www.douyin.com/video/7696783380364742760"
    assert match_site(extract_url(raw)).id == "douyin"


def test_douyin_video_url_keeps_query():
    raw = "https://www.douyin.com/video/7696783380364742760?previous_page=app_code_link"
    assert extract_url(raw) == raw


def test_douyin_share_and_modal_urls_become_video_url():
    share = "https://www.iesdouyin.com/share/video/1234567890/"
    modal = "https://www.douyin.com/user/MS4wLjAB?modal_id=1234567890"
    assert extract_url(share) == "https://www.douyin.com/video/1234567890"
    assert extract_url(modal) == "https://www.douyin.com/video/1234567890"
