import os
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def audio_convert_env(monkeypatch, tmp_path):
    import core.services.audio_convert_mgr as ac

    # Redirect media dir into tmp
    monkeypatch.setattr(ac, "MEDIA_BASE_DIR", str(tmp_path / "media"))
    monkeypatch.setattr(ac, "FFMPEG_PATH", "ffmpeg")
    monkeypatch.setattr(ac, "FFMPEG_TIMEOUT", 1)

    # Avoid loading any history
    monkeypatch.setattr(ac.AudioConvertMgr, "_load_history_tasks", lambda self: None)

    # Make ensure_directory stable
    monkeypatch.setattr(ac, "ensure_directory", lambda p: os.makedirs(p, exist_ok=True))

    # Avoid real gevent spawn in duration update
    def fake_start_async(self, task_id, file_paths):
        return

    monkeypatch.setattr(ac.AudioConvertMgr, "_start_async_duration_update", fake_start_async)

    # Deterministic duration
    monkeypatch.setattr(ac, "get_media_duration", lambda p: 9.9)

    return ac


def test_create_task_validations(audio_convert_env):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg, tid = mgr.create_task(output_dir="   ")
    assert code == -1

    code, msg, tid = mgr.create_task(name="n", output_dir="mp3", overwrite=False)
    assert code == 0
    assert tid


