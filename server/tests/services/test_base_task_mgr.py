import os
import json
import time
import pytest
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple

from core.services.base_task_mgr import BaseTaskMgr, TaskBase
from core.config import TASK_STATUS_PENDING, TASK_STATUS_PROCESSING, TASK_STATUS_SUCCESS, TASK_STATUS_FAILED


@dataclass
class SimpleTask(TaskBase):
    some_data: str = ""


class SimpleTaskMgr(BaseTaskMgr[SimpleTask]):

    def _task_from_dict(self, task_data: Dict[str, Any]) -> SimpleTask:
        return SimpleTask(**task_data)

    def create_task(self, some_data: str) -> Tuple[int, str, Optional[str]]:
        task = SimpleTask(task_id="", some_data=some_data)
        return self._create_task_and_save(task)

    def start_task(self, task_id: str, runner=None) -> Tuple[int, str]:
        self._run_task_async(task_id, runner)
        return 0, "Task started"


@pytest.fixture
def task_mgr(tmp_path):
    """Provides a clean SimpleTaskMgr instance for each test."""
    mgr = SimpleTaskMgr(base_dir=str(tmp_path))
    mgr._tasks = {}  # Ensure a clean state
    return mgr


def test_create_task_base(task_mgr: SimpleTaskMgr):
    """Test that a task is created, saved, and can be retrieved."""
    code, msg, task_id = task_mgr.create_task(some_data="test_data")

    assert code == 0
    assert msg == "任务创建成功"
    assert task_id is not None

    retrieved_task = task_mgr.get_task(task_id)
    assert retrieved_task is not None
    assert retrieved_task['some_data'] == "test_data"
    assert retrieved_task['status'] == TASK_STATUS_PENDING


def test_list_tasks(task_mgr: SimpleTaskMgr):
    """Test that list_tasks returns all created tasks."""
    _, _, id1 = task_mgr.create_task(some_data="task1")
    _, _, id2 = task_mgr.create_task(some_data="task2")

    tasks = task_mgr.list_tasks()
    assert len(tasks) == 2
    task_ids = {t['task_id'] for t in tasks}
    assert {id1, id2} == task_ids


def test_delete_task_success(task_mgr: SimpleTaskMgr):
    """Test that a task can be successfully deleted."""
    _, _, task_id = task_mgr.create_task(some_data="to_delete")
    assert task_mgr.get_task(task_id) is not None

    code, msg = task_mgr.delete_task(task_id)

    assert code == 0
    assert msg == "任务删除成功"
    assert task_mgr.get_task(task_id) is None


def test_delete_task_processing_fails(task_mgr: SimpleTaskMgr):
    """Test that a task cannot be deleted while it is processing."""
    _, _, task_id = task_mgr.create_task(some_data="processing_task")
    task = task_mgr._get_task(task_id)
    task.status = TASK_STATUS_PROCESSING

    code, msg = task_mgr.delete_task(task_id)

    assert code == -1
    assert "任务正在处理中" in msg
    assert task_mgr.get_task(task_id) is not None


def test_run_task_async_failure(task_mgr: SimpleTaskMgr):
    """Test that _run_task_async correctly handles exceptions in the runner."""
    _, _, task_id = task_mgr.create_task(some_data="failing_task")

    def failing_runner(task):
        raise ValueError("Something went wrong")

    task_mgr.start_task(task_id, runner=failing_runner)

    # Allow the thread to execute
    time.sleep(0.1)

    task = task_mgr.get_task(task_id)
    assert task['status'] == TASK_STATUS_FAILED
    assert "Something went wrong" in task['error_message']


def test_stop_task_not_processing(task_mgr: SimpleTaskMgr):
    """stop_task 在任务未处于 processing 时返回 -1"""
    _, _, task_id = task_mgr.create_task(some_data="ok")
    code, msg = task_mgr.stop_task(task_id)
    assert code == -1
    assert "未在处理中" in msg


def test_ensure_not_processing(task_mgr: SimpleTaskMgr):
    """_ensure_not_processing 在 status 为 PROCESSING 时返回错误信息"""
    _, _, task_id = task_mgr.create_task(some_data="x")
    task = task_mgr._get_task(task_id)
    task.status = TASK_STATUS_PROCESSING
    err = task_mgr._ensure_not_processing(task, "更新任务")
    assert err is not None
    assert "任务正在处理中" in err
    assert "更新任务" in err


def test_load_tasks_invalid_json_not_dict(task_mgr: SimpleTaskMgr):
    """加载 meta 文件内容非 dict 时静默跳过（不抛错）"""
    meta_file = task_mgr._get_task_meta_file()
    os.makedirs(os.path.dirname(meta_file), exist_ok=True)
    with open(meta_file, 'w', encoding='utf-8') as f:
        f.write('[]')
    task_mgr._load_history_tasks()
    assert len(task_mgr._tasks) == 0


def test_save_all_tasks_exception(task_mgr: SimpleTaskMgr, monkeypatch):
    """_save_all_tasks 在写文件异常时记录日志不抛错"""
    _, _, task_id = task_mgr.create_task(some_data="x")

    def broken_dump(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(json, "dump", broken_dump)
    task_mgr._save_all_tasks()
    # 不应抛错；任务仍在内存
    assert task_mgr.get_task(task_id) is not None


def test_run_task_async_task_gone_after_runner(task_mgr: SimpleTaskMgr):
    """runner 执行完后任务已被删除时，不更新状态（命中 task2 为 None 分支）"""
    _, _, task_id = task_mgr.create_task(some_data="gone")

    def runner_that_clears_status_and_deletes(task):
        # 先改为 PENDING 才能通过 delete_task 的状态检查，再删除；使 wrapped 内 task2=None
        task.status = TASK_STATUS_PENDING
        task_mgr.delete_task(task.task_id)

    task_mgr.start_task(task_id, runner=runner_that_clears_status_and_deletes)
    for _ in range(50):
        if task_mgr.get_task(task_id) is None:
            break
        time.sleep(0.1)
    assert task_mgr.get_task(task_id) is None
