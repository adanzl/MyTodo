"""
文字提取管理服务。

任务由视频链接创建：yt-dlp 下载，优先使用平台字幕，没有则本地语音识别。
存档仍是 tasks.json + upload/ + output/。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from core.config import (
    TASK_STATUS_FAILED,
    TASK_STATUS_PROCESSING,
    VIDEO_DUMP_BASE_DIR,
    VIDEO_DUMP_OUTPUT_DIR,
    VIDEO_DUMP_UPLOAD_DIR,
    app_logger,
    config,
)
from core.services.base_task_mgr import BaseTaskMgr, FileInfo, TaskBase
from core.services.tools.video_dump_sites import match_site
from core.services.tools.video_dump_text import cues_to_text, pick_subtitle
from core.subtitles.whisper_client import WhisperError, transcribe_to_sidecar_sync
from core.utils import ensure_directory, get_file_info, run_subprocess_safe

log = app_logger

VideoDumpFileInfo = FileInfo
_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".flv", ".mov"}
_DOWNLOAD_TIMEOUT = 3600.0
_TEXT_LIMIT = 400_000


@dataclass
class VideoDumpTask(TaskBase):
    """文字提取任务"""
    source_url: str = ""
    platform: str = ""
    platform_label: str = ""
    stage: str = ""
    subtitle_source: str = ""
    uploaded_path: str = ""
    uploaded_info: Optional[VideoDumpFileInfo] = None
    output_path: Optional[str] = None
    output_info: Optional[VideoDumpFileInfo] = None
    subtitle_path: Optional[str] = None
    subtitle_info: Optional[VideoDumpFileInfo] = None


class VideoDumpMgr(BaseTaskMgr[VideoDumpTask]):
    """文字提取管理器（任务模式）"""

    TASK_META_FILE = "tasks.json"

    def __init__(self) -> None:
        super().__init__(base_dir=VIDEO_DUMP_BASE_DIR)

    def _task_from_dict(self, data: dict) -> VideoDumpTask:
        fields = {key: data[key] for key in VideoDumpTask.__dataclass_fields__ if key in data}
        return VideoDumpTask(**fields)

    def _get_output_path(self, task_id: str) -> str:
        return os.path.join(VIDEO_DUMP_OUTPUT_DIR, f"{task_id}.txt")

    def _task_dir(self, task_id: str) -> str:
        return os.path.join(VIDEO_DUMP_UPLOAD_DIR, task_id)

    def _load_history_tasks(self) -> None:
        super()._load_history_tasks()
        changed = False
        with self._task_lock.gen_wlock():
            for task in self._tasks.values():
                if task.status == TASK_STATUS_PROCESSING:
                    task.status = TASK_STATUS_FAILED
                    task.error_message = task.error_message or "任务已中断"
                    task.stage = ""
                    changed = True
                if task.uploaded_path and os.path.isfile(task.uploaded_path):
                    info = get_file_info(task.uploaded_path)
                    if info:
                        task.uploaded_info = info
                if task.output_path and os.path.isfile(task.output_path):
                    task.output_info = get_file_info(task.output_path)
                elif task.output_path:
                    task.output_path = None
                    task.output_info = None
                if task.subtitle_path and os.path.isfile(task.subtitle_path):
                    task.subtitle_info = get_file_info(task.subtitle_path)
                elif task.subtitle_path:
                    task.subtitle_path = None
                    task.subtitle_info = None
            if changed:
                self._save_all_tasks()

    def _has_processing(self) -> bool:
        return any(task.status == TASK_STATUS_PROCESSING for task in self._tasks.values())

    def submit_url(self, url: str) -> Tuple[int, str, Optional[str]]:
        """创建任务并开始下载、提取。同一时间只跑一个任务。"""
        raw = (url or "").strip()
        if not raw.startswith(("http://", "https://")):
            return -1, "请输入 http 或 https 链接", None
        if len(raw) > 2000:
            return -1, "链接过长", None

        site = match_site(raw)
        with self._task_lock.gen_rlock():
            if self._has_processing():
                return -1, "已有任务正在处理", None

        task = VideoDumpTask(
            task_id="",
            name=raw[:80],
            source_url=raw,
            platform=site.id if site else "other",
            platform_label=site.label if site else "其他",
            stage="准备下载",
        )
        code, msg, task_id = self._create_task_and_save(task)
        if code != 0 or not task_id:
            return code, msg, task_id
        start_code, start_msg = self.start_task(task_id)
        if start_code != 0:
            self.delete_task(task_id)
            return start_code, start_msg, None
        return 0, "已开始提取", task_id

    def create_task(self, *args: Any, **kwargs: Any) -> Tuple[int, str, Optional[str]]:
        url = kwargs.get("url") or (args[0] if args else "")
        return self.submit_url(str(url))

    def start_task(self, task_id: str, *args: Any, **kwargs: Any) -> Tuple[int, str]:
        with self._task_lock.gen_wlock():
            task, err = self._get_task_or_err(task_id)
            if not task:
                return -1, err
            if not task.source_url:
                return -1, "任务没有视频链接"
            if self._has_processing():
                return -1, "已有任务正在处理"
            task.status = TASK_STATUS_PROCESSING
            task.stage = "准备下载"
            task.error_message = None
            self._save_task_and_update_time(task)

        self._run_task_async(task_id, lambda current: self._extract(current.task_id))
        return 0, "已开始提取"

    def _patch(self, task_id: str, **fields: Any) -> None:
        with self._task_lock.gen_wlock():
            task = self._get_task(task_id)
            if not task:
                return
            for key, value in fields.items():
                setattr(task, key, value)
            self._save_task_and_update_time(task)

    def _extract(self, task_id: str) -> None:
        task = self._get_task(task_id)
        if not task:
            raise Exception("任务不存在")
        self._patch(task_id, stage="正在下载")
        title, video_path = self._download(task_id, task.source_url)
        video_info = get_file_info(video_path)
        if not video_info:
            raise Exception("下载完成但找不到视频文件")
        self._patch(
            task_id,
            name=(title or task.source_url)[:80],
            uploaded_path=video_path,
            uploaded_info=video_info,
            stage="正在提取字幕",
        )

        directory = os.path.dirname(video_path)
        subtitle_path = pick_subtitle(directory, video_path)
        text = cues_to_text(subtitle_path).strip() if subtitle_path else ""
        source = "platform"
        if not text:
            self._patch(task_id, stage="正在识别语音")
            try:
                transcribe_to_sidecar_sync(video_path, language="zh")
            except WhisperError as exc:
                raise Exception(str(exc)) from exc
            base, _ext = os.path.splitext(video_path)
            whisper_path = base + ".zh.vtt"
            subtitle_path = whisper_path if os.path.isfile(whisper_path) else pick_subtitle(directory, video_path)
            text = cues_to_text(subtitle_path).strip() if subtitle_path else ""
            source = "whisper"
        if not subtitle_path or not text:
            raise Exception("没有平台字幕，语音识别也没有得到文本")

        ensure_directory(VIDEO_DUMP_OUTPUT_DIR)
        text_path = self._get_output_path(task_id)
        with open(text_path, "w", encoding="utf-8") as handle:
            handle.write(text)
        ext = os.path.splitext(subtitle_path)[1].lower() or ".vtt"
        saved_sub = os.path.join(VIDEO_DUMP_OUTPUT_DIR, f"{task_id}{ext}")
        if os.path.abspath(subtitle_path) != os.path.abspath(saved_sub):
            shutil.copyfile(subtitle_path, saved_sub)
        self._patch(
            task_id,
            output_path=text_path,
            output_info=get_file_info(text_path),
            subtitle_path=saved_sub,
            subtitle_info=get_file_info(saved_sub),
            subtitle_source=source,
            stage="完成",
        )

    def _download(self, task_id: str, url: str) -> Tuple[str, str]:
        dest = self._task_dir(task_id)
        ensure_directory(dest)
        outtmpl = os.path.join(dest, "%(id)s.%(ext)s")
        ffmpeg_dir = os.path.dirname(config.FFMPEG_PATH) or config.FFMPEG_PATH
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-playlist",
            "--no-warnings",
            "--no-progress",
            "--retries", "3",
            "--socket-timeout", "30",
            "-o", outtmpl,
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", "ai-zh,zh-Hans,zh-CN,zh.*",
            "--convert-subs", "vtt",
            "--merge-output-format", "mp4",
            "--ffmpeg-location", ffmpeg_dir,
            "--print-json",
            url,
        ]
        cookies = (config.VIDEO_DUMP_COOKIES_FILE or "").strip()
        if cookies and os.path.isfile(cookies):
            cmd[-1:-1] = ["--cookies", cookies]
        code, stdout, stderr = run_subprocess_safe(cmd, timeout=_DOWNLOAD_TIMEOUT)
        if code != 0:
            tail = _last_line(stderr or stdout) or f"退出码 {code}"
            raise Exception(f"下载失败: {tail[:300]}")

        info = _last_json(stdout)
        title = ""
        video_path = ""
        if info:
            title = str(info.get("title") or "").strip()
            downloads = info.get("requested_downloads") or []
            if downloads:
                video_path = str(downloads[-1].get("filepath") or "")
        if not video_path or not os.path.isfile(video_path):
            video_path = _largest_video(dest) or ""
        if not video_path:
            raise Exception("下载结束但没有视频文件")
        return title, video_path

    def get_task(self, task_id: str) -> Optional[dict]:
        data = super().get_task(task_id)
        if not data:
            return None
        path = data.get("output_path") or ""
        text = ""
        if path and os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read(_TEXT_LIMIT)
        data["text"] = text
        return data

    def resolve_download(self, task_id: str, kind: str) -> Optional[str]:
        with self._task_lock.gen_rlock():
            task = self._get_task(task_id)
            if not task:
                return None
            path = {
                "video": task.uploaded_path,
                "text": task.output_path,
                "subtitle": task.subtitle_path,
            }.get(kind)
        if not path:
            return None
        return _path_inside(path, VIDEO_DUMP_BASE_DIR)

    def _before_delete_task(self, task: VideoDumpTask) -> None:
        errors: list[str] = []
        paths = [
            self._task_dir(task.task_id),
            task.uploaded_path,
            task.output_path,
            task.subtitle_path,
            self._get_output_path(task.task_id),
        ]
        seen: set[str] = set()
        for path in paths:
            if not path:
                continue
            real = _path_inside(path, VIDEO_DUMP_BASE_DIR) if os.path.lexists(path) else ""
            if not real:
                continue
            key = os.path.normcase(real)
            if key in seen:
                continue
            seen.add(key)
            try:
                if os.path.isdir(real):
                    shutil.rmtree(real)
                else:
                    os.remove(real)
                log.info(f"[文字提取] 删除: {real}")
            except Exception as exc:
                log.error(f"[文字提取] 删除失败 {real}: {exc}")
                errors.append(f"{real}: {exc}")
        if errors:
            raise OSError("删除关联文件失败: " + "; ".join(errors))


def _last_line(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _last_json(stdout: str) -> Optional[dict]:
    found: Optional[dict] = None
    for line in (stdout or "").splitlines():
        raw = line.strip()
        if not raw.startswith("{"):
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            found = parsed
    return found


def _largest_video(directory: str) -> Optional[str]:
    best = ""
    best_size = -1
    try:
        names = os.listdir(directory)
    except OSError:
        return None
    for name in names:
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        if os.path.splitext(name)[1].lower() not in _VIDEO_EXTS:
            continue
        size = os.path.getsize(path)
        if size > best_size:
            best = path
            best_size = size
    return best or None


def _path_inside(path: str, root: str) -> Optional[str]:
    real = os.path.realpath(path)
    base = os.path.realpath(root)
    if os.path.normcase(real) == os.path.normcase(base):
        return None
    prefix = os.path.normcase(base + os.sep)
    if not os.path.normcase(real).startswith(prefix):
        return None
    if not os.path.lexists(real):
        return None
    return real


video_dump_mgr = VideoDumpMgr()
