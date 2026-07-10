import os
import pytest
from unittest.mock import patch, MagicMock
from core.services.tools.audio_convert_mgr import AudioConvertMgr, AudioConvertTask
from core.config import TASK_STATUS_PENDING, TASK_STATUS_PROCESSING, TASK_STATUS_SUCCESS, TASK_STATUS_FAILED


@pytest.fixture
def convert_mgr(tmp_path, monkeypatch):
    """Provides a clean AudioConvertMgr instance using a temporary directory."""
    monkeypatch.setattr('core.services.tools.audio_convert_mgr.AUDIO_CONVERT_BASE_DIR', str(tmp_path))
    mgr = AudioConvertMgr()
    mgr._tasks = {}  # Ensure no tasks from previous tests
    return mgr


def test_create_task_success(convert_mgr: AudioConvertMgr, monkeypatch):
    monkeypatch.setattr('core.services.tools.audio_convert_mgr._spawn', lambda fn: None)
    """Test successful creation of a conversion task with specified parameters."""
    name = "My Test Task"
    output_dir = "test_output"
    overwrite = False

    code, msg, task_id = convert_mgr.create_task(name=name, output_dir=output_dir, overwrite=overwrite)

    assert code == 0
    assert msg == "任务创建成功"
    assert task_id is not None

    task = convert_mgr.get_task(task_id)
    assert task is not None
    assert task['name'] == name
    assert task['output_dir'] == output_dir
    assert task['overwrite'] == overwrite
    assert task['status'] == TASK_STATUS_PENDING
    assert task['directory'] is None
    assert task['progress'] is None


def test_create_task_with_defaults(convert_mgr: AudioConvertMgr, monkeypatch):
    monkeypatch.setattr('core.services.tools.audio_convert_mgr._spawn', lambda fn: None)
    """Test task creation using default values for name, output_dir, and overwrite."""
    code, msg, task_id = convert_mgr.create_task()

    assert code == 0
    assert task_id is not None

    task = convert_mgr.get_task(task_id)
    assert task is not None
    assert task['name'] is not None
    assert task['output_dir'] == 'mp3'
    assert task['overwrite'] is True
    assert task['status'] == TASK_STATUS_PENDING


def test_create_task_empty_output_dir_uses_default(convert_mgr: AudioConvertMgr):
    """output_dir 为空或空格时回退为 mp3"""
    code, _, task_id = convert_mgr.create_task(output_dir="   ")
    assert code == 0
    assert convert_mgr.get_task(task_id)['output_dir'] == 'mp3'


def test_update_task_empty_output_dir_keeps_previous(convert_mgr: AudioConvertMgr, monkeypatch):
    monkeypatch.setattr('core.services.tools.audio_convert_mgr._spawn', lambda fn: None)
    _, _, task_id = convert_mgr.create_task()
    code, msg = convert_mgr.update_task(task_id, output_dir="   ")
    assert code == 0
    assert convert_mgr.get_task(task_id)['output_dir'] == 'mp3'


def test_update_task_no_fields_fails(convert_mgr: AudioConvertMgr):
    _, _, task_id = convert_mgr.create_task()
    code, msg = convert_mgr.update_task(task_id)
    assert code == -1
    assert "没有提供" in msg


def test_scan_skips_getsize_error(convert_mgr: AudioConvertMgr, tmp_path, monkeypatch):
    """扫描文件时 getsize 失败不影响入库"""
    monkeypatch.setattr("os.path.getsize", lambda p: (_ for _ in ()).throw(OSError("perm")))
    (tmp_path / "a.mp3").write_bytes(b"x")
    task = AudioConvertTask(task_id="t1", name="n", directory=str(tmp_path))
    convert_mgr._tasks["t1"] = task
    convert_mgr._scan_and_bind_files(task)
    assert "size" not in (task.file_status or {}).get(str(tmp_path / "a.mp3"), {})


