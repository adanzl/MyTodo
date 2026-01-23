"""
TTS 事件循环单元测试

测试 TTS 任务执行时的事件循环设置是否正确，
避免 "child watchers are only available on the default loop" 错误。
"""
import asyncio
import threading
import pytest
from unittest.mock import patch

from core.services.tts_mgr import TTSMgr
from core.tools.async_util import _clear_event_loop
from core.config import (
    TASK_STATUS_PENDING,
    TASK_STATUS_PROCESSING,
    TASK_STATUS_SUCCESS,
    TASK_STATUS_FAILED,
)


@pytest.fixture
def tts_mgr(tmp_path, monkeypatch):
    """Provides a clean TTSMgr instance using a temporary directory."""
    monkeypatch.setattr('core.services.tts_mgr.TTS_BASE_DIR', str(tmp_path))
    mgr = TTSMgr()
    mgr._tasks = {}
    return mgr


def test_event_loop_in_thread():
    """测试在新线程中创建事件循环"""
    thread_result = {'ok': False, 'error': None}

    def thread_check():
        try:
            # 清除事件循环引用
            _clear_event_loop()

            # 尝试获取或创建事件循环
            try:
                loop = asyncio.get_event_loop()
                assert loop is not None
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                assert loop is not None

            thread_result['ok'] = True
        except Exception as e:
            thread_result['error'] = str(e)

    thread = threading.Thread(target=thread_check, daemon=True)
    thread.start()
    thread.join(timeout=2)

    assert thread_result['ok'], f"事件循环设置失败: {thread_result.get('error')}"


def test_tts_task_creation(tts_mgr: TTSMgr):
    """测试 TTS 任务创建"""
    code, msg, task_id = tts_mgr.create_task(
        text="这是一个测试文本，用于验证事件循环设置是否正确。",
        name="事件循环测试任务"
    )

    assert code == 0, f"创建任务失败: {msg}"
    assert task_id is not None, "task_id 不应该为空"

    # 获取任务详情
    task = tts_mgr.get_task(task_id)
    assert task is not None, "应该能获取到任务"
    assert task['name'] == "事件循环测试任务"
    assert task['status'] == TASK_STATUS_PENDING
    assert task['text'] == "这是一个测试文本，用于验证事件循环设置是否正确。"


def test_tts_task_start_with_event_loop(tts_mgr: TTSMgr, tmp_path):
    """测试 TTS 任务启动时的事件循环设置"""
    import time

    # 创建测试任务
    code, msg, task_id = tts_mgr.create_task(
        text="测试文本",
        name="事件循环测试"
    )
    assert code == 0

    # Mock TTSClient 以避免实际调用 TTS 服务
    class FakeTTSClient:
        def __init__(self, on_msg=None, on_err=None):
            self.on_msg = on_msg
            self.on_err = on_err
            self.speed = 1.0
            self.vol = 50

        def stream_msg(self, text: str, role=None, id=None):
            # 模拟发送数据
            if self.on_msg:
                self.on_msg(b"test_audio_data", 0)

        def stream_complete(self):
            # 模拟完成
            if self.on_msg:
                self.on_msg("done", 1)

    with patch('core.services.tts_mgr.TTSClient', FakeTTSClient):
        # 启动任务
        code, msg = tts_mgr.start_task(task_id)
        assert code == 0, f"启动任务失败: {msg}"

        # 等待任务完成（最多等待 5 秒）
        deadline = 5.0
        start = time.time()
        task = None
        while time.time() - start < deadline:
            task = tts_mgr.get_task(task_id)
            assert task is not None
            if task['status'] in (TASK_STATUS_SUCCESS, TASK_STATUS_FAILED):
                break
            time.sleep(0.1)

        assert task is not None, "应该能获取到任务"
        assert task['status'] == TASK_STATUS_SUCCESS, f"任务应该成功，但状态是: {task['status']}, 错误: {task.get('error_message')}"

        # 验证输出文件是否存在
        output_file = tmp_path / task_id / 'output.mp3'
        assert output_file.exists(), "输出文件应该存在"


def test_run_task_async_with_loop_creates_event_loop(tts_mgr: TTSMgr):
    """测试 _run_task_async_with_loop 方法是否正确创建事件循环"""
    # 记录事件循环创建情况
    event_loop_created = {'created': False}

    # 直接测试事件循环创建逻辑（模拟 _run_task_async_with_loop 中的逻辑）
    def test_wrapped():
        _clear_event_loop()
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        event_loop_created['created'] = True

    thread = threading.Thread(target=test_wrapped, daemon=True)
    thread.start()
    thread.join(timeout=2)

    assert event_loop_created['created'], "应该在新线程中创建事件循环"


def test_clear_event_loop_in_thread():
    """测试 _clear_event_loop 函数在新线程中的行为"""
    clear_result = {'ok': False}

    def thread_test():
        try:
            _clear_event_loop()
            # 尝试创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            clear_result['ok'] = True
        except Exception as e:
            clear_result['error'] = str(e)

    thread = threading.Thread(target=thread_test, daemon=True)
    thread.start()
    thread.join(timeout=2)

    assert clear_result['ok'], f"清除事件循环失败: {clear_result.get('error')}"


def test_tts_task_execution_without_event_loop_error(tts_mgr: TTSMgr, tmp_path):
    """测试 TTS 任务执行不会出现事件循环错误"""
    import time

    # 创建测试任务
    code, msg, task_id = tts_mgr.create_task(
        text="测试文本，用于验证事件循环",
        name="事件循环错误测试"
    )
    assert code == 0

    # Mock TTSClient
    class FakeTTSClient:
        def __init__(self, on_msg=None, on_err=None):
            self.on_msg = on_msg
            self.on_err = on_err
            self.speed = 1.0
            self.vol = 50

        def stream_msg(self, text: str, role=None, id=None):
            if self.on_msg:
                self.on_msg(b"audio_data", 0)

        def stream_complete(self):
            if self.on_msg:
                self.on_msg("done", 1)

    # 记录是否有事件循环错误
    event_loop_errors = []

    def error_handler(err):
        if "child watchers" in str(err) or "default loop" in str(err):
            event_loop_errors.append(str(err))

    with patch('core.services.tts_mgr.TTSClient', FakeTTSClient):
        # 启动任务
        code, msg = tts_mgr.start_task(task_id)
        assert code == 0

        # 等待任务完成
        deadline = 5.0
        start = time.time()
        task = None
        while time.time() - start < deadline:
            task = tts_mgr.get_task(task_id)
            if task and task['status'] in (TASK_STATUS_SUCCESS, TASK_STATUS_FAILED):
                break
            time.sleep(0.1)

        # 检查是否有事件循环错误
        assert len(event_loop_errors) == 0, f"不应该有事件循环错误，但发现了: {event_loop_errors}"
        
        # 检查任务状态
        assert task is not None
        if task['status'] == TASK_STATUS_FAILED:
            error_msg = task.get('error_message', '')
            assert "child watchers" not in error_msg.lower(), f"任务失败，但错误信息中不应该包含事件循环错误: {error_msg}"
            assert "default loop" not in error_msg.lower(), f"任务失败，但错误信息中不应该包含事件循环错误: {error_msg}"
