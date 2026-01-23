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
