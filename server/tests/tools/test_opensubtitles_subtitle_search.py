"""OpenSubtitles 字幕搜索单元测试。"""

from unittest.mock import MagicMock, patch

from flask import Flask

import core.api.media_routes as media_routes
from core.tools.open_subtitles import OpenSubtitlesClient, _normalize_base_url, compute_movie_hash
from core.services.subtitle_mgr import SubtitleMgr


def test_normalize_base_url_adds_https():
    assert _normalize_base_url("api.opensubtitles.com") == "https://api.opensubtitles.com"
    assert _normalize_base_url("https://api.opensubtitles.com").startswith("https://")


def test_compute_movie_hash(tmp_path):
    p = tmp_path / "sample.bin"
    p.write_bytes(b"\x01\x02\x03\x04" * (32 * 1024))
    assert len(compute_movie_hash(str(p))) == 16


def test_search_by_text_requires_query():
    assert SubtitleMgr().search_by_text("")["code"] == -1


@patch.object(media_routes.subtitle_mgr, "search_by_text")
def test_media_subtitle_search_route_text(mock_search):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(media_routes.media_bp)
    mock_search.return_value = {
        "code": 0,
        "data": {"mode": "text", "query": "matrix", "total_count": 0, "data": []},
    }
    resp = app.test_client().get("/media/subtitle/search?mode=text&query=matrix")
    assert resp.status_code == 200
    mock_search.assert_called_once()


@patch("core.tools.open_subtitles.OpenSubtitlesClient._get_json")
def test_search_by_query_returns_official_shape(mock_call, monkeypatch):
    monkeypatch.setattr("core.tools.open_subtitles.config.OPEN_SUBTITLES_API", "key", raising=False)
    mock_call.return_value = {
        "total_count": 1,
        "total_pages": 1,
        "page": 1,
        "per_page": 1,
        "data": [{
            "id": "1",
            "type": "subtitle",
            "attributes": {
                "subtitle_id": "1",
                "language": "zh",
                "files": [{"file_id": 99, "file_name": "a.srt"}],
            },
        }],
    }
    out = OpenSubtitlesClient().search_by_query("matrix", languages="en")
    assert out["total_count"] == 1
    assert out["data"][0]["attributes"]["files"][0]["file_id"] == 99


@patch("core.tools.open_subtitles.requests.request")
def test_login_base_url_without_scheme(mock_request, monkeypatch):
    monkeypatch.setattr("core.tools.open_subtitles.config.OPEN_SUBTITLES_API", "test-key", raising=False)
    monkeypatch.setattr("core.tools.open_subtitles.config.OPEN_SUBTITLES_USER", "user", raising=False)
    monkeypatch.setattr("core.tools.open_subtitles.config.OPEN_SUBTITLES_PASS", "pass", raising=False)

    import core.tools.open_subtitles as mod
    mod._auth.clear()
    mod._auth.update({"token": None, "expires": 0.0})

    login_resp = MagicMock(status_code=200)
    login_resp.json.return_value = {"token": "tok", "base_url": "api.opensubtitles.com"}
    search_resp = MagicMock(status_code=200)
    search_resp.json.return_value = {"total_count": 0, "total_pages": 0, "page": 1, "data": []}
    mock_request.side_effect = [login_resp, search_resp]

    client = OpenSubtitlesClient()
    client.search_by_query("matrix", languages="en")
    assert client.base_url == "https://api.opensubtitles.com"
    search_url = mock_request.call_args_list[1].args[1]
    assert search_url.startswith("https://")