def test_convert_file_to_mp3_generic_exception(convert_mgr: AudioConvertMgr, tmp_path):
    """_convert_file_to_mp3 当 run_subprocess_safe 抛非 Timeout/FileNotFound 异常时返回 False"""
    in_f = tmp_path / "a.wav"
    in_f.write_bytes(b"x")
    out_f = tmp_path / "out" / "a.mp3"
    with patch.object(convert_mgr, "_ensure_output_directory", return_value=(True, None)):
        with patch("core.services.tools.audio_convert_mgr.run_subprocess_safe", side_effect=RuntimeError("boom")):
            ok, err = convert_mgr._convert_file_to_mp3(str(in_f), str(out_f))
    assert ok is False
    assert err is not None
    assert "boom" in err or "失败" in err


def test_update_file_duration_async_duration_none(convert_mgr: AudioConvertMgr, monkeypatch):
    """_update_file_duration_async 当 get_media_duration 返回 None 时不更新"""
    monkeypatch.setattr("core.services.tools.audio_convert_mgr.get_media_duration", lambda p: None)
    _, _, task_id = convert_mgr.create_task()
    task = convert_mgr._get_task(task_id)
    task.file_status = {"/f.mp3": {"status": "pending"}}
    convert_mgr._update_file_duration_async(task_id, "/f.mp3")
    assert task.file_status["/f.mp3"].get("duration") is None


def test_ensure_output_directory_os_error(convert_mgr: AudioConvertMgr, tmp_path, monkeypatch):
    """_ensure_output_directory 当 makedirs 抛 OSError 时返回 False"""
    monkeypatch.setattr("os.path.exists", lambda p: False)
    monkeypatch.setattr("os.makedirs", lambda p, **kw: (_ for _ in ()).throw(OSError("disk full")))
    ok, err = convert_mgr._ensure_output_directory(str(tmp_path / "newdir"))
    assert ok is False
    assert err is not None


def test_update_task_success(convert_mgr: AudioConvertMgr, tmp_path, monkeypatch):
    monkeypatch.setattr('core.services.tools.audio_convert_mgr._spawn', lambda fn: None)
    """Test successful update of a task's properties."""
    _, _, task_id = convert_mgr.create_task()
    new_name = "Updated Task Name"
    new_dir = tmp_path

    code, msg = convert_mgr.update_task(task_id, name=new_name, directory=str(new_dir))

    assert code == 0
    assert msg == "任务更新成功"

    task = convert_mgr.get_task(task_id)
    assert task['name'] == new_name
    assert task['directory'] == str(new_dir)


def test_update_task_not_processing(convert_mgr: AudioConvertMgr):
    """Test that a task cannot be updated while it is processing."""
    _, _, task_id = convert_mgr.create_task()
    task = convert_mgr._get_task(task_id)
    task.status = TASK_STATUS_PROCESSING

    code, msg = convert_mgr.update_task(task_id, name="New Name")

    assert code == -1
    assert "任务正在处理中" in msg


def test_delete_task_success(convert_mgr: AudioConvertMgr):
    """Test successful deletion of a task."""
    _, _, task_id = convert_mgr.create_task()
    code, msg = convert_mgr.delete_task(task_id)

    assert code == 0
    assert msg == "任务删除成功"
    assert convert_mgr.get_task(task_id) is None


def test_delete_task_processing(convert_mgr: AudioConvertMgr):
    """Test that a task cannot be deleted while it is processing."""
    _, _, task_id = convert_mgr.create_task()
    task = convert_mgr._get_task(task_id)
    task.status = TASK_STATUS_PROCESSING

    code, msg = convert_mgr.delete_task(task_id)

    assert code == -1
    assert "任务正在处理中" in msg