def test_update_task_scans_and_initializes_file_status(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg, tid = mgr.create_task(name="n")
    assert code == 0

    # create a directory with media files, including output dir which should be skipped
    d = tmp_path / "in"
    (d / "mp3").mkdir(parents=True)
    f1 = d / "a.mp3"
    f2 = d / "b.mp4"
    f3 = d / "mp3" / "skip.mp3"
    f1.write_bytes(b"1")
    f2.write_bytes(b"2")
    f3.write_bytes(b"3")

    code, msg = mgr.update_task(tid, directory=str(d), output_dir="mp3")
    assert code == 0

    task = mgr._tasks[tid]
    assert task.directory == str(d)
    assert task.total_files == 2
    assert task.file_status is not None
    assert str(f1) in task.file_status
    assert str(f2) in task.file_status
    assert str(f3) not in task.file_status


def test_update_task_errors(audio_convert_env, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg = mgr.update_task("nope", name="x")
    assert code == -1

    code, msg, tid = mgr.create_task(name="n")
    assert code == 0

    # invalid name
    code, msg = mgr.update_task(tid, name="   ")
    assert code == -1

    # invalid directory
    code, msg = mgr.update_task(tid, directory=str(tmp_path / "missing"))
    assert code == -1

    # path is not directory
    f = tmp_path / "file"
    f.write_text("x")
    code, msg = mgr.update_task(tid, directory=str(f))
    assert code == -1

    # no fields
    code, msg = mgr.update_task(tid)
    assert code == -1


def test_update_task_refuses_when_processing(audio_convert_env):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg, tid = mgr.create_task(name="n")
    assert code == 0

    mgr._tasks[tid].status = ac.TASK_STATUS_PROCESSING

    code, msg = mgr.update_task(tid, name="x")
    assert code == -1


def test_ensure_output_directory(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    out_dir = tmp_path / "out"

    ok, err = mgr._ensure_output_directory(str(out_dir))
    assert ok is True

    # simulate no write permission
    monkeypatch.setattr(ac.os, "access", lambda p, mode: False)
    ok, err = mgr._ensure_output_directory(str(out_dir))
    assert ok is False


def test_ensure_output_directory_existing_dir_writable(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    monkeypatch.setattr(ac.os, "access", lambda p, mode: True)

    ok, err = mgr._ensure_output_directory(str(out_dir))
    assert ok is True


def test_ensure_output_directory_permission_error(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    out_dir = tmp_path / "out"

    def raise_perm(path, exist_ok=True):
        raise PermissionError("no")

    monkeypatch.setattr(ac.os, "makedirs", raise_perm)

    ok, err = mgr._ensure_output_directory(str(out_dir))
    assert ok is False


def test_ensure_output_directory_os_error(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    out_dir = tmp_path / "out"

    def raise_oserr(path, exist_ok=True):
        raise OSError("no")

    monkeypatch.setattr(ac.os, "makedirs", raise_oserr)

    ok, err = mgr._ensure_output_directory(str(out_dir))
    assert ok is False


def test_convert_file_to_mp3_success_and_failures(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    in_f = tmp_path / "in.mp4"
    in_f.write_bytes(b"x")

    out_f = tmp_path / "mp3" / "in.mp3"

    # Success path
    def fake_run(cmds, timeout=1):
        os.makedirs(os.path.dirname(out_f), exist_ok=True)
        out_f.write_bytes(b"ok")
        return 0, "", ""

    monkeypatch.setattr(ac, "run_subprocess_safe", fake_run)

    ok, err = mgr._convert_file_to_mp3(str(in_f), str(out_f))
    assert ok is True
    assert err is None

    # Timeout
    def fake_run_timeout(cmds, timeout=1):
        raise TimeoutError("t")

    monkeypatch.setattr(ac, "run_subprocess_safe", fake_run_timeout)
    ok, err = mgr._convert_file_to_mp3(str(in_f), str(out_f))
    assert ok is False

    # ffmpeg not found
    def fake_run_fnf(cmds, timeout=1):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(ac, "run_subprocess_safe", fake_run_fnf)
    ok, err = mgr._convert_file_to_mp3(str(in_f), str(out_f))
    assert ok is False

    # generic exception
    monkeypatch.setattr(ac, "run_subprocess_safe", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    ok, err = mgr._convert_file_to_mp3(str(in_f), str(out_f))
    assert ok is False

    # returncode != 0
    monkeypatch.setattr(ac, "run_subprocess_safe", lambda *a, **kw: (1, "", "bad"))
    ok, err = mgr._convert_file_to_mp3(str(in_f), str(out_f))
    assert ok is False


def test_convert_file_to_mp3_output_not_created(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    in_f = tmp_path / "in.mp4"
    in_f.write_bytes(b"x")

    out_f = tmp_path / "mp3" / "in.mp3"

    # returncode 0 but output file missing
    monkeypatch.setattr(ac, "run_subprocess_safe", lambda *a, **kw: (0, "", ""))
    monkeypatch.setattr(ac.os.path, "exists", lambda p: False)

    ok, err = mgr._convert_file_to_mp3(str(in_f), str(out_f))
    assert ok is False


def test_convert_directory_empty_and_overwrite_false(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg, tid = mgr.create_task(name="n")
    assert code == 0

    task = mgr._tasks[tid]

    # no directory
    task.directory = str(tmp_path / "missing")
    mgr._convert_directory(task)
    assert task.status == ac.TASK_STATUS_FAILED

    # empty directory
    d = tmp_path / "dir"
    d.mkdir()
    task.directory = str(d)

    # Ensure scan returns empty
    monkeypatch.setattr(mgr, "_scan_media_files", lambda directory, output_dir: [])
    mgr._convert_directory(task)
    assert task.status == ac.TASK_STATUS_SUCCESS

    # overwrite false should skip existing output
    f1 = d / "a.mp3"
    f1.write_bytes(b"x")
    out_dir = d / task.output_dir
    out_dir.mkdir()
    (out_dir / "a.mp3").write_bytes(b"exists")

    monkeypatch.setattr(mgr, "_scan_media_files", lambda directory, output_dir: [str(f1)])
    task.overwrite = False

    # Make convert not called by ensuring output exists
    mgr._convert_directory(task)
    assert task.status == ac.TASK_STATUS_SUCCESS


def test_convert_directory_ensure_output_directory_failed(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg, tid = mgr.create_task(name="n")
    assert code == 0

    d = tmp_path / "dir"
    d.mkdir()
    mgr._tasks[tid].directory = str(d)

    monkeypatch.setattr(mgr, "_scan_media_files", lambda directory, output_dir: [str(d / "a.mp3")])
    monkeypatch.setattr(mgr, "_ensure_output_directory", lambda p: (False, "no"))

    mgr._convert_directory(mgr._tasks[tid])
    assert mgr._tasks[tid].status == ac.TASK_STATUS_FAILED


def test_convert_directory_stop_flag_early(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg, tid = mgr.create_task(name="n")
    assert code == 0

    d = tmp_path / "dir"
    d.mkdir()
    f1 = d / "a.mp3"
    f1.write_bytes(b"x")

    task = mgr._tasks[tid]
    task.directory = str(d)

    monkeypatch.setattr(mgr, "_scan_media_files", lambda directory, output_dir: [str(f1)])
    monkeypatch.setattr(mgr, "_ensure_output_directory", lambda p: (True, None))

    # _convert_directory 会在开始时重置 stop flag，因此这里通过 mock _convert_file_to_mp3
    # 让其在第一次转换时设置 stop flag，以覆盖循环中的“任务被停止”分支。
    def fake_convert(input_file, output_file):
        mgr._stop_flags[tid] = True
        return True, None

    monkeypatch.setattr(mgr, "_convert_file_to_mp3", fake_convert)

    mgr._convert_directory(task)
    assert task.status == ac.TASK_STATUS_FAILED


def test_convert_directory_handles_exception(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg, tid = mgr.create_task(name="n")
    assert code == 0

    task = mgr._tasks[tid]
    task.directory = str(tmp_path)

    monkeypatch.setattr(mgr, "_scan_media_files", lambda directory, output_dir:
                        (_ for _ in ()).throw(RuntimeError("boom")))

    mgr._convert_directory(task)
    assert task.status == ac.TASK_STATUS_FAILED


def test_get_task_and_list(audio_convert_env):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg, tid = mgr.create_task(name="n")
    assert code == 0

    assert mgr.get_task("nope") is None

    info = mgr.get_task(tid)
    assert info is not None
    assert info["task_id"] == tid

    lst = mgr.get_task_list()
    assert isinstance(lst, list)
    assert any(x["task_id"] == tid for x in lst)


def test_start_task_and_delete_task(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg = mgr.start_task("nope")
    assert code == -1

    code, msg, tid = mgr.create_task(name="n")
    assert code == 0

    # cannot start without directory
    code, msg = mgr.start_task(tid)
    assert code == -1

    # set directory and make threading synchronous
    d = tmp_path / "dir"
    d.mkdir()
    mgr._tasks[tid].directory = str(d)

    class FakeThread:

        def __init__(self, target, args, daemon):
            self._target = target
            self._args = args

        def start(self):
            self._target(*self._args)

    monkeypatch.setattr(ac.threading, "Thread", FakeThread)
    monkeypatch.setattr(mgr, "_scan_media_files", lambda directory, output_dir: [])

    code, msg = mgr.start_task(tid)
    assert code == 0

    # delete while processing sets stop flag
    mgr._tasks[tid].status = ac.TASK_STATUS_PROCESSING
    code, msg = mgr.delete_task(tid)
    assert code == 0

    # delete missing
    code, msg = mgr.delete_task(tid)
    assert code == -1


def test_start_task_refuses_when_processing(audio_convert_env):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg, tid = mgr.create_task(name="n")
    assert code == 0

    mgr._tasks[tid].status = ac.TASK_STATUS_PROCESSING

    code, msg = mgr.start_task(tid)
    assert code == -1


def test_delete_task_removes_meta_file_and_handles_remove_error(audio_convert_env, monkeypatch, tmp_path):
    ac = audio_convert_env
    mgr = ac.AudioConvertMgr()

    code, msg, tid = mgr.create_task(name="n")
    assert code == 0

    meta_file = mgr._get_task_meta_file(tid)
    os.makedirs(os.path.dirname(meta_file), exist_ok=True)
    with open(meta_file, "w", encoding="utf-8") as f:
        f.write("x")

    def raise_remove(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(ac.os, "remove", raise_remove)

    code, msg = mgr.delete_task(tid)
    assert code == 0
