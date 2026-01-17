"""Tests for core/utils.py"""

import pytest
from flask import Flask, request
from unittest.mock import patch, MagicMock

from core.utils import (ok_response, err_response, get_json_body, read_json_from_request, format_time_str,
                        time_to_seconds, decode_url_path, is_allowed_audio_file, is_allowed_pdf_file,
                        get_unique_filepath, convert_standard_cron_weekday_to_apscheduler)

# --- Test Response Helpers ---


def test_ok_response():
    """Test ok_response for correct structure."""
    assert ok_response() == {"code": 0, "msg": "ok", "data": None}
    assert ok_response(data={"foo": "bar"}) == {"code": 0, "msg": "ok", "data": {"foo": "bar"}}


def test_err_response():
    """Test err_response for correct structure."""
    assert err_response("An error") == {"code": -1, "msg": "An error"}


# --- Test Time Helpers ---


@pytest.mark.parametrize("seconds, expected", [
    (3661, "01:01:01"),
    (61, "00:01:01"),
    (59, "00:00:59"),
    (0, "00:00:00"),
    (3600.5, "01:00:00"),
])
def test_format_time_str(seconds, expected):
    assert format_time_str(seconds) == expected


@pytest.mark.parametrize("time_str, expected", [
    ("01:01:01", 3661),
    ("00:01:01", 61),
    ("00:00:59", 59),
    ("00:00:00", 0),
    ("10:00:00", 36000),
])
def test_time_to_seconds(time_str, expected):
    assert time_to_seconds(time_str) == expected


# --- Test URL/Path Helpers ---


@pytest.mark.parametrize(
    "path, expected",
    [
        ("a%20b", "a b"),
        ("a%25b", "a%b"),  # Already decoded once
        ("a b", "a b"),
        ("%E4%BD%A0%E5%A5%BD", "你好"),
    ])
def test_decode_url_path(path, expected):
    assert decode_url_path(path) == expected


# --- Test File Type Checkers ---


@pytest.mark.parametrize("filename, expected", [
    ("test.mp3", True),
    ("test.WAV", True),
    ("test.txt", False),
    ("test", False),
])
def test_is_allowed_audio_file(filename, expected):
    assert is_allowed_audio_file(filename) == expected


@pytest.mark.parametrize("filename, expected", [
    ("document.pdf", True),
    ("document.PDF", True),
    ("document.docx", False),
])
def test_is_allowed_pdf_file(filename, expected):
    assert is_allowed_pdf_file(filename) == expected


# --- Test Cron Helpers ---


@pytest.mark.parametrize(
    "cron_day, aps_day",
    [
        ("0", "6"),  # Sunday
        ("1", "0"),  # Monday
        ("6", "5"),  # Saturday
        ("1-5", "0-4"),  # Weekdays
        ("0,6", "6,5"),  # Weekend
        ("*", "*"),
        ("*/2", "*/2"),
    ])
def test_convert_standard_cron_weekday_to_apscheduler(cron_day, aps_day):
    assert convert_standard_cron_weekday_to_apscheduler(cron_day) == aps_day


# --- Test Request Helpers (requires app context) ---


@pytest.fixture
def app():
    """Create a Flask app context for testing request-dependent functions."""
    app = Flask(__name__)
    return app


def test_get_json_body_with_json(app):
    with app.test_request_context(json={"key": "value"}):
        assert get_json_body() == {"key": "value"}


def test_get_json_body_no_json(app):
    with app.test_request_context():
        assert get_json_body() == {}


def test_get_json_body_not_json_content_type(app):
    with app.test_request_context(data="not json", content_type="text/plain"):
        assert get_json_body() == {}


# --- Test Filepath Helpers (requires mocking os) ---


@patch('core.utils.os.path.exists')
def test_get_unique_filepath_does_not_exist(mock_exists):
    """Test get_unique_filepath when the file does not initially exist."""
    mock_exists.return_value = False
    path = get_unique_filepath('/tmp', 'file', '.txt')
    assert path == '/tmp/file.txt'
    mock_exists.assert_called_once_with('/tmp/file.txt')


@patch('core.utils.os.path.exists')
def test_get_unique_filepath_exists_once(mock_exists):
    """Test get_unique_filepath when the file exists once."""
    mock_exists.side_effect = [True, False]
    path = get_unique_filepath('/tmp', 'file', '.txt')
    assert path == '/tmp/file_1.txt'
    assert mock_exists.call_count == 2


@patch('core.utils.os.path.exists')
def test_get_unique_filepath_exists_twice(mock_exists):
    """Test get_unique_filepath when the file and its first variant exist."""
    mock_exists.side_effect = [True, True, False]
    path = get_unique_filepath('/tmp', 'file', '.txt')
    assert path == '/tmp/file_2.txt'
    assert mock_exists.call_count == 3
