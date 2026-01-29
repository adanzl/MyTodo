import os
import json
import pytest
from unittest.mock import patch, mock_open

from core.config import TASK_STATUS_FAILED, TASK_STATUS_PENDING, TASK_STATUS_PROCESSING, TASK_STATUS_SUCCESS
from core.services.audio_merge_mgr import AudioMergeMgr


@pytest.fixture
def merge_mgr(tmp_path, monkeypatch):
    """Provides a clean AudioMergeMgr instance using a temporary directory."""
    monkeypatch.setattr('core.services.audio_merge_mgr.AUDIO_MERGE_BASE_DIR', str(tmp_path))
    mgr = AudioMergeMgr()
    mgr._tasks = {}  # Ensure no tasks from previous tests
    return mgr


def test_create_task_success(merge_mgr: AudioMergeMgr):
    name = "My Merge Task"
    code, msg, task_id = merge_mgr.create_task(name=name)

    assert code == 0
    assert msg == "任务创建成功"
    assert task_id is not None

    task = merge_mgr.get_task(task_id)
    assert task is not None
    assert task['name'] == name
    assert task['status'] == TASK_STATUS_PENDING
    assert task['files'] == []


def test_create_task_with_defaults(merge_mgr: AudioMergeMgr):
    code, msg, task_id = merge_mgr.create_task()

    assert code == 0
    assert task_id is not None

    task = merge_mgr.get_task(task_id)
    assert task is not None
    assert task['name'] is not None
    assert task['status'] == TASK_STATUS_PENDING


@patch('os.path.exists', return_value=True)
@patch('os.path.getsize', return_value=1024)
@patch('core.services.audio_merge_mgr.get_media_duration', return_value=10.0)
def test_add_file_success(mock_get_duration, mock_getsize, mock_exists, merge_mgr: AudioMergeMgr, tmp_path):
    _, _, task_id = merge_mgr.create_task()
    file_path = str(tmp_path / "test.mp3")

    code, msg = merge_mgr.add_file(task_id, file_path, "test.mp3")

    assert code == 0
    assert msg == "文件添加成功"
    task = merge_mgr.get_task(task_id)
    assert len(task['files']) == 1
    assert task['files'][0]['name'] == "test.mp3"


def test_add_file_failures(merge_mgr: AudioMergeMgr, tmp_path):
    _, _, task_id = merge_mgr.create_task()
    task = merge_mgr._get_task(task_id)
    task.status = TASK_STATUS_PROCESSING

    code, msg = merge_mgr.add_file(task_id, "/path/to/file.mp3", "file.mp3")
    assert code == -1
    assert "任务正在处理中" in msg

    task.status = TASK_STATUS_PENDING
    code, msg = merge_mgr.add_file(task_id, "/path/to/nonexistent.mp3", "nonexistent.mp3")
    assert code == -1
    assert "文件不存在" in msg

    file_path = str(tmp_path / "test.txt")
    with open(file_path, "w") as f:
        f.write("test")
    code, msg = merge_mgr.add_file(task_id, file_path, "test.txt")
    assert code == -1
    assert "不支持的文件类型" in msg


def test_read_tasks_from_file_not_exists(merge_mgr: AudioMergeMgr):
    """_read_tasks_from_file 当文件不存在时返回 None"""
    assert merge_mgr._read_tasks_from_file("/nonexistent/path/tasks.json") is None