@patch('core.services.tools.audio_convert_mgr.AudioConvertMgr._run_task_async')
def test_start_task_success(mock_run_task_async, convert_mgr: AudioConvertMgr, tmp_path):
    """Test that a task can be started successfully."""
    _, _, task_id = convert_mgr.create_task()
    convert_mgr.update_task(task_id, directory=str(tmp_path))

    code, msg = convert_mgr.start_task(task_id)

    assert code == 0
    assert msg == "转码任务已启动"
    mock_run_task_async.assert_called_once_with(task_id, convert_mgr._run_convert)


def test_start_task_already_processing(convert_mgr: AudioConvertMgr):
    """Test that a task cannot be started if it is already processing."""
    _, _, task_id = convert_mgr.create_task()
    task = convert_mgr._get_task(task_id)
    task.status = TASK_STATUS_PROCESSING

    code, msg = convert_mgr.start_task(task_id)

    assert code == -1
    assert "任务正在处理中" in msg


def test_start_task_no_directory(convert_mgr: AudioConvertMgr):
    """Test that a task cannot be started without a directory."""
    _, _, task_id = convert_mgr.create_task()

    code, msg = convert_mgr.start_task(task_id)

    assert code == -1
    assert "请先设置转码目录" in msg


def test_scan_media_files(tmp_path):
    """Test the scanning of media files in a directory."""
    mgr = AudioConvertMgr()
    # Create dummy files
    (tmp_path / "audio.mp3").touch()
    (tmp_path / "video.mkv").touch()
    (tmp_path / "text.txt").touch()
    output_dir = tmp_path / "mp3"
    output_dir.mkdir()
    (output_dir / "existing.mp3").touch()

    media_files = mgr._scan_media_files(str(tmp_path), "mp3")

    assert len(media_files) == 2
    assert str(tmp_path / "audio.mp3") in media_files
    assert str(tmp_path / "video.mkv") in media_files
    assert str(tmp_path / "text.txt") not in media_files


@patch('core.services.tools.audio_convert_mgr.run_subprocess_safe')
def test_convert_directory_success(mock_run_subprocess, convert_mgr: AudioConvertMgr, tmp_path, monkeypatch):
    """Test a successful directory conversion."""
    monkeypatch.setattr('core.services.tools.audio_convert_mgr._spawn', lambda fn: None)
    mock_run_subprocess.return_value = (0, "", "")
    # Create dummy media files
    (tmp_path / "song1.wav").touch()
    (tmp_path / "song2.flac").touch()

    _, _, task_id = convert_mgr.create_task()
    convert_mgr.update_task(task_id, directory=str(tmp_path))
    task = convert_mgr._get_task(task_id)

    # Mock os.path.exists to simulate output file creation
    original_exists = os.path.exists

    def mock_exists(path):
        if 'song1.mp3' in path or 'song2.mp3' in path:
            return True
        return original_exists(path)

    with patch('os.path.exists', side_effect=mock_exists), patch('os.path.isfile', side_effect=mock_exists):
        convert_mgr._run_convert(task)

    assert task.status == TASK_STATUS_SUCCESS
    assert task.progress['processed'] == 2
    assert task.progress['total'] == 2


@patch('core.services.tools.audio_convert_mgr.run_subprocess_safe')
def test_convert_directory_with_failure(mock_run_subprocess, convert_mgr: AudioConvertMgr, tmp_path, monkeypatch):
    """Test a directory conversion where one file fails."""
    monkeypatch.setattr('core.services.tools.audio_convert_mgr._spawn', lambda fn: None)
    mock_run_subprocess.side_effect = [
        (0, "", ""),  # Success for song1
        (1, "", "error"),  # Failure for song2
    ]
    (tmp_path / "song1.wav").touch()
    (tmp_path / "song2.flac").touch()

    _, _, task_id = convert_mgr.create_task()
    convert_mgr.update_task(task_id, directory=str(tmp_path))
    task = convert_mgr._get_task(task_id)

    original_exists = os.path.exists

    def mock_exists(path):
        if 'song1.mp3' in path:
            return True  # Pretend the first file was created
        return original_exists(path)

    with patch('os.path.exists', side_effect=mock_exists):
        convert_mgr._run_convert(task)

    assert task.status == TASK_STATUS_FAILED
    assert task.progress['processed'] == 2
    assert "部分文件转换失败" in task.error_message


