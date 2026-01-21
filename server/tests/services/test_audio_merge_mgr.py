import os
import json

import pytest


@pytest.fixture
def audio_merge_env(monkeypatch, tmp_path):
    import core.services.audio_merge_mgr as am

    # Redirect base dir into tmp
    monkeypatch.setattr(am, "MEDIA_BASE_DIR", str(tmp_path / "media"))
    monkeypatch.setattr(am, "FFMPEG_PATH", "ffmpeg")
    monkeypatch.setattr(am, "FFMPEG_TIMEOUT", 1)

    monkeypatch.setattr(am, "get_media_task_dir", lambda tid: str(tmp_path / "media" / tid))
    monkeypatch.setattr(am, "get_media_task_result_dir", lambda tid: str(tmp_path / "media" / tid / "result"))

    monkeypatch.setattr(am, "ensure_directory", lambda p: os.makedirs(p, exist_ok=True))

    # Make duration deterministic
    monkeypatch.setattr(am, "get_media_duration", lambda p: 12.3)

    return am


def test_create_task_add_remove_reorder(audio_merge_env, tmp_path):
    am = audio_merge_env

    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0
    assert task_id

    task_dir = am.get_media_task_dir(task_id)
    result_dir = am.get_media_task_result_dir(task_id)
    assert os.path.isdir(task_dir)
    assert os.path.isdir(result_dir)

    # create dummy files
    f1 = tmp_path / "a.mp3"
    f2 = tmp_path / "b.mp3"
    f1.write_bytes(b"1")
    f2.write_bytes(b"2")

    code, msg = mgr.add_file(task_id, str(f1), "a.mp3")
    assert code == 0
    code, msg = mgr.add_file(task_id, str(f2), "b.mp3")
    assert code == 0

    t = mgr._tasks[task_id]
    assert len(t.files) == 2
    assert t.files[0]["index"] == 0
    assert t.files[1]["index"] == 1

    # reorder
    code, msg = mgr.reorder_files(task_id, [1, 0])
    assert code == 0
    t = mgr._tasks[task_id]
    assert t.files[0]["name"] == "b.mp3"
    assert t.files[0]["index"] == 0

    # remove
    code, msg = mgr.remove_file(task_id, 0)
    assert code == 0
    assert len(mgr._tasks[task_id].files) == 1
    assert mgr._tasks[task_id].files[0]["index"] == 0