def test_read_tasks_from_file_invalid_json(merge_mgr: AudioMergeMgr, tmp_path):
    """_read_tasks_from_file 当文件内容非合法 JSON 时返回 None"""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not valid json {", encoding="utf-8")
    assert merge_mgr._read_tasks_from_file(str(bad_file)) is None


def test_validate_file_not_exists(merge_mgr: AudioMergeMgr):
    """_validate_file 当文件不存在时返回错误信息"""
    err = merge_mgr._validate_file("/nonexistent.mp3", "a.mp3")
    assert err is not None
    assert "文件不存在" in err


def test_validate_file_unsupported_extension(merge_mgr: AudioMergeMgr, tmp_path):
    """_validate_file 当扩展名不支持时返回错误信息"""
    f = tmp_path / "a.txt"
    f.write_text("x", encoding="utf-8")
    err = merge_mgr._validate_file(str(f), "a.txt")
    assert err is not None
    assert "不支持" in err


@patch('os.path.exists', return_value=True)
@patch('os.path.getsize', return_value=1024)
@patch('core.services.audio_merge_mgr.get_media_duration', return_value=10.0)
def test_remove_file_success(mock_get_duration, mock_getsize, mock_exists, merge_mgr: AudioMergeMgr, tmp_path):
    _, _, task_id = merge_mgr.create_task()
    file_path = str(tmp_path / "test.mp3")
    merge_mgr.add_file(task_id, file_path, "test.mp3")

    code, msg = merge_mgr.remove_file(task_id, 0)

    assert code == 0
    assert msg == "文件移除成功"
    task = merge_mgr.get_task(task_id)
    assert len(task['files']) == 0


def test_remove_file_failures(merge_mgr: AudioMergeMgr, tmp_path):
    _, _, task_id = merge_mgr.create_task()
    task = merge_mgr._get_task(task_id)
    task.status = TASK_STATUS_PROCESSING

    code, msg = merge_mgr.remove_file(task_id, 0)
    assert code == -1
    assert "任务正在处理中" in msg

    task.status = TASK_STATUS_PENDING
    code, msg = merge_mgr.remove_file(task_id, 0)
    assert code == -1
    assert "文件索引无效" in msg


@patch('os.path.exists', return_value=True)
@patch('os.path.getsize', return_value=1024)
@patch('core.services.audio_merge_mgr.get_media_duration', return_value=10.0)
def test_reorder_files_success(mock_get_duration, mock_getsize, mock_exists, merge_mgr: AudioMergeMgr, tmp_path):
    _, _, task_id = merge_mgr.create_task()
    merge_mgr.add_file(task_id, str(tmp_path / "a.mp3"), "a.mp3")
    merge_mgr.add_file(task_id, str(tmp_path / "b.mp3"), "b.mp3")

    code, msg = merge_mgr.reorder_files(task_id, [1, 0])

    assert code == 0
    assert msg == "文件顺序调整成功"
    task = merge_mgr.get_task(task_id)
    assert task['files'][0]['name'] == "b.mp3"
    assert task['files'][1]['name'] == "a.mp3"


def test_reorder_files_failures(merge_mgr: AudioMergeMgr, tmp_path):
    _, _, task_id = merge_mgr.create_task()
    task = merge_mgr._get_task(task_id)
    task.status = TASK_STATUS_PROCESSING

    code, msg = merge_mgr.reorder_files(task_id, [1, 0])
    assert code == -1
    assert "任务正在处理中" in msg

    task.status = TASK_STATUS_PENDING
    code, msg = merge_mgr.reorder_files(task_id, [0])
    assert code == -1
    assert "文件索引数量不匹配" in msg

    with patch('os.path.exists',
               return_value=True), patch('os.path.getsize',
                                         return_value=1024), patch('core.services.audio_merge_mgr.get_media_duration',
                                                                   return_value=10.0):
        merge_mgr.add_file(task_id, str(tmp_path / "a.mp3"), "a.mp3")

    code, msg = merge_mgr.reorder_files(task_id, [99])
    assert code == -1
    assert "文件索引无效" in msg


def test_reorder_files_exception_returns_error(monkeypatch, merge_mgr: AudioMergeMgr, tmp_path):
    _, _, task_id = merge_mgr.create_task()
    t = merge_mgr._get_task(task_id)
    t.files.append({'name': 'a.mp3', 'path': str(tmp_path / 'a.mp3'), 'size': 1, 'duration': 1.0, 'index': 0})

    monkeypatch.setattr(merge_mgr, '_save_task_and_update_time', lambda *_: (_ for _ in ()).throw(RuntimeError('boom')))

    code, msg = merge_mgr.reorder_files(task_id, [0])
    assert code == -1
    assert '调整文件顺序失败' in msg


@patch('os.path.exists', return_value=True)
@patch('os.path.getsize', return_value=1024)
@patch('core.services.audio_merge_mgr.get_media_duration', return_value=10.0)
@patch('core.services.audio_merge_mgr.AudioMergeMgr._run_task_async')
def test_start_task_success(mock_run_async, mock_get_duration, mock_getsize, mock_exists, merge_mgr: AudioMergeMgr,
                            tmp_path):
    _, _, task_id = merge_mgr.create_task()
    merge_mgr.add_file(task_id, str(tmp_path / "a.mp3"), "a.mp3")

    code, msg = merge_mgr.start_task(task_id)

    assert code == 0
    assert msg == "任务已开始处理"
    mock_run_async.assert_called_once()


def test_start_task_task_not_found(merge_mgr: AudioMergeMgr):
    code, msg = merge_mgr.start_task('nope')
    assert code == -1
    assert msg == '任务不存在'


def test_start_task_already_processing(merge_mgr: AudioMergeMgr):
    _, _, task_id = merge_mgr.create_task()
    task = merge_mgr._get_task(task_id)
    task.status = TASK_STATUS_PROCESSING

    code, msg = merge_mgr.start_task(task_id)

    assert code == -1
    assert "任务正在处理中" in msg


def test_start_task_no_files(merge_mgr: AudioMergeMgr):
    _, _, task_id = merge_mgr.create_task()

    code, msg = merge_mgr.start_task(task_id)

    assert code == -1
    assert "任务中没有文件" in msg


def test_parse_duration_from_ffmpeg_output(merge_mgr: AudioMergeMgr):
    out = "Duration: 00:01:02.03, start: 0.000000, bitrate: 128 kb/s"
    assert merge_mgr._parse_duration_from_ffmpeg_output(out) == 62.03
    assert merge_mgr._parse_duration_from_ffmpeg_output("no duration") is None


def test_get_result_duration_uses_fallback(merge_mgr: AudioMergeMgr):
    assert merge_mgr._get_result_duration('/tmp/x.mp3', fallback_duration=3.3) == 3.3


def test_get_file_duration_with_ffmpeg_success(merge_mgr: AudioMergeMgr):
    stderr = "Duration: 00:00:01.00"
    with patch('core.services.audio_merge_mgr.run_subprocess_safe', return_value=(0, '', stderr)):
        assert merge_mgr._get_file_duration_with_ffmpeg('/tmp/a.mp3') == 1.0


def test_get_file_duration_with_ffmpeg_handles_timeout(merge_mgr: AudioMergeMgr):
    with patch('core.services.audio_merge_mgr.run_subprocess_safe', side_effect=TimeoutError('t')):
        assert merge_mgr._get_file_duration_with_ffmpeg('/tmp/a.mp3') is None


def test_get_file_duration_with_ffmpeg_outer_exception(merge_mgr: AudioMergeMgr):
    with patch('core.services.audio_merge_mgr.run_subprocess_safe', side_effect=RuntimeError('boom')):
        assert merge_mgr._get_file_duration_with_ffmpeg('/tmp/a.mp3') is None


@patch('shutil.copy2')
@patch('core.services.audio_merge_mgr.get_media_task_result_dir')
def test_merge_audio_files_single_file(mock_get_result_dir, mock_copy, merge_mgr: AudioMergeMgr, tmp_path):
    mock_get_result_dir.return_value = str(tmp_path)
    files = [{'path': 'a.mp3', 'duration': 10.0}]
    result_file, _ = merge_mgr._merge_audio_files('task1', files)
    mock_copy.assert_called_once_with('a.mp3', str(tmp_path / 'merged.mp3'))
    assert result_file is not None


def test_merge_audio_files_no_files_returns_none(merge_mgr: AudioMergeMgr):
    rf, dur = merge_mgr._merge_audio_files('t1', [])
    assert rf is None
    assert dur is None


@patch('builtins.open', new_callable=mock_open)
@patch('core.services.audio_merge_mgr.run_subprocess_safe')
@patch('os.path.exists', return_value=True)
@patch('core.services.audio_merge_mgr.get_media_task_result_dir')
def test_merge_audio_files_multiple_files(mock_get_result_dir, mock_exists, mock_run_subprocess, mock_file_open,
                                          merge_mgr: AudioMergeMgr, tmp_path):
    mock_get_result_dir.return_value = str(tmp_path)
    mock_run_subprocess.return_value = (0, '', '')
    files = [{'path': 'a.mp3'}, {'path': 'b.mp3'}]

    result_file, _ = merge_mgr._merge_audio_files('task1', files)

    assert mock_run_subprocess.call_count == 2
    assert result_file is not None


@patch('builtins.open', new_callable=mock_open)
@patch('core.services.audio_merge_mgr.run_subprocess_safe')
@patch('os.path.exists', return_value=False)
@patch('core.services.audio_merge_mgr.get_media_task_result_dir')
def test_merge_audio_files_returncode_0_but_missing_result(mock_get_result_dir, mock_exists, mock_run_subprocess,
                                                           mock_file_open, merge_mgr: AudioMergeMgr, tmp_path):
    mock_get_result_dir.return_value = str(tmp_path)
    mock_run_subprocess.return_value = (0, '', '')
    files = [{'path': 'a.mp3'}, {'path': 'b.mp3'}]

    result_file, dur = merge_mgr._merge_audio_files('task1', files)

    assert result_file is None
    assert dur is None


@patch('builtins.open', new_callable=mock_open)
@patch('core.services.audio_merge_mgr.run_subprocess_safe', return_value=(1, '', 'ffmpeg error'))
@patch('os.path.exists', return_value=False)
@patch('core.services.audio_merge_mgr.get_media_task_result_dir')
def test_merge_audio_files_returncode_nonzero(mock_get_result_dir, mock_exists, mock_run_subprocess, mock_file_open,
                                              merge_mgr: AudioMergeMgr, tmp_path):
    mock_get_result_dir.return_value = str(tmp_path)
    files = [{'path': 'a.mp3'}, {'path': 'b.mp3'}]

    result_file, dur = merge_mgr._merge_audio_files('task1', files)

    assert result_file is None
    assert dur is None


@patch('builtins.open', new_callable=mock_open)
@patch('core.services.audio_merge_mgr.run_subprocess_safe', side_effect=TimeoutError('t'))
@patch('core.services.audio_merge_mgr.get_media_task_result_dir')
def test_merge_audio_files_timeout(mock_get_result_dir, mock_run_subprocess, mock_file_open, merge_mgr: AudioMergeMgr,
                                   tmp_path):
    mock_get_result_dir.return_value = str(tmp_path)
    files = [{'path': 'a.mp3'}, {'path': 'b.mp3'}]

    result_file, dur = merge_mgr._merge_audio_files('task1', files)

    assert result_file is None
    assert dur is None


@patch('builtins.open', new_callable=mock_open)
@patch('core.services.audio_merge_mgr.run_subprocess_safe', side_effect=RuntimeError('boom'))
@patch('core.services.audio_merge_mgr.get_media_task_result_dir')
def test_merge_audio_files_run_subprocess_exception(mock_get_result_dir, mock_run_subprocess, mock_file_open,
                                                    merge_mgr: AudioMergeMgr, tmp_path):
    mock_get_result_dir.return_value = str(tmp_path)
    files = [{'path': 'a.mp3'}, {'path': 'b.mp3'}]

    result_file, dur = merge_mgr._merge_audio_files('task1', files)

    assert result_file is None
    assert dur is None


def test_merge_audio_files_outer_exception_returns_none(monkeypatch, merge_mgr: AudioMergeMgr):
    monkeypatch.setattr('core.services.audio_merge_mgr.get_media_task_result_dir', lambda *_:
                        (_ for _ in ()).throw(RuntimeError('boom')))
    rf, dur = merge_mgr._merge_audio_files('t1', [{'path': 'a.mp3'}])
    assert rf is None
    assert dur is None


def test_load_history_tasks_removes_missing_task_dir(monkeypatch, tmp_path):
    monkeypatch.setattr('core.services.audio_merge_mgr.AUDIO_MERGE_BASE_DIR', str(tmp_path / 'merge'))

    monkeypatch.setattr('core.services.audio_merge_mgr.get_media_task_dir', lambda tid: str(tmp_path / 'missing' / tid))
    monkeypatch.setattr('core.services.audio_merge_mgr.get_media_task_result_dir',
                        lambda tid: str(tmp_path / 'missing' / tid / 'result'))

    monkeypatch.setattr('core.services.audio_merge_mgr.shutil.rmtree', lambda p: None)

    os.makedirs(tmp_path / 'merge', exist_ok=True)
    meta = {
        't1': {
            'task_id': 't1',
            'name': 'n1',
            'status': TASK_STATUS_PENDING,
            'files': [{
                'name': 'a.mp3',
                'path': str(tmp_path / 'no.mp3'),
                'size': 1,
                'duration': 1.0,
                'index': 0
            }],
            'result_file': str(tmp_path / 'no_result.mp3'),
            'result_duration': 1.0,
            'error_message': None,
            'create_time': 1,
            'update_time': 1,
        }
    }
    (tmp_path / 'merge' / 'tasks.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')

    mgr = AudioMergeMgr()
    assert mgr.get_task('t1') is None


def test_load_history_tasks_filters_files_and_clears_missing_result(monkeypatch, tmp_path):
    monkeypatch.setattr('core.services.audio_merge_mgr.AUDIO_MERGE_BASE_DIR', str(tmp_path / 'merge'))
    os.makedirs(tmp_path / 'merge', exist_ok=True)

    task_dir = tmp_path / 'taskdir'
    os.makedirs(task_dir, exist_ok=True)

    # make task dir exist
    monkeypatch.setattr('core.services.audio_merge_mgr.get_media_task_dir', lambda tid: str(task_dir))

    file_ok = tmp_path / 'ok.mp3'
    file_ok.write_bytes(b'x')

    # exists for task dir, file_ok and tasks.json (so BaseTaskMgr can load it)
    tasks_json = str(tmp_path / 'merge' / 'tasks.json')

    def fake_exists(p):
        return p in (str(task_dir), str(file_ok), tasks_json)

    monkeypatch.setattr('core.services.audio_merge_mgr.os.path.exists', fake_exists)

    meta = {
        't1': {
            'task_id':
            't1',
            'name':
            'n1',
            'status':
            TASK_STATUS_PENDING,
            'files': [
                {
                    'name': 'ok.mp3',
                    'path': str(file_ok),
                    'size': 1,
                    'duration': 1.0,
                    'index': 0
                },
                {
                    'name': 'missing.mp3',
                    'path': str(tmp_path / 'missing.mp3'),
                    'size': 1,
                    'duration': 1.0,
                    'index': 1
                },
                {
                    'name': 'nop.mp3',
                    'path': '',
                    'size': 1,
                    'duration': 1.0,
                    'index': 2
                },
            ],
            'result_file':
            str(tmp_path / 'no_result.mp3'),
            'result_duration':
            1.0,
            'error_message':
            None,
            'create_time':
            1,
            'update_time':
            1,
        }
    }

    (tmp_path / 'merge' / 'tasks.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')

    mgr = AudioMergeMgr()
    t = mgr.get_task('t1')
    assert t is not None
    assert len(t['files']) == 1
    assert t['files'][0]['path'] == str(file_ok)
    assert t['files'][0]['index'] == 0
    assert t['result_file'] is None
    assert t['result_duration'] is None


def test_load_history_tasks_exception_removes_task(monkeypatch, tmp_path):
    monkeypatch.setattr('core.services.audio_merge_mgr.AUDIO_MERGE_BASE_DIR', str(tmp_path / 'merge'))
    os.makedirs(tmp_path / 'merge', exist_ok=True)

    meta = {
        't1': {
            'task_id': 't1',
            'name': 'n1',
            'status': TASK_STATUS_PENDING,
            'files': [],
            'result_file': None,
            'result_duration': None,
            'error_message': None,
            'create_time': 1,
            'update_time': 1,
        }
    }
    (tmp_path / 'merge' / 'tasks.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')

    monkeypatch.setattr('core.services.audio_merge_mgr.get_media_task_dir', lambda tid:
                        (_ for _ in ()).throw(RuntimeError('boom')))

    mgr = AudioMergeMgr()
    assert mgr.get_task('t1') is None


def test_validate_file_wrong_ext_and_missing(tmp_path):
    mgr = AudioMergeMgr()

    msg = mgr._validate_file('/nope.mp3', 'nope.mp3')
    assert msg is not None
    assert '文件不存在' in msg

    f = tmp_path / 'a.txt'
    f.write_text('x', encoding='utf-8')
    msg2 = mgr._validate_file(str(f), 'a.txt')
    assert msg2 is not None
    assert '不支持的文件类型' in msg2


def test_update_file_indices_sets_index():
    mgr = AudioMergeMgr()
    files = [{'name': 'a'}, {'name': 'b'}]
    mgr._update_file_indices(files)
    assert files[0]['index'] == 0
    assert files[1]['index'] == 1


def test_before_delete_task_rmtree_called(monkeypatch, tmp_path):
    monkeypatch.setattr('core.services.audio_merge_mgr.get_media_task_dir', lambda tid: str(tmp_path / tid))
    os.makedirs(tmp_path / 't1', exist_ok=True)

    called = {'p': None}

    def fake_rmtree(p):
        called['p'] = p

    monkeypatch.setattr('core.services.audio_merge_mgr.shutil.rmtree', fake_rmtree)

    mgr = AudioMergeMgr()
    t = mgr._task_from_dict({
        'task_id': 't1',
        'name': 'n1',
        'status': TASK_STATUS_PENDING,
        'files': [],
        'result_file': None,
        'result_duration': None,
        'error_message': None,
        'create_time': 1,
        'update_time': 1,
    })

    mgr._before_delete_task(t)
    assert called['p'] == str(tmp_path / 't1')


def test_start_task_runner_result_duration_fallback(monkeypatch, merge_mgr: AudioMergeMgr):
    monkeypatch.setattr(merge_mgr, '_merge_audio_files', lambda task_id, files: ('/tmp/r.mp3', None))
    monkeypatch.setattr('core.services.audio_merge_mgr.get_media_duration', lambda p: 9.9)

    def fake_run_task_async(task_id, runner):
        t = merge_mgr._get_task(task_id)
        t.status = TASK_STATUS_PROCESSING
        runner(t)
        if t.status == TASK_STATUS_PROCESSING:
            t.status = TASK_STATUS_SUCCESS

    monkeypatch.setattr(merge_mgr, '_run_task_async', fake_run_task_async)

    _, _, tid = merge_mgr.create_task('n')
    t = merge_mgr._get_task(tid)
    t.files.append({'name': 'a.mp3', 'path': '/tmp/a.mp3', 'size': 1, 'duration': 1.0, 'index': 0})

    code, msg = merge_mgr.start_task(tid)
    assert code == 0

    task = merge_mgr.get_task(tid)
    assert task['result_duration'] == 9.9


def test_start_task_runner_merge_failed(monkeypatch, merge_mgr: AudioMergeMgr):
    monkeypatch.setattr(merge_mgr, '_merge_audio_files', lambda task_id, files: (None, None))

    def fake_run_task_async(task_id, runner):
        t = merge_mgr._get_task(task_id)
        t.status = TASK_STATUS_PROCESSING
        runner(t)

    monkeypatch.setattr(merge_mgr, '_run_task_async', fake_run_task_async)

    _, _, tid = merge_mgr.create_task('n')
    t = merge_mgr._get_task(tid)
    t.files.append({'name': 'a.mp3', 'path': '/tmp/a.mp3', 'size': 1, 'duration': 1.0, 'index': 0})

    code, msg = merge_mgr.start_task(tid)
    assert code == 0

    task = merge_mgr.get_task(tid)
    assert task['status'] == TASK_STATUS_FAILED
    assert task['error_message'] == '合成失败'
