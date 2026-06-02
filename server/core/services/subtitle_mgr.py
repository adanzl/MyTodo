"""字幕服务：sidecar 发现、ASSRT 搜索下载、Whisper 识别任务队列。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Tuple

from core.config import (
    MEDIA_BASE_DIR,
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_PROCESSING,
    TASK_STATUS_SUCCESS,
    app_logger,
    config,
)
from core.services.base_task_mgr import BaseTaskMgr, TaskBase
from core.subtitles import AssrtError, WhisperError, assrt_client, transcribe_to_sidecar
from core.tools.async_util import run_in_background
from core.utils import (
    _err,
    _ok,
    subtitle_label_from_path,
    subtitle_lang_from_path,
    validate_and_normalize_path,
)

log = app_logger

_SUBTITLE_SUFFIXES = ("", ".zh", ".chs", ".cht", ".en", ".eng")
_SUBTITLE_EXTS = (".vtt", ".srt")
_RECOGNIZE_TASK_DIR = os.path.join(MEDIA_BASE_DIR, "subtitle_recognize")
_RECOGNIZE_TASK_RETENTION_SEC = 24 * 3600  # 终态任务记录保留 1 天


def _normalize_video_path(path: str, base_dir: str) -> tuple[str | None, str]:
    path = (path or "").strip()
    if not path:
        return None, "video_path 不能为空"
    normalized, err = validate_and_normalize_path(path, base_dir, must_be_file=True)
    return normalized, err or "Invalid video_path"


@dataclass
class SubtitleRecognizeTask(TaskBase):
    video_path: str = ""
    language: str = "en"
    output_path: str = ""


class SubtitleRecognizeMgr(BaseTaskMgr[SubtitleRecognizeTask]):
    """Whisper 识别串行队列（tasks.json 持久化，终态记录保留 1 天）。"""

    def __init__(self) -> None:
        super().__init__(base_dir=_RECOGNIZE_TASK_DIR)
        self._media_base_dir = config.DEFAULT_BASE_DIR
        self._drain_queue()

    def _task_from_dict(self, data: dict) -> SubtitleRecognizeTask:
        return SubtitleRecognizeTask(**data)

    def _load_history_tasks(self) -> None:
        super()._load_history_tasks()
        changed = False
        for task in self._tasks.values():
            if task.status == TASK_STATUS_PROCESSING:
                task.status = TASK_STATUS_PENDING
                task.error_message = None
                changed = True
        if self._purge_expired_tasks():
            changed = True
        elif changed:
            self._save_all_tasks()
        if self._tasks:
            log.info("[SUBTITLE] 恢复 %d 个识别任务", len(self._tasks))

    def _purge_expired_tasks(self) -> bool:
        """删除超过保留期的 success/failed 记录。"""
        cutoff = self._now_ts() - _RECOGNIZE_TASK_RETENTION_SEC
        terminal = {TASK_STATUS_SUCCESS, TASK_STATUS_FAILED}
        expired = [
            tid for tid, t in self._tasks.items()
            if t.status in terminal and t.update_time < cutoff
        ]
        if not expired:
            return False
        for tid in expired:
            del self._tasks[tid]
        self._save_all_tasks()
        log.info("[SUBTITLE] 清理 %d 条过期识别记录", len(expired))
        return True

    def _finish_task(
        self,
        task_id: str,
        *,
        success: bool,
        error_message: str | None = None,
        output_path: str = "",
        from_status: str | None = None,
    ) -> None:
        allowed = {TASK_STATUS_PROCESSING}
        if from_status:
            allowed.add(from_status)
        with self._task_lock.gen_wlock():
            task = self._get_task(task_id)
            if not task or task.status not in allowed:
                return
            task.status = TASK_STATUS_SUCCESS if success else TASK_STATUS_FAILED
            task.error_message = None if success else (error_message or "识别失败")
            task.output_path = output_path if success else ""
            self._save_task_and_update_time(task)
        self._purge_expired_tasks()

    def _drop_task(self, task_id: str) -> None:
        with self._task_lock.gen_wlock():
            if self._tasks.pop(task_id, None) is not None:
                self._save_all_tasks()

    def _pick_pending_id(self) -> str | None:
        with self._task_lock.gen_rlock():
            if any(t.status == TASK_STATUS_PROCESSING for t in self._tasks.values()):
                return None
            pending = sorted(
                (t for t in self._tasks.values() if t.status == TASK_STATUS_PENDING),
                key=lambda t: t.create_time,
            )
            return pending[0].task_id if pending else None

    def _drain_queue(self) -> None:
        task_id = self._pick_pending_id()
        if not task_id:
            return

        def job() -> None:
            video_path, language = "", "en"
            entered_processing = False
            outcome_success = False
            outcome_error: str | None = None
            outcome_path = ""
            try:
                with self._task_lock.gen_wlock():
                    task = self._get_task(task_id)
                    if not task or task.status != TASK_STATUS_PENDING:
                        return
                    task.status = TASK_STATUS_PROCESSING
                    task.error_message = None
                    self._save_task_and_update_time(task)
                    entered_processing = True
                    video_path, language = task.video_path, task.language

                if self._should_stop(task_id):
                    outcome_error = "已取消"
                else:
                    log.info("[SUBTITLE] 识别开始 %s %s", task_id, video_path)
                    try:
                        out = transcribe_to_sidecar(video_path, language=language)
                        outcome_path = str(out.get("path") or "")
                        outcome_success = True
                        log.info("[SUBTITLE] 识别完成 %s -> %s", task_id, outcome_path)
                    except Exception as e:
                        outcome_error = str(e)
                        (log.warning if isinstance(e, WhisperError) else log.error)(
                            "[SUBTITLE] 识别失败 %s: %s", task_id, e,
                        )
            except Exception as e:
                outcome_error = str(e)
                log.error("[SUBTITLE] 识别异常 %s: %s", task_id, e)
            finally:
                self._clear_stop_flag(task_id)
                if entered_processing:
                    if outcome_error == "已取消":
                        self._drop_task(task_id)
                    else:
                        self._finish_task(
                            task_id,
                            success=outcome_success,
                            error_message=outcome_error,
                            output_path=outcome_path,
                        )
                self._drain_queue()

        run_in_background(job)

    def create_task(
        self,
        video_path: str,
        *,
        language: str = "en",
        name: Optional[str] = None,
    ) -> Tuple[int, str, Optional[str]]:
        normalized, err = _normalize_video_path(video_path, self._media_base_dir)
        if not normalized:
            return -1, err, None
        task = SubtitleRecognizeTask(
            task_id="",
            name=name or os.path.basename(normalized) or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            video_path=normalized,
            language=(language or "en").strip().lower() or "en",
        )
        code, msg, task_id = self._create_task_and_save(task)
        if code == 0:
            self._drain_queue()
        return code, msg, task_id

    def start_task(self, task_id: str) -> Tuple[int, str]:
        """BaseTaskMgr 抽象方法；入队后由 create_task / enqueue 自动 _drain_queue。"""
        task, err = self._get_task_or_err(task_id)
        if not task:
            return -1, err
        if task.status != TASK_STATUS_PENDING:
            return -1, "仅 pending 任务可启动"
        self._drain_queue()
        return 0, "已加入队列"

    def enqueue(self, video_path: str, *, language: str = "en") -> dict[str, Any]:
        code, msg, task_id = self.create_task(video_path, language=language)
        if code != 0 or not task_id:
            return _err(msg)
        task = self.get_task(task_id) or {}
        return _ok({
            "task_id": task_id,
            "video_path": task.get("video_path"),
            "language": task.get("language"),
            "status": task.get("status") or TASK_STATUS_PENDING,
        })

    def cancel(self, task_id: str) -> dict[str, Any]:
        """取消/删除任务：进行中则请求停止，其余状态直接从列表移除。"""
        tid = (task_id or "").strip()
        if not tid:
            return _err("task_id 不能为空")
        task, err = self._get_task_or_err(tid)
        if not task:
            return _err(err)
        if task.status == TASK_STATUS_PROCESSING:
            code, msg = self.stop_task(tid)
            if code != 0:
                return _err(msg)
            return _ok({"task_id": tid})
        code, msg = self.delete_task(tid)
        if code != 0:
            return _err(msg)
        self._drain_queue()
        return _ok({"task_id": tid})

    def retry(self, task_id: str) -> dict[str, Any]:
        tid = (task_id or "").strip()
        if not tid:
            return _err("task_id 不能为空")
        task, err = self._get_task_or_err(tid)
        if not task:
            return _err(err)
        if task.status not in (TASK_STATUS_SUCCESS, TASK_STATUS_FAILED):
            return _err("仅已完成或失败的任务可重试")
        with self._task_lock.gen_wlock():
            task.status = TASK_STATUS_PENDING
            task.error_message = None
            task.output_path = ""
            self._save_task_and_update_time(task)
        self._drain_queue()
        return _ok({"task_id": tid, "status": TASK_STATUS_PENDING})


class SubtitleMgr:
    """ASSRT 搜索 / sidecar 字幕；识别见 ``recognize`` 队列。"""

    def __init__(self) -> None:
        self.default_base_dir = config.DEFAULT_BASE_DIR
        self.recognize = SubtitleRecognizeMgr()

    def resolve_subtitles(self, video_path: str) -> dict[str, Any]:
        try:
            normalized_video, error_msg = validate_and_normalize_path(
                video_path,
                self.default_base_dir,
                must_be_file=True,
            )
            if not normalized_video:
                return _err(error_msg or "Invalid video_path")

            tracks: list[dict[str, Any]] = []
            last_dot = normalized_video.rfind(".")
            if last_dot > 0:
                base = normalized_video[:last_dot]
                candidates = [f"{base}{suffix}{ext}" for suffix in _SUBTITLE_SUFFIXES for ext in _SUBTITLE_EXTS]
                for candidate in candidates:
                    ext = os.path.splitext(candidate)[1].lower()
                    if ext not in _SUBTITLE_EXTS:
                        continue
                    normalized, _ = validate_and_normalize_path(
                        candidate,
                        self.default_base_dir,
                        must_be_file=True,
                    )
                    if not normalized or not os.path.isfile(normalized):
                        continue
                    tracks.append({
                        "path": normalized,
                        "label": subtitle_label_from_path(normalized),
                        "lang": subtitle_lang_from_path(normalized),
                        "ext": ext.lstrip("."),
                    })

            return _ok({"tracks": tracks})
        except Exception as e:
            log.error(f"[SUBTITLE] resolve failed: {e}")
            return _err(f"resolve subtitle failed: {e}")

    def search_by_text(self, query: str, *, languages: str | None = None, page: int = 1) -> dict[str, Any]:
        q = (query or "").strip()
        if not q:
            return _err("query 不能为空")
        try:
            payload = assrt_client.search_by_query(q, languages=languages, page=page)
            return _ok(payload)
        except RecursionError:
            log.exception("[SUBTITLE] ASSRT recursion, query=%s", q)
            return _err("search subtitle failed: 在线搜索请求异常")
        except AssrtError as e:
            log.warning(f"[SUBTITLE] text search failed: {e}")
            return _err(str(e))
        except Exception as e:
            log.error(f"[SUBTITLE] text search failed: {e}")
            return _err(f"search subtitle failed: {e}")

    def recognize_subtitle(self, video_path: str, *, language: str = "en") -> dict[str, Any]:
        return self.recognize.enqueue(video_path, language=language)

    def list_recognize_tasks(self) -> dict[str, Any]:
        tasks = self.recognize.list_tasks()
        tasks.sort(key=lambda x: float(x.get("create_time") or 0))
        return _ok({"tasks": tasks})

    def cancel_recognize_task(self, task_id: str) -> dict[str, Any]:
        return self.recognize.cancel(task_id)

    def retry_recognize_task(self, task_id: str) -> dict[str, Any]:
        return self.recognize.retry(task_id)

    def download_subtitle(self, video_path: str, subtitle_id: str, *, file_index: int = 0) -> dict[str, Any]:
        path = (video_path or "").strip()
        sid = (subtitle_id or "").strip()
        if not path:
            return _err("video_path 不能为空")
        if not sid:
            return _err("subtitle_id 不能为空")

        normalized, error_msg = validate_and_normalize_path(
            path,
            self.default_base_dir,
            must_be_file=True,
        )
        if not normalized:
            return _err(error_msg or "Invalid video_path")

        try:
            result = assrt_client.download_to_sidecar(
                sid,
                normalized,
                file_index=file_index,
            )
        except AssrtError as e:
            log.warning(f"[SUBTITLE] download failed: {e}")
            return _err(str(e))
        except OSError as e:
            return _err(f"写入字幕文件失败: {e}")
        except Exception as e:
            log.error(f"[SUBTITLE] download failed: {e}")
            return _err(f"download subtitle failed: {e}")

        return _ok({
            "video_path": normalized,
            **result,
            "label": subtitle_label_from_path(result["path"]),
            "lang": subtitle_lang_from_path(result["path"]),
            "ext": os.path.splitext(result["path"])[1].lstrip(".").lower(),
        })


subtitle_mgr = SubtitleMgr()