def test_reorder_files_invalid_inputs(audio_merge_env, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f2 = tmp_path / "b.mp3"
    f1.write_bytes(b"1")
    f2.write_bytes(b"2")
    assert mgr.add_file(task_id, str(f1), "a.mp3")[0] == 0
    assert mgr.add_file(task_id, str(f2), "b.mp3")[0] == 0

    # wrong length
    code, msg = mgr.reorder_files(task_id, [0])
    assert code == -1

    # not a permutation
    code, msg = mgr.reorder_files(task_id, [0, 0])
    assert code == -1


def test_add_file_validations(audio_merge_env, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    # task not exist
    code, msg = mgr.add_file("nope", str(tmp_path / "x.mp3"), "x.mp3")
    assert code == -1

    # file not exist
    code, msg = mgr.add_file(task_id, str(tmp_path / "x.mp3"), "x.mp3")
    assert code == -1

    # invalid ext
    p = tmp_path / "x.txt"
    p.write_bytes(b"x")
    code, msg = mgr.add_file(task_id, str(p), "x.txt")
    assert code == -1


def test_add_file_refuses_when_processing(audio_merge_env, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")

    mgr._tasks[task_id].status = am.TASK_STATUS_PROCESSING

    code, msg = mgr.add_file(task_id, str(f1), "a.mp3")
    assert code == -1


def test_remove_file_index_invalid(audio_merge_env, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")
    assert mgr.add_file(task_id, str(f1), "a.mp3")[0] == 0

    code, msg = mgr.remove_file(task_id, -1)
    assert code == -1

    code, msg = mgr.remove_file(task_id, 2)
    assert code == -1


def test_remove_file_refuses_when_processing(audio_merge_env, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")
    assert mgr.add_file(task_id, str(f1), "a.mp3")[0] == 0

    mgr._tasks[task_id].status = am.TASK_STATUS_PROCESSING

    code, msg = mgr.remove_file(task_id, 0)
    assert code == -1


def test_reorder_refuses_when_processing(audio_merge_env, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")
    assert mgr.add_file(task_id, str(f1), "a.mp3")[0] == 0

    mgr._tasks[task_id].status = am.TASK_STATUS_PROCESSING

    code, msg = mgr.reorder_files(task_id, [0])
    assert code == -1


def test_start_task_validations(audio_merge_env):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    # task not exist
    assert mgr.start_task("nope")[0] == -1

    # empty files
    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0
    assert mgr.start_task(task_id)[0] == -1


def test_start_task_already_processing(audio_merge_env, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    mgr._tasks[task_id].status = am.TASK_STATUS_PROCESSING

    code, msg = mgr.start_task(task_id)
    assert code == -1


def test_start_task_thread_success(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")
    assert mgr.add_file(task_id, str(f1), "a.mp3")[0] == 0

    # make merge deterministic and avoid ffmpeg
    monkeypatch.setattr(
        mgr,
        "_merge_audio_files",
        lambda tid, files: (os.path.join(am.get_media_task_result_dir(tid), "merged.mp3"), 3.0),
    )

    # run background thread immediately
    class FakeThread:

        def __init__(self, target, daemon=True):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr(am.threading, "Thread", FakeThread)

    code, msg = mgr.start_task(task_id)
    assert code == 0

    t = mgr._tasks[task_id]
    assert t.status == am.TASK_STATUS_SUCCESS
    assert t.result_file is not None
    assert t.result_duration == 3.0


def test_start_task_thread_success_fallback_duration(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")
    assert mgr.add_file(task_id, str(f1), "a.mp3")[0] == 0

    result_file = os.path.join(am.get_media_task_result_dir(task_id), "merged.mp3")

    monkeypatch.setattr(mgr, "_merge_audio_files", lambda tid, files: (result_file, None))
    monkeypatch.setattr(am, "get_media_duration", lambda p: 8.8)

    class FakeThread:

        def __init__(self, target, daemon=True):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr(am.threading, "Thread", FakeThread)

    code, msg = mgr.start_task(task_id)
    assert code == 0
    assert mgr._tasks[task_id].status == am.TASK_STATUS_SUCCESS
    assert mgr._tasks[task_id].result_duration == 8.8


def test_start_task_thread_failure(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")
    assert mgr.add_file(task_id, str(f1), "a.mp3")[0] == 0

    monkeypatch.setattr(mgr, "_merge_audio_files", lambda tid, files: (None, None))

    class FakeThread:

        def __init__(self, target, daemon=True):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr(am.threading, "Thread", FakeThread)

    code, msg = mgr.start_task(task_id)
    assert code == 0

    t = mgr._tasks[task_id]
    assert t.status == am.TASK_STATUS_FAILED
    assert t.result_duration is None


def test_start_task_thread_exception(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")
    assert mgr.add_file(task_id, str(f1), "a.mp3")[0] == 0

    def boom(tid, files):
        raise Exception("boom")

    monkeypatch.setattr(mgr, "_merge_audio_files", boom)

    class FakeThread:

        def __init__(self, target, daemon=True):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr(am.threading, "Thread", FakeThread)

    code, msg = mgr.start_task(task_id)
    assert code == 0

    t = mgr._tasks[task_id]
    assert t.status == am.TASK_STATUS_FAILED
    assert t.error_message


def test_get_file_duration_with_ffmpeg(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")

    # parse ok
    monkeypatch.setattr(am, "run_subprocess_safe", lambda *a, **kw: (0, "", "Duration: 00:00:01.00"))
    assert mgr._get_file_duration_with_ffmpeg(str(f1)) == 1.0

    # exception -> None
    def bad(*a, **kw):
        raise Exception("x")

    monkeypatch.setattr(am, "run_subprocess_safe", bad)
    assert mgr._get_file_duration_with_ffmpeg(str(f1)) is None


def test_merge_audio_files_single_and_multi(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    result_dir = am.get_media_task_result_dir(task_id)
    os.makedirs(result_dir, exist_ok=True)

    # single file -> copy2
    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")

    monkeypatch.setattr(am.shutil, "copy2", lambda src, dst: open(dst, "wb").write(open(src, "rb").read()))
    monkeypatch.setattr(mgr, "_get_result_duration", lambda result_file, fallback_duration=None: fallback_duration)

    result_file, duration = mgr._merge_audio_files(task_id, [{"path": str(f1), "duration": 5.0}])
    assert result_file
    assert duration == 5.0

    # multi file -> run_subprocess_safe
    f2 = tmp_path / "b.mp3"
    f2.write_bytes(b"2")

    def fake_run(cmds, timeout=1):
        out_path = cmds[-1]
        with open(out_path, "wb") as f:
            f.write(b"merged")
        return 0, "", "Duration: 00:00:10.00"

    monkeypatch.setattr(am, "run_subprocess_safe", fake_run)

    result_file2, duration2 = mgr._merge_audio_files(task_id, [{"path": str(f1)}, {"path": str(f2)}])
    assert result_file2
    assert duration2 == 10.0


def test_merge_audio_files_timeout_and_error(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f2 = tmp_path / "b.mp3"
    f1.write_bytes(b"1")
    f2.write_bytes(b"2")

    # TimeoutError
    monkeypatch.setattr(am, "run_subprocess_safe", lambda *a, **kw: (_ for _ in ()).throw(TimeoutError("t")))
    assert mgr._merge_audio_files(task_id, [{"path": str(f1)}, {"path": str(f2)}]) == (None, None)

    # generic error
    monkeypatch.setattr(am, "run_subprocess_safe", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    assert mgr._merge_audio_files(task_id, [{"path": str(f1)}, {"path": str(f2)}]) == (None, None)


def test_merge_audio_files_returncode_nonzero(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f2 = tmp_path / "b.mp3"
    f1.write_bytes(b"1")
    f2.write_bytes(b"2")

    monkeypatch.setattr(am, "run_subprocess_safe", lambda *a, **kw: (1, "", "bad"))
    assert mgr._merge_audio_files(task_id, [{"path": str(f1)}, {"path": str(f2)}]) == (None, None)


def test_parse_duration(audio_merge_env):
    mgr = audio_merge_env.AudioMergeMgr()

    assert mgr._parse_duration_from_ffmpeg_output("Duration: 00:01:02.50") == 62.5
    assert mgr._parse_duration_from_ffmpeg_output("no duration") is None


def test_get_task_fills_duration(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    result_dir = am.get_media_task_result_dir(task_id)
    os.makedirs(result_dir, exist_ok=True)
    result_file = os.path.join(result_dir, "merged.mp3")
    with open(result_file, "wb") as f:
        f.write(b"x")

    t = am.AudioMergeTask(
        task_id=task_id,
        name="t",
        status=am.TASK_STATUS_SUCCESS,
        files=[],
        result_file=result_file,
        result_duration=None,
        error_message=None,
        create_time=1,
        update_time=1,
    )
    mgr._tasks[task_id] = t

    monkeypatch.setattr(mgr, "_get_result_duration", lambda rf, fallback_duration=None: 7.7)

    data = mgr.get_task(task_id)
    assert data["result_duration"] == 7.7


def test_get_task_duration_update_exception_is_ignored(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    result_dir = am.get_media_task_result_dir(task_id)
    os.makedirs(result_dir, exist_ok=True)
    result_file = os.path.join(result_dir, "merged.mp3")
    with open(result_file, "wb") as f:
        f.write(b"x")

    t = am.AudioMergeTask(
        task_id=task_id,
        name="t",
        status=am.TASK_STATUS_SUCCESS,
        files=[],
        result_file=result_file,
        result_duration=None,
        error_message=None,
        create_time=1,
        update_time=1,
    )
    mgr._tasks[task_id] = t

    monkeypatch.setattr(mgr, "_get_result_duration", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))

    data = mgr.get_task(task_id)
    assert data["result_duration"] is None


def test_list_tasks_sorting(audio_merge_env):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    t1 = am.AudioMergeTask(task_id="t1",
                           name="t1",
                           status=am.TASK_STATUS_PENDING,
                           files=[],
                           create_time=1,
                           update_time=1)
    t2 = am.AudioMergeTask(task_id="t2",
                           name="t2",
                           status=am.TASK_STATUS_PENDING,
                           files=[],
                           create_time=2,
                           update_time=2)

    mgr._tasks = {"t1": t1, "t2": t2}

    lst = mgr.list_tasks()
    assert lst[0]["task_id"] == "t2"


def test_delete_task(audio_merge_env, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    task_dir = am.get_media_task_dir(task_id)
    assert os.path.isdir(task_dir)

    code, msg = mgr.delete_task(task_id)
    assert code == 0

    code, msg = mgr.delete_task(task_id)
    assert code == -1


def test_delete_task_refuses_when_processing(audio_merge_env, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0

    mgr._tasks[task_id].status = am.TASK_STATUS_PROCESSING

    code, msg = mgr.delete_task(task_id)
    assert code == -1


def test_validate_file_and_not_processing_helpers(audio_merge_env, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    # _validate_file: not exists
    assert "文件不存在" in (mgr._validate_file(str(tmp_path / "nope.mp3"), "nope.mp3") or "")

    # _validate_file: invalid ext
    p = tmp_path / "x.txt"
    p.write_text("x")
    assert "不支持的文件类型" in (mgr._validate_file(str(p), "x.txt") or "")

    # _validate_task_not_processing
    code, msg, task_id = mgr.create_task(name="t")
    assert code == 0
    task = mgr._tasks[task_id]
    task.status = am.TASK_STATUS_PROCESSING
    assert "无法" in (mgr._validate_task_not_processing(task, "添加文件") or "")


def test_save_all_tasks_open_error_is_caught(audio_merge_env, monkeypatch):
    import builtins

    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    mgr._tasks["t1"] = am.AudioMergeTask(task_id="t1", name="n", status=am.TASK_STATUS_PENDING, files=[])

    monkeypatch.setattr(builtins, "open", lambda *a, **kw: (_ for _ in ()).throw(OSError("no")))

    # should not raise
    mgr._save_all_tasks()


def test_load_history_tasks(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env

    task1_id = "task1"
    task2_id = "task2_missing_dir"
    task3_id = "task3_missing_file"
    task4_id = "task4_missing_result"

    (tmp_path / "media" / task1_id).mkdir(parents=True)
    (tmp_path / "media" / task3_id).mkdir(parents=True)
    (tmp_path / "media" / task4_id).mkdir(parents=True)

    valid_file_path = tmp_path / "audio.mp3"
    valid_file_path.write_text("audio")

    result_file_path = tmp_path / "media" / task1_id / "result" / "merged.mp3"
    result_file_path.parent.mkdir(parents=True)
    result_file_path.write_text("result")

    mock_tasks_data = {
        task1_id: {
            "name": "Task 1",
            "status": "success",
            "files": [{
                "path": str(valid_file_path)
            }],
            "result_file": str(result_file_path),
        },
        task2_id: {
            "name": "Task 2"
        },
        task3_id: {
            "name": "Task 3",
            "files": [{
                "path": "/path/to/nonexistent.mp3"
            }],
        },
        task4_id: {
            "name": "Task 4",
            "result_file": "/path/to/nonexistent_result.mp3",
        },
    }

    mgr = am.AudioMergeMgr()
    monkeypatch.setattr(mgr, "_read_tasks_from_file", lambda path: mock_tasks_data)

    mgr._load_history_tasks()

    assert task1_id in mgr._tasks
    assert task2_id not in mgr._tasks
    assert mgr._tasks[task3_id].files == []
    assert mgr._tasks[task4_id].result_file is None


def test_read_tasks_from_file(audio_merge_env, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    assert mgr._read_tasks_from_file("nope") is None

    p = tmp_path / "bad.json"
    p.write_text("{")
    assert mgr._read_tasks_from_file(str(p)) is None


def test_create_task_no_name(audio_merge_env):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task()
    assert code == 0

    data = mgr.get_task(task_id)
    assert data is not None
    assert data["name"]


def test_create_task_exception(audio_merge_env, monkeypatch):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    def boom(*args, **kwargs):
        raise OSError("Disk full")

    monkeypatch.setattr(os, "makedirs", boom)

    code, msg, task_id = mgr.create_task("t")
    assert code == -1
    assert "Disk full" in msg


def test_add_file_exception(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task("t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")

    monkeypatch.setattr(am, "get_media_duration", lambda p: (_ for _ in ()).throw(Exception("boom")))

    code, msg = mgr.add_file(task_id, str(f1), "a.mp3")
    assert code == -1
    assert "boom" in msg


def test_remove_file_exception(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task("t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")
    mgr.add_file(task_id, str(f1), "a.mp3")

    monkeypatch.setattr(mgr, "_save_all_tasks", lambda: (_ for _ in ()).throw(Exception("boom")))

    code, msg = mgr.remove_file(task_id, 0)
    assert code == -1
    assert "boom" in msg


def test_reorder_files_exception(audio_merge_env, monkeypatch, tmp_path):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task("t")
    assert code == 0

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"1")
    mgr.add_file(task_id, str(f1), "a.mp3")

    monkeypatch.setattr(mgr, "_save_all_tasks", lambda: (_ for _ in ()).throw(Exception("boom")))

    code, msg = mgr.reorder_files(task_id, [0])
    assert code == -1
    assert "boom" in msg


def test_start_task_exception(audio_merge_env, monkeypatch):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task("t")
    assert code == 0

    monkeypatch.setattr(mgr, "_validate_task_exists", lambda tid: (_ for _ in ()).throw(Exception("boom")))

    code, msg = mgr.start_task(task_id)
    assert code == -1
    assert "boom" in msg


def test_delete_task_exception(audio_merge_env, monkeypatch):
    am = audio_merge_env
    mgr = am.AudioMergeMgr()

    code, msg, task_id = mgr.create_task("t")
    assert code == 0

    monkeypatch.setattr(mgr, "_validate_task_exists", lambda tid: (_ for _ in ()).throw(Exception("boom")))

    code, msg = mgr.delete_task(task_id)
    assert code == -1
    assert "boom" in msg
