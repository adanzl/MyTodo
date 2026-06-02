"""ASSRT 字幕搜索、下载与 Whisper 识别单元测试。"""

from unittest.mock import patch

from flask import Flask

import core.api.media_routes as media_routes
from core.services.subtitle_mgr import SubtitleMgr
from core.subtitles.assrt_client import AssrtClient, _lang_ok, _row


def test_lang_ok_english_by_desc():
    sub = {"lang": {"desc": "英文", "langlist": {"langdou": True}}}
    assert _lang_ok(sub, {"en"}) is True
    assert _lang_ok(sub, {"zh"}) is False


def test_row_shape():
    row = _row({
        "id": 123,
        "native_name": "Test Show S01E01",
        "videoname": "test.s01e01",
        "subtype": "srt",
        "lang": {"desc": "英"},
    })
    assert row["id"] == "123"
    assert row["attributes"]["files"][0]["file_id"] == 123


def test_search_by_text_requires_query():
    assert SubtitleMgr().search_by_text("")["code"] == -1


@patch.object(media_routes.subtitle_mgr, "search_by_text")
def test_media_subtitle_search_route(mock_search):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(media_routes.media_bp)
    mock_search.return_value = {
        "code": 0,
        "data": {"mode": "text", "query": "matrix", "total_count": 0, "data": []},
    }
    resp = app.test_client().get("/media/subtitle/search?query=matrix")
    assert resp.status_code == 200
    mock_search.assert_called_once()


@patch.object(media_routes.subtitle_mgr, "recognize_subtitle")
def test_media_subtitle_recognize_route(mock_recognize):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(media_routes.media_bp)
    mock_recognize.return_value = {
        "code": 0,
        "data": {"path": "/tmp/x.en.vtt", "language": "en"},
    }
    resp = app.test_client().post(
        "/media/subtitle/recognize",
        json={"video_path": "/tmp/a.mp4", "language": "en"},
    )
    assert resp.status_code == 200
    mock_recognize.assert_called_once()


@patch("core.subtitles.assrt_client.http_get_bytes")
def test_search_by_query_maps_results(mock_http, monkeypatch):
    from core.config import config as app_config

    monkeypatch.setattr(app_config, "ASSRT_API_KEY", "test-token", raising=False)
    import json

    payload = {
        "status": 0,
        "sub": {
            "result": "succeed",
            "subs": [{
                "id": 99,
                "native_name": "Matrix",
                "videoname": "matrix.1999",
                "subtype": "srt",
                "lang": {"desc": "英", "langlist": {"langdou": True}},
            }],
        },
    }
    mock_http.return_value = (200, json.dumps(payload).encode("utf-8"))
    out = AssrtClient().search_by_query("matrix", languages="en")
    assert out["total_count"] == 1
    assert out["data"][0]["attributes"]["subtitle_id"] == "99"


@patch.object(AssrtClient, "download_to_sidecar")
def test_download_subtitle(mock_dl, tmp_path, monkeypatch):
    monkeypatch.setattr("core.services.subtitle_mgr.config.DEFAULT_BASE_DIR", str(tmp_path), raising=False)
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    sub = tmp_path / "clip.en.srt"
    mock_dl.return_value = {
        "path": str(sub),
        "remote_name": "clip.srt",
        "subtitle_id": "99",
    }
    mgr = SubtitleMgr()
    mgr.default_base_dir = str(tmp_path)
    out = mgr.download_subtitle(str(video), "99")
    assert out["code"] == 0
    assert out["data"]["path"] == str(sub)


@patch("core.services.subtitle_mgr.transcribe_to_sidecar")
def test_recognize_subtitle(mock_transcribe, tmp_path, monkeypatch):
    monkeypatch.setattr("core.services.subtitle_mgr.config.DEFAULT_BASE_DIR", str(tmp_path), raising=False)
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    vtt = tmp_path / "clip.en.vtt"
    mock_transcribe.return_value = {
        "path": str(vtt),
        "remote_name": "clip.en.vtt",
        "language": "en",
        "source": "whisper",
    }
    mgr = SubtitleMgr()
    mgr.default_base_dir = str(tmp_path)
    out = mgr.recognize_subtitle(str(video), language="en")
    assert out["code"] == 0
    mock_transcribe.assert_called_once_with(str(video), language="en")
