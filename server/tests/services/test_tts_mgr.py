import os
import pytest
from unittest.mock import patch

from core.services.tts_mgr import TTSMgr
from core.config import TASK_STATUS_PENDING, TASK_STATUS_PROCESSING, TASK_STATUS_SUCCESS, TASK_STATUS_FAILED


@pytest.fixture
def tts_mgr(tmp_path, monkeypatch):
    """Provides a clean TTSMgr instance using a temporary directory."""
    monkeypatch.setattr('core.services.tts_mgr.TTS_BASE_DIR', str(tmp_path))
    mgr = TTSMgr()
    mgr._tasks = {}
    return mgr


def test_create_task_success(tts_mgr: TTSMgr):
    code, msg, task_id = tts_mgr.create_task(text="Hello world", name="Test Task")

    assert code == 0
    assert msg == "任务创建成功"
    assert task_id is not None

    task = tts_mgr.get_task(task_id)
    assert task is not None
    assert task['name'] == "Test Task"
    assert task['text'] == "Hello world"
    assert task['status'] == TASK_STATUS_PENDING


def test_create_task_empty_text_fails(tts_mgr: TTSMgr):
    code, msg, task_id = tts_mgr.create_task(text="  ")
    assert code == -1
    assert "文本不能为空" in msg


def test_update_task_success(tts_mgr: TTSMgr):
    _, _, task_id = tts_mgr.create_task(text="Initial text")
    code, msg = tts_mgr.update_task(task_id, name="New Name", text="Updated text", speed=1.5, vol=75)

    assert code == 0
    assert msg == "任务更新成功"

    task = tts_mgr.get_task(task_id)
    assert task['name'] == "New Name"
    assert task['text'] == "Updated text"
    assert task['speed'] == 1.5
    assert task['vol'] == 75


def test_update_task_processing_fails(tts_mgr: TTSMgr):
    _, _, task_id = tts_mgr.create_task(text="test")
    task = tts_mgr._get_task(task_id)
    task.status = TASK_STATUS_PROCESSING

    code, msg = tts_mgr.update_task(task_id, name="New Name")

    assert code == -1
    assert "任务正在处理中" in msg


def test_delete_task_success(tts_mgr: TTSMgr, tmp_path):
    _, _, task_id = tts_mgr.create_task(text="test")
    task_dir = tmp_path / task_id
    assert os.path.exists(task_dir)

    code, msg = tts_mgr.delete_task(task_id)

    assert code == 0
    assert msg == "任务删除成功"
    assert not os.path.exists(task_dir)


@patch('core.services.tts_mgr.TTSMgr._run_task_async')
def test_start_task_success(mock_run_async, tts_mgr: TTSMgr):
    _, _, task_id = tts_mgr.create_task(text="Hello")

    code, msg = tts_mgr.start_task(task_id)

    assert code == 0
    assert msg == "TTS 任务已启动"
    mock_run_async.assert_called_once()


def test_start_task_task_not_found(tts_mgr: TTSMgr):
    code, msg = tts_mgr.start_task('nope')
    assert code == -1
    assert msg == '任务不存在'


def test_start_task_already_processing(tts_mgr: TTSMgr):
    _, _, task_id = tts_mgr.create_task(text="hello")
    task = tts_mgr._get_task(task_id)
    task.status = TASK_STATUS_PROCESSING

    code, msg = tts_mgr.start_task(task_id)
    assert code == -1
    assert '任务正在处理中' in msg


def test_start_task_async_runs_and_writes_file(tts_mgr: TTSMgr, tmp_path):

    class FakeTTSClient:

        def __init__(self, on_msg=None, on_err=None):
            self.on_msg = on_msg
            self.on_err = on_err
            self.speed = 1.0
            self.vol = 50

        def stream_msg(self, text: str, role=None, id=None):
            self.on_msg(b"abc", 0)
            self.on_msg(b"def", 0)

        def stream_complete(self):
            self.on_msg("done", 1)

    with patch('core.services.tts_mgr.TTSClient', FakeTTSClient):
        code, msg, task_id = tts_mgr.create_task(text="这是测试文本", name="async")
        assert code == 0
        assert task_id is not None

        code2, _ = tts_mgr.start_task(task_id)
        assert code2 == 0

        deadline = 5.0
        import time
        start = time.time()
        last = None
        while time.time() - start < deadline:
            task = tts_mgr.get_task(task_id)
            assert task is not None
            last = task
            if task['status'] in (TASK_STATUS_SUCCESS, TASK_STATUS_FAILED):
                break
            time.sleep(0.05)

        assert last is not None
        assert last['status'] == TASK_STATUS_SUCCESS

        output_file = os.path.join(str(tmp_path), task_id, 'output.mp3')
        assert os.path.exists(output_file)
        with open(output_file, 'rb') as f:
            data = f.read()
        assert data == b"abcdef"


def test_start_task_no_text_fails(tts_mgr: TTSMgr):
    _, _, task_id = tts_mgr.create_task(text="not empty")
    task = tts_mgr._get_task(task_id)
    if task:
        task.text = ""
        tts_mgr._save_all_tasks()

    code, msg = tts_mgr.start_task(task_id)

    assert code == -1
    assert "文本为空" in msg


def test_run_tts_task_stop_midway_sets_failed(tts_mgr: TTSMgr, monkeypatch):

    class FakeTTSClient:

        def __init__(self, on_msg=None, on_err=None):
            self.on_msg = on_msg
            self.on_err = on_err
            self.speed = 1.0
            self.vol = 50

        def stream_msg(self, text: str, role=None, id=None):
            self.on_msg(b"abc", 0)

        def stream_complete(self):
            self.on_msg("done", 1)

    with patch('core.services.tts_mgr.TTSClient', FakeTTSClient):
        _, _, task_id = tts_mgr.create_task(text="x", name="stop")

        # request stop before running
        tts_mgr._stop_flags[task_id] = True

        with pytest.raises(RuntimeError):
            task = tts_mgr._get_task(task_id)
            tts_mgr._run_tts_task(task)

        t = tts_mgr.get_task(task_id)
        assert t['status'] == TASK_STATUS_FAILED
        assert '任务已被停止' in t['error_message']


def test_after_delete_task_handles_nested_dirs(tts_mgr: TTSMgr, tmp_path):
    _, _, task_id = tts_mgr.create_task(text="x")

    # create nested dirs/files
    base = tmp_path / task_id
    d1 = base / 'a' / 'b'
    os.makedirs(d1, exist_ok=True)
    (d1 / 'x.txt').write_text('x', encoding='utf-8')

    # call hook directly
    tts_mgr._after_delete_task(task_id)

    assert not os.path.exists(base)