def test_update_task_output_and_overwrite(convert_mgr: AudioConvertMgr):
    """Test updating output_dir and overwrite properties."""
    _, _, task_id = convert_mgr.create_task()

    code, msg = convert_mgr.update_task(task_id, output_dir="new_mp3", overwrite=False)

    assert code == 0
    task = convert_mgr.get_task(task_id)
    assert task['output_dir'] == "new_mp3"
    assert task['overwrite'] is False


def test_convert_directory_no_files(convert_mgr: AudioConvertMgr, tmp_path, monkeypatch):
    """Test directory conversion with no media files."""
    monkeypatch.setattr('core.services.tools.audio_convert_mgr._spawn', lambda fn: None)
    _, _, task_id = convert_mgr.create_task()
    convert_mgr.update_task(task_id, directory=str(tmp_path))
    task = convert_mgr._get_task(task_id)

    convert_mgr._run_convert(task)

    assert task.status == TASK_STATUS_SUCCESS
    assert task.progress['total'] == 0


def test_convert_directory_stopped(convert_mgr: AudioConvertMgr, tmp_path, monkeypatch):
    """Test stopping a directory conversion midway."""
    (tmp_path / "song1.wav").touch()

    # avoid spawning gevent greenlet during unit tests
    monkeypatch.setattr('core.services.tools.audio_convert_mgr._spawn', lambda fn: None)

    _, _, task_id = convert_mgr.create_task()
    convert_mgr.update_task(task_id, directory=str(tmp_path))
    task = convert_mgr._get_task(task_id)

    convert_mgr._stop_flags[task_id] = True
    convert_mgr._run_convert(task)

    assert task.status == TASK_STATUS_FAILED
    assert "任务已被停止" in task.error_message


def test_ensure_output_directory_makedirs_error(convert_mgr: AudioConvertMgr, tmp_path):
    with patch('os.makedirs', side_effect=PermissionError('nope')):
        ok, err = convert_mgr._ensure_output_directory(str(tmp_path / 'out'))
    assert ok is False
    assert err


def test_convert_file_to_mp3_timeout(convert_mgr: AudioConvertMgr, tmp_path):
    in_f = tmp_path / 'a.wav'
    in_f.write_bytes(b'x')
    out_f = tmp_path / 'out' / 'a.mp3'

    with patch.object(convert_mgr, '_ensure_output_directory', return_value=(True, None)):
        with patch('core.services.tools.audio_convert_mgr.run_subprocess_safe', side_effect=TimeoutError('t')):
            ok, err = convert_mgr._convert_file_to_mp3(str(in_f), str(out_f))

    assert ok is False
    assert err == '转换超时'


def test_convert_file_to_mp3_ffmpeg_not_found(convert_mgr: AudioConvertMgr, tmp_path):
    in_f = tmp_path / 'a.wav'
    in_f.write_bytes(b'x')
    out_f = tmp_path / 'out' / 'a.mp3'

    with patch.object(convert_mgr, '_ensure_output_directory', return_value=(True, None)):
        with patch('core.services.tools.audio_convert_mgr.run_subprocess_safe', side_effect=FileNotFoundError('ffmpeg')):
            ok, err = convert_mgr._convert_file_to_mp3(str(in_f), str(out_f))

    assert ok is False
    assert 'ffmpeg 未找到' in err


def test_convert_file_to_mp3_returncode_0_but_output_missing(convert_mgr: AudioConvertMgr, tmp_path):
    in_f = tmp_path / 'a.wav'
    in_f.write_bytes(b'x')
    out_f = tmp_path / 'out' / 'a.mp3'

    with patch.object(convert_mgr, '_ensure_output_directory', return_value=(True, None)):
        with patch('core.services.tools.audio_convert_mgr.run_subprocess_safe', return_value=(0, '', '')):
            with patch('os.path.exists', return_value=False):
                ok, err = convert_mgr._convert_file_to_mp3(str(in_f), str(out_f))

    assert ok is False
    assert err is not None
    assert err


