import json
import os
import random
import string
import threading
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar, TypedDict

from core.config import (TASK_STATUS_FAILED, TASK_STATUS_PENDING, TASK_STATUS_PROCESSING, TASK_STATUS_SUCCESS,
                         app_logger)
from core.utils import ensure_directory

log = app_logger


class TaskProgress(TypedDict):
    total: int
    processed: int
    current_file: str


class FileInfo(TypedDict, total=False):
    name: str
    path: str
    size: int
    duration: float
    modified: float
    index: int
    status: str
    error: str


@dataclass(kw_only=True)
class TaskBase:
    task_id: str
    name: str = ''
    status: str = TASK_STATUS_PENDING
    error_message: Optional[str] = None
    create_time: float = 0
    update_time: float = 0


TTask = TypeVar('TTask', bound=TaskBase)


class BaseTaskMgr(ABC, Generic[TTask]):

    TASK_META_FILE = 'tasks.json'

    def __init__(self, base_dir: str) -> None:
        self._tasks: Dict[str, TTask] = {}
        self._task_lock = threading.Lock()
        self._stop_flags: Dict[str, bool] = {}
        self._base_dir = base_dir
        ensure_directory(self._base_dir)
        self._load_history_tasks()

    def _now_ts(self) -> float:
        return datetime.now().timestamp()

    def _generate_task_id(self) -> str:
        timestamp = int(self._now_ts())
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"{timestamp}{random_str}"

    def _get_task(self, task_id: str) -> Optional[TTask]:
        return self._tasks.get(task_id)

    def _get_task_or_err(self, task_id: str) -> Tuple[Optional[TTask], Optional[str]]:
        task = self._get_task(task_id)
        if not task:
            return None, '任务不存在'
        return task, None

    def _get_task_meta_file(self) -> str:
        return os.path.join(self._base_dir, self.TASK_META_FILE)

    def _load_history_tasks(self) -> None:
        meta_file = self._get_task_meta_file()
        if not os.path.exists(meta_file):
            return
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return
            for task_id, task_data in data.items():
                try:
                    self._tasks[task_id] = self._task_from_dict(task_data)
                except Exception as e:
                    log.error(f"[BaseTaskMgr] 加载任务失败 {task_id}: {e}")
            log.info(f"[BaseTaskMgr] 加载了 {len(self._tasks)} 个历史任务: {self.__class__.__name__}")
        except Exception as e:
            log.error(f"[BaseTaskMgr] 加载历史任务失败: {e}")

    @abstractmethod
    def _task_from_dict(self, task_data: Dict[str, Any]) -> TTask:
        raise NotImplementedError

    def _task_to_dict(self, task: TTask) -> Dict[str, Any]:
        return asdict(task)

    def _save_all_tasks(self) -> None:
        try:
            ensure_directory(self._base_dir)
            all_tasks_data = {task_id: self._task_to_dict(task) for task_id, task in self._tasks.items()}
            meta_file = self._get_task_meta_file()
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(all_tasks_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"[BaseTaskMgr] 保存所有任务失败: {e}", exc_info=True)

    def _update_task_time(self, task: TTask) -> None:
        task.update_time = self._now_ts()

    def _save_task_and_update_time(self, task: TTask) -> None:
        self._update_task_time(task)
        self._save_all_tasks()

    def _ensure_not_processing(self, task: TTask, operation: str) -> Optional[str]:
        if task.status == TASK_STATUS_PROCESSING:
            return f"任务正在处理中，无法{operation}"
        return None

    def stop_task(self, task_id: str) -> Tuple[int, str]:
        with self._task_lock:
            task, err = self._get_task_or_err(task_id)
            if err:
                return -1, err
            if task.status != TASK_STATUS_PROCESSING:
                return -1, '任务未在处理中'
            self._stop_flags[task_id] = True
            return 0, '已请求停止任务'

    def _should_stop(self, task_id: str) -> bool:
        return self._stop_flags.get(task_id, False)

    def _clear_stop_flag(self, task_id: str) -> None:
        self._stop_flags.pop(task_id, None)

    @abstractmethod
    def create_task(self, *args: Any, **kwargs: Any) -> Tuple[int, str, Optional[str]]:
        raise NotImplementedError

    @abstractmethod
    def start_task(self, task_id: str, *args: Any, **kwargs: Any) -> Tuple[int, str]:
        raise NotImplementedError

    def _run_task_async(self, task_id: str, runner: Callable[[TTask], None]) -> None:

        def wrapped() -> None:
            try:
                with self._task_lock:
                    task = self._get_task(task_id)
                    if not task:
                        return
                    task.status = TASK_STATUS_PROCESSING
                    task.error_message = None
                    self._save_task_and_update_time(task)

                runner(task)

                with self._task_lock:
                    task2 = self._get_task(task_id)
                    if task2 and task2.status == TASK_STATUS_PROCESSING:
                        task2.status = TASK_STATUS_SUCCESS
                        task2.error_message = None
                        self._save_task_and_update_time(task2)
            except Exception as e:
                log.error(f"[{self.__class__.__name__}] 任务 {task_id} 执行异常: {e}")
                with self._task_lock:
                    task3 = self._get_task(task_id)
                    if task3:
                        task3.status = TASK_STATUS_FAILED
                        task3.error_message = str(e)
                        self._save_task_and_update_time(task3)
            finally:
                self._clear_stop_flag(task_id)

        threading.Thread(target=wrapped, daemon=True).start()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._task_lock:
            task = self._get_task(task_id)
            return self._task_to_dict(task) if task else None

    def list_tasks(self) -> List[Dict[str, Any]]:
        with self._task_lock:
            tasks = [self._task_to_dict(t) for t in self._tasks.values()]
        tasks.sort(key=lambda x: x.get('create_time', 0), reverse=True)
        return tasks

    def _before_delete_task(self, _task: TTask) -> None:
        """在任务从内存和 tasks.json 移除前执行的清理钩子。"""
        return

    def _after_delete_task(self, _task_id: str) -> None:
        """在任务从内存和 tasks.json 移除后执行的清理钩子。"""
        return

    def _should_request_stop_before_delete(self, _task: TTask) -> bool:
        """是否在删除 processing 任务时先发出停止请求（stop-then-retry 语义）。"""
        return False

    def delete_task(self, task_id: str) -> Tuple[int, str]:
        with self._task_lock:
            task, err = self._get_task_or_err(task_id)
            if err:
                return -1, err

            if task.status == TASK_STATUS_PROCESSING:
                if self._should_request_stop_before_delete(task):
                    self._stop_flags[task_id] = True
                    return -1, '任务正在处理中，已请求停止，请稍后再删除'
                return -1, '任务正在处理中，无法删除'

            try:
                self._before_delete_task(task)
            except Exception as e:
                log.error(f"[BaseTaskMgr] 删除前清理失败 {task_id}: {e}")
                return -1, f"删除失败: {str(e)}"

            del self._tasks[task_id]
            self._save_all_tasks()

        try:
            self._after_delete_task(task_id)
        except Exception as e:
            log.error(f"[BaseTaskMgr] 删除后清理失败 {task_id}: {e}")

        return 0, '任务删除成功'

    def _before_create_task(self, task: TTask) -> None:
        """Hook for subclasses to perform actions before task creation."""
        pass

    def _create_task_and_save(self, task: TTask, task_id: Optional[str] = None) -> Tuple[int, str, Optional[str]]:
        with self._task_lock:
            tid = task_id or task.task_id or self._generate_task_id()
            while tid in self._tasks:
                tid = self._generate_task_id()

            task.task_id = tid
            now = self._now_ts()
            task.create_time = now
            task.update_time = now
            task.status = TASK_STATUS_PENDING

            try:
                self._before_create_task(task)
            except Exception as e:
                log.error(f"[{self.__class__.__name__}] 任务创建前操作失败 {tid}: {e}")
                return -1, f"任务创建前操作失败: {str(e)}", None

            self._tasks[tid] = task
            self._save_all_tasks()
            log.info(f"[{self.__class__.__name__}] 创建任务: {tid}, 名称: {task.name}")
            return 0, '任务创建成功', tid
