"""Tests for core/utils.py"""

import pytest
import queue
import json
import os
import sys
from datetime import datetime
from flask import Flask, request
from unittest.mock import patch, MagicMock

from core.utils import (_build_shell_command, _read_file_safe, _read_returncode, ok_response,
                        err_response, get_json_body, read_json_from_request, format_time_str, time_to_seconds,
                        decode_url_path, is_allowed_audio_file, is_allowed_pdf_file, get_unique_filepath,
                        convert_standard_cron_weekday_to_apscheduler, validate_and_normalize_path, get_media_url,
                        ensure_directory, get_file_info, convert_to_http_url, run_subprocess_safe,
                        check_cron_will_trigger_today, get_media_duration, save_uploaded_files, cleanup_temp_files,
                        _cleanup_temp_files)

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


@pytest.mark.parametrize("path, expected", [
    ("a%20b", "a b"),
    ("a%25b", "a%b"),
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


@pytest.mark.parametrize("cron_day, aps_day", [
    ("0", "6"),
    ("1", "0"),
    ("6", "5"),
    ("1-5", "0-4"),
    ("0,6", "6,5"),
    ("*", "*"),
    ("*/2", "*/2"),
])
def test_convert_standard_cron_weekday_to_apscheduler(cron_day, aps_day):
    assert convert_standard_cron_weekday_to_apscheduler(cron_day) == aps_day


# --- Test Request Helpers (requires app context) ---


@pytest.fixture
def app():
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
    mock_exists.return_value = False
    path = get_unique_filepath('/tmp', 'file', '.txt')
    assert path == '/tmp/file.txt'
    mock_exists.assert_called_once_with('/tmp/file.txt')


@patch('core.utils.os.path.exists')
def test_get_unique_filepath_exists_once(mock_exists):
    mock_exists.side_effect = [True, False]
    path = get_unique_filepath('/tmp', 'file', '.txt')
    assert path == '/tmp/file_1.txt'
    assert mock_exists.call_count == 2


@patch('core.utils.os.path.exists')
def test_get_unique_filepath_exists_twice(mock_exists):
    mock_exists.side_effect = [True, True, False]
    path = get_unique_filepath('/tmp', 'file', '.txt')
    assert path == '/tmp/file_2.txt'
    assert mock_exists.call_count == 3


@patch('core.utils.os.path.exists', return_value=True)
@patch('core.utils.os.path.isfile', return_value=True)
@patch('core.utils.os.path.isabs', return_value=True)
@patch('core.utils.os.path.abspath', side_effect=lambda p: p)
def test_validate_and_normalize_path_ok(mock_abspath, mock_isabs, mock_isfile, mock_exists):
    path, err = validate_and_normalize_path('/mnt/file.txt', base_dir='/mnt')
    assert err is None
    assert path == '/mnt/file.txt'


@patch('core.utils.os.path.exists', return_value=False)
def test_validate_and_normalize_path_not_exists(mock_exists):
    # 使用允许目录内的路径进行测试
    path, err = validate_and_normalize_path('/opt/my_todo/data/nonexistent.txt')
    assert err == "文件不存在"
    assert path is None


@patch('core.utils.os.path.exists', return_value=True)
@patch('core.utils.os.path.isfile', return_value=False)
def test_validate_and_normalize_path_not_a_file(mock_isfile, mock_exists):
    # 使用允许目录内的路径进行测试
    path, err = validate_and_normalize_path('/opt/my_todo/data/a_directory', must_be_file=True)
    assert err == "路径不是文件"
    assert path is None


@patch('core.utils._get_media_server_url', return_value="http://localhost:8000")
def test_get_media_url(mock_get_url):
    url = get_media_url('/mnt/music/song.mp3')
    assert url == "http://localhost:8000/api/media/files/mnt/music/song.mp3"


@patch('core.utils.os.makedirs')
def test_ensure_directory(mock_makedirs):
    ensure_directory('/tmp/new_dir')
    mock_makedirs.assert_called_once_with('/tmp/new_dir', exist_ok=True)


@patch('core.utils.os.path.exists', return_value=True)
@patch('core.utils.os.stat')
def test_get_file_info(mock_stat, mock_exists):
    mock_stat.return_value.st_size = 1024
    mock_stat.return_value.st_mtime = 1234567890
    info = get_file_info('/path/to/file.txt')
    assert info == {
        "name": "file.txt",
        "path": "/path/to/file.txt",
        "size": 1024,
        "modified": 1234567890,
    }


@patch('core.utils.os.path.exists', return_value=True)
@patch('core.utils.get_media_url', return_value='http://media/url')
def test_convert_to_http_url_local_path(mock_get_media_url, mock_exists):
    url = convert_to_http_url('/mnt/file.mp3')
    assert url == 'http://media/url'


def test_convert_to_http_url_http_url():
    url = convert_to_http_url('http://example.com/file.mp3')
    assert url == 'http://example.com/file.mp3'


# --- Test Request Helpers (stream read) ---


def test_read_json_from_request_reads_stream(app):
    payload = {"a": 1}
    raw = json.dumps(payload).encode("utf-8")

    class _Stream:

        def __init__(self, b):
            self._b = b

        def read(self, n=None):
            return self._b

    with app.test_request_context(data=raw, content_type="application/json"):
        request.stream = _Stream(raw)
        assert read_json_from_request() == payload


# --- Test validate_and_normalize_path edge cases ---


def test_validate_and_normalize_path_rejects_path_traversal():
    path, err = validate_and_normalize_path("../etc/passwd")
    assert path is None
    assert "Path traversal" in err


@patch('core.utils.os.path.isabs', return_value=False)
@patch('core.utils.os.path.abspath', side_effect=lambda p: p)
@patch('core.utils.os.path.exists', return_value=True)
@patch('core.utils.os.path.isfile', return_value=True)
@patch('core.utils.os.path.join', side_effect=lambda a, b: f"{a}/{b}")
def test_validate_and_normalize_path_relative_path_ok(mock_join, mock_isfile, mock_exists, mock_abspath, mock_isabs):
    path, err = validate_and_normalize_path("ext_base/a.mp3", base_dir="/mnt")
    assert err is None
    assert path.startswith("/mnt/")


# --- Test Cron Helpers (check_cron_will_trigger_today) ---


def test_check_cron_will_trigger_today_invalid_returns_false():
    assert check_cron_will_trigger_today("bad cron") is False


@patch('core.utils.datetime')
def test_check_cron_will_trigger_today_true(mock_datetime):
    now = datetime(2023, 1, 1, 12, 0, 0)
    mock_datetime.now.return_value = now
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    assert check_cron_will_trigger_today("* * * * *") is True


@patch('core.utils.datetime')
def test_check_cron_will_trigger_today_false(mock_datetime):
    now = datetime(2023, 1, 1, 12, 0, 0)  # Sunday
    mock_datetime.now.return_value = now
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    assert check_cron_will_trigger_today("* * * * 1") is False  # Monday


# --- Test Subprocess Helpers ---


@patch('core.utils._run_with_os_system')
def test_run_subprocess_safe_ok(mock_run_with_os):

    def side_effect(cmd, timeout, env, cwd, result_q, error_q):
        result_q.put((0, "output", ""))

    mock_run_with_os.side_effect = side_effect
    returncode, stdout, stderr = run_subprocess_safe(['echo', 'hello'])
    assert returncode == 0
    assert stdout == "output"
    assert stderr == ""


@patch('core.utils._run_with_os_system')
def test_run_subprocess_safe_timeout(mock_run_with_os):

    def side_effect(cmd, timeout, env, cwd, result_q, error_q):
        import time
        time.sleep(timeout + 0.2)

    mock_run_with_os.side_effect = side_effect
    with pytest.raises(TimeoutError):
        run_subprocess_safe(['sleep', '10'], timeout=0.1)


@patch('core.utils._run_with_os_system')
def test_run_subprocess_safe_error(mock_run_with_os):

    def side_effect(cmd, timeout, env, cwd, result_q, error_q):
        error_q.put(ValueError("test error"))

    mock_run_with_os.side_effect = side_effect
    with pytest.raises(ValueError, match="test error"):
        run_subprocess_safe(['some', 'command'])


# --- Test Subprocess Internal Helpers ---


def test_read_file_safe_reads_content(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("hello")
    assert _read_file_safe(str(p)) == "hello"


def test_read_file_safe_returns_empty_on_error():
    assert _read_file_safe("/nonexistent/path") == ""
    assert _read_file_safe(None) == ""


def test_read_returncode_reads_from_file(tmp_path):
    p = tmp_path / "rc.txt"
    p.write_text("123")
    assert _read_returncode(str(p), 999) == 123


def test_read_returncode_falls_back_to_system_rc(tmp_path):
    expected_rc = 999 >> 8 if sys.platform != 'win32' else 999
    assert _read_returncode(str(tmp_path / "nonexistent.txt"), 999) == expected_rc
    p = tmp_path / "rc.txt"
    p.write_text("abc")
    assert _read_returncode(str(p), 999) == expected_rc


@patch('core.utils.os.unlink')
def test_cleanup_temp_files_old(mock_unlink):
    """测试旧的 _cleanup_temp_files 函数（向后兼容）"""
    _cleanup_temp_files(["/tmp/a", "/tmp/b", None])
    assert mock_unlink.call_count == 2
    mock_unlink.assert_any_call("/tmp/a")
    mock_unlink.assert_any_call("/tmp/b")


@patch('core.utils.os.unlink', side_effect=OSError("Permission denied"))
def test_cleanup_temp_files_old_ignores_errors(mock_unlink):
    """测试旧的 _cleanup_temp_files 函数忽略错误（向后兼容）"""
    _cleanup_temp_files(["/tmp/a"])


def test_save_uploaded_files_to_temp_dir(tmp_path):
    """测试保存上传文件到临时目录"""
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    
    # 创建模拟文件对象
    file1 = FileStorage(stream=BytesIO(b'file1 content'), filename='test1.jpg')
    file2 = FileStorage(stream=BytesIO(b'file2 content'), filename='test2.jpg')
    files = [file1, file2]
    
    file_paths, temp_dir = save_uploaded_files(files, temp_prefix='test_')
    
    assert file_paths is not None
    assert temp_dir is not None
    assert len(file_paths) == 2
    assert all(os.path.exists(path) for path in file_paths)
    assert os.path.exists(temp_dir)
    
    # 验证文件内容
    with open(file_paths[0], 'rb') as f:
        assert f.read() == b'file1 content'
    with open(file_paths[1], 'rb') as f:
        assert f.read() == b'file2 content'
    
    # 清理
    cleanup_temp_files(temp_dir, file_paths)


def test_save_uploaded_files_to_target_dir(tmp_path):
    """测试保存上传文件到指定目录"""
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    
    target_dir = str(tmp_path / "upload")
    file1 = FileStorage(stream=BytesIO(b'content'), filename='test.jpg')
    
    file_paths, directory = save_uploaded_files([file1], target_dir=target_dir)
    
    assert file_paths is not None
    assert directory == target_dir
    assert len(file_paths) == 1
    assert os.path.exists(file_paths[0])
    assert os.path.exists(target_dir)


def test_save_uploaded_files_empty_files(tmp_path):
    """测试保存空文件列表"""
    file_paths, temp_dir = save_uploaded_files([], temp_prefix='test_')
    
    assert file_paths is None
    assert temp_dir is None


def test_save_uploaded_files_no_valid_files(tmp_path):
    """测试保存没有有效文件名的文件"""
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    
    # 创建没有文件名的文件对象
    file1 = FileStorage(stream=BytesIO(b'content'), filename='')
    files = [file1]
    
    file_paths, temp_dir = save_uploaded_files(files, temp_prefix='test_')
    
    assert file_paths is None
    assert temp_dir is None


def test_save_uploaded_files_exception(tmp_path, monkeypatch):
    """测试保存文件时发生异常"""
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    
    file1 = FileStorage(stream=BytesIO(b'content'), filename='test.jpg')
    
    # Mock os.makedirs 抛出异常
    def mock_makedirs(*args, **kwargs):
        raise OSError("Permission denied")
    
    monkeypatch.setattr('core.utils.os.makedirs', mock_makedirs)
    
    file_paths, temp_dir = save_uploaded_files([file1], target_dir=str(tmp_path / "upload"))
    
    assert file_paths is None
    assert temp_dir is None


def test_cleanup_temp_files(tmp_path):
    """测试清理临时文件"""
    import tempfile
    
    # 创建临时目录和文件
    temp_dir = tempfile.mkdtemp(prefix='test_cleanup_')
    file1 = os.path.join(temp_dir, 'file1.txt')
    file2 = os.path.join(temp_dir, 'file2.txt')
    
    with open(file1, 'w') as f:
        f.write('content1')
    with open(file2, 'w') as f:
        f.write('content2')
    
    # 清理文件
    cleanup_temp_files(temp_dir, [file1, file2])
    
    # 验证文件已删除
    assert not os.path.exists(file1)
    assert not os.path.exists(file2)
    assert not os.path.exists(temp_dir)


def test_cleanup_temp_files_nonexistent(tmp_path):
    """测试清理不存在的临时文件（应该不抛出异常）"""
    cleanup_temp_files("/nonexistent/dir", ["/nonexistent/file.txt"])


def test_cleanup_temp_files_no_file_paths(tmp_path):
    """测试清理临时目录（不指定文件路径）"""
    import tempfile
    
    temp_dir = tempfile.mkdtemp(prefix='test_cleanup_')
    
    cleanup_temp_files(temp_dir)
    
    # 验证目录已删除
    assert not os.path.exists(temp_dir)


@patch('core.utils.sys.platform', 'linux')
def test_build_shell_command_unix():
    cmd = _build_shell_command(['echo', 'hello world'], None, '/tmp', 'out.txt', 'err.txt', 'rc.txt')
    assert "cd /tmp" in cmd
    assert "hello world" in cmd
    assert "> out.txt" in cmd


@patch('core.utils.sys.platform', 'win32')
def test_build_shell_command_windows():
    cmd = _build_shell_command(['echo', 'hello world'], None, 'C:\\Temp', 'out.txt', 'err.txt', 'rc.txt')
    assert 'cd /d' in cmd and "echo 'hello world'" in cmd and "> out.txt" in cmd


# --- Test get_media_duration ---


@patch('core.utils.threading.Thread')
@patch('core.utils.tempfile.NamedTemporaryFile')
@patch('core.utils.os.system')
@patch('core.utils.open')
def test_get_media_duration_success(mock_open, mock_system, mock_tempfile, mock_thread):
    mock_system.return_value = 0
    mock_tempfile.return_value.__enter__.return_value.name = '/tmp/fake'
    mock_open.return_value.__enter__.return_value.read.return_value = "123.45"

    def run_target(target, **kwargs):
        target()

    mock_thread.return_value = MagicMock(start=lambda: run_target(target=mock_thread.call_args.kwargs['target']),
                                         join=lambda timeout: None,
                                         is_alive=lambda: False)

    assert get_media_duration('fake.mp3') == 123


@patch('core.utils.threading.Thread')
@patch('core.utils.tempfile.NamedTemporaryFile')
@patch('core.utils.os.system')
@patch('core.utils.open')
def test_get_media_duration_failure(mock_open, mock_system, mock_tempfile, mock_thread):
    mock_system.return_value = 1 << 8  # return code 1
    mock_tempfile.return_value.__enter__.return_value.name = '/tmp/fake'
    mock_open.return_value.__enter__.return_value.read.return_value = ""

    def run_target(target, **kwargs):
        target()

    mock_thread.return_value = MagicMock(start=lambda: run_target(target=mock_thread.call_args.kwargs['target']),
                                         join=lambda timeout: None,
                                         is_alive=lambda: False)

    assert get_media_duration('fake.mp3') is None


# --- Test save_uploaded_files and cleanup_temp_files ---


def test_save_uploaded_files_to_temp_dir(tmp_path):
    """测试保存上传文件到临时目录"""
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    
    # 创建模拟文件对象
    file1 = FileStorage(stream=BytesIO(b'file1 content'), filename='test1.jpg')
    file2 = FileStorage(stream=BytesIO(b'file2 content'), filename='test2.jpg')
    files = [file1, file2]
    
    file_paths, temp_dir = save_uploaded_files(files, temp_prefix='test_')
    
    assert file_paths is not None
    assert temp_dir is not None
    assert len(file_paths) == 2
    assert all(os.path.exists(path) for path in file_paths)
    assert os.path.exists(temp_dir)
    
    # 验证文件内容
    with open(file_paths[0], 'rb') as f:
        assert f.read() == b'file1 content'
    with open(file_paths[1], 'rb') as f:
        assert f.read() == b'file2 content'
    
    # 清理
    cleanup_temp_files(temp_dir, file_paths)


def test_save_uploaded_files_to_target_dir(tmp_path):
    """测试保存上传文件到指定目录"""
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    
    target_dir = str(tmp_path / "upload")
    file1 = FileStorage(stream=BytesIO(b'content'), filename='test.jpg')
    
    file_paths, directory = save_uploaded_files([file1], target_dir=target_dir)
    
    assert file_paths is not None
    assert directory == target_dir
    assert len(file_paths) == 1
    assert os.path.exists(file_paths[0])
    assert os.path.exists(target_dir)


def test_save_uploaded_files_empty_files(tmp_path):
    """测试保存空文件列表"""
    file_paths, temp_dir = save_uploaded_files([], temp_prefix='test_')
    
    assert file_paths is None
    assert temp_dir is None


def test_save_uploaded_files_no_valid_files(tmp_path):
    """测试保存没有有效文件名的文件"""
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    
    # 创建没有文件名的文件对象
    file1 = FileStorage(stream=BytesIO(b'content'), filename='')
    files = [file1]
    
    file_paths, temp_dir = save_uploaded_files(files, temp_prefix='test_')
    
    assert file_paths is None
    assert temp_dir is None


def test_save_uploaded_files_exception(tmp_path, monkeypatch):
    """测试保存文件时发生异常"""
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    
    file1 = FileStorage(stream=BytesIO(b'content'), filename='test.jpg')
    
    # Mock os.makedirs 抛出异常
    def mock_makedirs(*args, **kwargs):
        raise OSError("Permission denied")
    
    monkeypatch.setattr('core.utils.os.makedirs', mock_makedirs)
    
    file_paths, temp_dir = save_uploaded_files([file1], target_dir=str(tmp_path / "upload"))
    
    assert file_paths is None
    assert temp_dir is None


def test_cleanup_temp_files(tmp_path):
    """测试清理临时文件"""
    import tempfile
    
    # 创建临时目录和文件
    temp_dir = tempfile.mkdtemp(prefix='test_cleanup_')
    file1 = os.path.join(temp_dir, 'file1.txt')
    file2 = os.path.join(temp_dir, 'file2.txt')
    
    with open(file1, 'w') as f:
        f.write('content1')
    with open(file2, 'w') as f:
        f.write('content2')
    
    # 清理文件
    cleanup_temp_files(temp_dir, [file1, file2])
    
    # 验证文件已删除
    assert not os.path.exists(file1)
    assert not os.path.exists(file2)
    assert not os.path.exists(temp_dir)


def test_cleanup_temp_files_nonexistent(tmp_path):
    """测试清理不存在的临时文件（应该不抛出异常）"""
    cleanup_temp_files("/nonexistent/dir", ["/nonexistent/file.txt"])


def test_cleanup_temp_files_no_file_paths(tmp_path):
    """测试清理临时目录（不指定文件路径）"""
    import tempfile
    
    temp_dir = tempfile.mkdtemp(prefix='test_cleanup_')
    
    cleanup_temp_files(temp_dir)
    
    # 验证目录已删除
    assert not os.path.exists(temp_dir)
