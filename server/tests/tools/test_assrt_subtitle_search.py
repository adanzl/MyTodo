"""ASSRT 字幕搜索、下载与 Whisper 识别任务队列单元测试。"""

import json
from unittest.mock import patch

from flask import Flask

import core.api.media_routes as media_routes
from core.config import (
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_PROCESSING,
    TASK_STATUS_SUCCESS,
)
from core.services.subtitle_mgr import SubtitleMgr, SubtitleRecognizeMgr
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


@patch.object(SubtitleRecognizeMgr, "__init__", lambda self: None)
def test_search_by_text_requires_query():
    mgr = SubtitleMgr()
    assert mgr.search_by_text("")["code"] == -1


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
        "data": {"task_id": "t1", "status": "pending"},
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


@patch.object(SubtitleRecognizeMgr, "__init__", lambda self: None)
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
    out = mgr.download_subtitle(str(video), "99")
    assert out["code"] == 0
    assert out["data"]["path"] == str(sub)


def _make_recognize_mgr(tmp_path, monkeypatch) -> SubtitleRecognizeMgr:
    base = tmp_path / "subtitle_recognize"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("core.services.subtitle_mgr._RECOGNIZE_TASK_DIR", str(base))
    monkeypatch.setattr("core.services.subtitle_mgr.config.DEFAULT_BASE_DIR", str(tmp_path))
    return SubtitleRecognizeMgr()


@patch("core.services.subtitle_mgr.run_in_background")
def test_recognize_enqueue_and_list(mock_bg, tmp_path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    q = _make_recognize_mgr(tmp_path, monkeypatch)
    out = q.enqueue(str(video), language="en")
    assert out["code"] == 0
    task_id = out["data"]["task_id"]
    assert any(t["task_id"] == task_id for t in q.list_tasks())
    mock_bg.assert_called()


@patch("core.services.subtitle_mgr.run_in_background")
def test_recognize_cancel_pending(mock_bg, tmp_path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    q = _make_recognize_mgr(tmp_path, monkeypatch)
    task_id = q.enqueue(str(video), language="en")["data"]["task_id"]
    assert q.cancel(task_id)["code"] == 0
    task = q.get_task(task_id)
    assert task is not None
    assert task["status"] == TASK_STATUS_FAILED
    assert task["error_message"] == "已取消"


@patch("core.services.subtitle_mgr.transcribe_to_sidecar")
@patch("core.services.subtitle_mgr.run_in_background")
def test_recognize_worker_keeps_task_when_done(mock_bg, mock_transcribe, tmp_path, monkeypatch):
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x")
    mock_transcribe.return_value = {
        "path": str(tmp_path / "a.en.vtt"),
        "language": "en",
        "source": "whisper",
    }
    q = _make_recognize_mgr(tmp_path, monkeypatch)
    mock_bg.side_effect = lambda fn: fn()
    task_id = q.enqueue(str(video), language="en")["data"]["task_id"]
    task = q.get_task(task_id)
    assert task is not None
    assert task["status"] == TASK_STATUS_SUCCESS
    assert task["output_path"] == str(tmp_path / "a.en.vtt")
    mock_transcribe.assert_called_once()


@patch("core.services.subtitle_mgr.run_in_background")
def test_recognize_purge_expired_on_load(mock_bg, tmp_path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    base = tmp_path / "subtitle_recognize"
    base.mkdir(parents=True, exist_ok=True)
    (base / "tasks.json").write_text(
        json.dumps({
            "old0001": {
                "task_id": "old0001",
                "name": "clip",
                "video_path": str(video),
                "language": "en",
                "status": TASK_STATUS_SUCCESS,
                "output_path": str(tmp_path / "clip.en.vtt"),
                "create_time": 1,
                "update_time": 1,
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.services.subtitle_mgr._RECOGNIZE_TASK_RETENTION_SEC",
        3600,
    )
    q = _make_recognize_mgr(tmp_path, monkeypatch)
    assert q.get_task("old0001") is None


@patch("core.services.subtitle_mgr.run_in_background")
def test_recover_processing_to_pending(mock_bg, tmp_path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    base = tmp_path / "subtitle_recognize"
    base.mkdir(parents=True, exist_ok=True)
    (base / "tasks.json").write_text(
        json.dumps({
            "abc1234": {
                "task_id": "abc1234",
                "name": "clip",
                "video_path": str(video),
                "language": "en",
                "status": TASK_STATUS_PROCESSING,
                "create_time": 1,
                "update_time": 1,
            },
        }),
        encoding="utf-8",
    )
    q = _make_recognize_mgr(tmp_path, monkeypatch)
    task = q.get_task("abc1234")
    assert task is not None
    assert task["status"] == TASK_STATUS_PENDING
    mock_bg.assert_called()