def test_convert_file_to_mp3_returncode_nonzero_uses_stderr(convert_mgr: AudioConvertMgr, tmp_path):
    in_f = tmp_path / 'a.wav'
    in_f.write_bytes(b'x')
    out_f = tmp_path / 'out' / 'a.mp3'

    with patch.object(convert_mgr, '_ensure_output_directory', return_value=(True, None)):
        with patch('core.services.tools.audio_convert_mgr.run_subprocess_safe', return_value=(1, '', 'bad')):
            ok, err = convert_mgr._convert_file_to_mp3(str(in_f), str(out_f))

    assert ok is False
    assert err == 'bad'


def test_update_file_duration_async_sets_duration(convert_mgr: AudioConvertMgr):
    task = AudioConvertTask(task_id='t1', name='n1')
    task.file_status = {'/tmp/a.mp3': {'status': 'pending'}}
    convert_mgr._tasks['t1'] = task

    with patch('core.services.tools.audio_convert_mgr.get_media_duration', return_value=12.5):
        convert_mgr._update_file_duration_async('t1', '/tmp/a.mp3')

    assert task.file_status['/tmp/a.mp3']['duration'] == 12.5


def test_get_convert_output_file_success(convert_mgr: AudioConvertMgr, tmp_path):
    task_id = "t-download"
    upload_dir = tmp_path / task_id / "upload"
    upload_dir.mkdir(parents=True)
    output_dir = tmp_path / task_id / "result" / "mp3"
    output_dir.mkdir(parents=True)
    input_file = upload_dir / "source.wav"
    input_file.write_bytes(b"x")
    output_file = output_dir / "source.mp3"
    output_file.write_bytes(b"mp3")

    task = AudioConvertTask(
        task_id=task_id,
        name="download",
        source_type="upload",
        output_dir="mp3",
        resolved_output_dir=str(output_dir),
        file_status={
            str(input_file): {
                "status": "success",
                "output_path": str(output_file),
            }
        },
    )
    convert_mgr._tasks[task.task_id] = task

    path, err = convert_mgr.get_convert_output_file(task.task_id, str(output_file))
    assert err is None
    assert path == str(output_file)


def test_get_convert_output_file_rejects_source_file(convert_mgr: AudioConvertMgr, tmp_path):
    task_id = "t-bad-output"
    upload_dir = tmp_path / task_id / "upload"
    upload_dir.mkdir(parents=True)
    output_dir = tmp_path / task_id / "result" / "mp3"
    output_dir.mkdir(parents=True)
    input_file = upload_dir / "source.mp4"
    input_file.write_bytes(b"x")

    task = AudioConvertTask(
        task_id=task_id,
        name="bad",
        source_type="upload",
        output_dir="mp3",
        resolved_output_dir=str(output_dir),
        file_status={
            str(input_file): {
                "status": "success",
                "output_path": str(input_file),
            }
        },
    )
    convert_mgr._tasks[task.task_id] = task

    path, err = convert_mgr.get_convert_output_file(task.task_id, str(output_dir / "missing.mp3"))
    assert path is None
    assert err == "文件不存在"


def test_get_convert_output_file_not_ready(convert_mgr: AudioConvertMgr, tmp_path):
    input_file = tmp_path / "source.wav"
    input_file.write_bytes(b"x")
    task = AudioConvertTask(
        task_id="t-pending",
        name="pending",
        file_status={str(input_file): {"status": "pending"}},
    )
    convert_mgr._tasks[task.task_id] = task

    pending_output = convert_mgr._expected_output_path(task, str(input_file))
    path, err = convert_mgr.get_convert_output_file(task.task_id, pending_output or str(tmp_path / "x.mp3"))
    assert path is None
    assert err == "文件不存在"
