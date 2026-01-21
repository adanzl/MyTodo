import io
import json
import os
import types

import pytest


class _FakeFile:

    def __init__(self, content=b"x"):
        self._content = content
        self.saved_path = None

    def save(self, path):
        self.saved_path = path
        with open(path, "wb") as f:
            f.write(self._content)


@pytest.fixture
def pdf_env(monkeypatch, tmp_path):
    import core.services.pdf_mgr as pm

    monkeypatch.setattr(pm, "PDF_BASE_DIR", str(tmp_path / "pdf"))
    monkeypatch.setattr(pm, "PDF_UPLOAD_DIR", str(tmp_path / "pdf" / "upload"))
    monkeypatch.setattr(pm, "PDF_UNLOCK_DIR", str(tmp_path / "pdf" / "unlock"))

    monkeypatch.setattr(pm, "ensure_directory", lambda p: os.makedirs(p, exist_ok=True))

    def fake_get_file_info(p):
        if not os.path.exists(p):
            return None
        return {"name": os.path.basename(p), "path": p, "size": os.path.getsize(p)}

    monkeypatch.setattr(pm, "get_file_info", fake_get_file_info)

    return pm


def test_upload_file_rejects_non_pdf(pdf_env, monkeypatch):
    pm = pdf_env
    monkeypatch.setattr(pm, "is_allowed_pdf_file", lambda name: False)

    mgr = pm.PdfMgr()
    code, msg, info = mgr.upload_file(_FakeFile(), "a.txt")
    assert code == -1
    assert info is None


def test_upload_file_success_and_duplicate_rename(pdf_env, monkeypatch):
    pm = pdf_env
    monkeypatch.setattr(pm, "is_allowed_pdf_file", lambda name: True)

    mgr = pm.PdfMgr()

    f1 = _FakeFile(b"1")
    code, msg, info = mgr.upload_file(f1, "a.pdf")
    assert code == 0
    assert info is not None

    f2 = _FakeFile(b"2")
    code, msg, info2 = mgr.upload_file(f2, "a.pdf")
    assert code == 0
    assert info2 is not None
    assert info2["name"] != info["name"]


def test_upload_file_get_file_info_failed_returns_error(pdf_env, monkeypatch):
    pm = pdf_env
    monkeypatch.setattr(pm, "is_allowed_pdf_file", lambda name: True)
    monkeypatch.setattr(pm, "get_file_info", lambda p: None)

    mgr = pm.PdfMgr()
    code, msg, info = mgr.upload_file(_FakeFile(b"x"), "a.pdf")
    assert code == -1
    assert info is None


def test_upload_file_os_fsync_failure_is_ignored(pdf_env, monkeypatch):
    pm = pdf_env
    monkeypatch.setattr(pm, "is_allowed_pdf_file", lambda name: True)

    mgr = pm.PdfMgr()

    monkeypatch.setattr(pm.os, "open", lambda *a, **kw: 10)
    monkeypatch.setattr(pm.os, "fsync", lambda fd: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(pm.os, "close", lambda fd: None)

    code, msg, info = mgr.upload_file(_FakeFile(b"x"), "a.pdf")
    assert code == 0
    assert info is not None


def test_upload_file_exception_returns_error(pdf_env, monkeypatch):
    pm = pdf_env
    monkeypatch.setattr(pm, "is_allowed_pdf_file", lambda name: True)

    mgr = pm.PdfMgr()

    monkeypatch.setattr(pm, "secure_filename", lambda x: (_ for _ in ()).throw(RuntimeError("boom")))

    code, msg, info = mgr.upload_file(_FakeFile(b"x"), "a.pdf")
    assert code == -1
    assert info is None


def test_list_updates_and_removes_missing_files(pdf_env, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    os.makedirs(upload_dir, exist_ok=True)

    p1 = upload_dir / "a.pdf"
    p1.write_bytes(b"a")

    t1 = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(p1),
        uploaded_info=pm.get_file_info(str(p1)),
        create_time=1,
        update_time=1,
    )

    mgr._tasks = {
        "a.pdf":
        t1,
        "missing.pdf":
        pm.PdfTask(
            task_id="missing.pdf",
            filename="missing.pdf",
            status=pm.TASK_STATUS_UPLOADED,
            uploaded_path=str(upload_dir / "missing.pdf"),
            uploaded_info={},
            create_time=1,
            update_time=2,
        ),
    }

    items = mgr.list()
    assert len(items) == 1
    assert items[0]["task_id"] == "a.pdf"


def test_list_exception_returns_empty(pdf_env, monkeypatch):
    pm = pdf_env
    mgr = pm.PdfMgr()

    monkeypatch.setattr(pm, "ensure_directory", lambda p: (_ for _ in ()).throw(RuntimeError("boom")))

    assert mgr.list() == []


def test_update_unlocked_file_info_transitions(pdf_env, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    unlock_dir = tmp_path / "pdf" / "unlock"
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(unlock_dir, exist_ok=True)

    up = upload_dir / "a.pdf"
    up.write_bytes(b"a")

    # unlocked exists but task.unlocked_path empty -> should detect via _get_unlocked_path
    unlocked = unlock_dir / "a_unlocked.pdf"
    unlocked.write_bytes(b"u")

    task = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(up),
        uploaded_info=pm.get_file_info(str(up)),
        unlocked_path=None,
        unlocked_info=None,
        create_time=1,
        update_time=1,
    )

    mgr._update_unlocked_file_info(task)
    assert task.unlocked_path is not None
    assert task.status == pm.TASK_STATUS_SUCCESS

    # if unlocked_path exists but get_file_info fails -> reset
    task2 = pm.PdfTask(
        task_id="b.pdf",
        filename="b.pdf",
        status=pm.TASK_STATUS_SUCCESS,
        uploaded_path=str(up),
        uploaded_info=pm.get_file_info(str(up)),
        unlocked_path=str(unlocked),
        unlocked_info=None,
        create_time=1,
        update_time=1,
    )

    # monkeypatch get_file_info to fail for unlocked
    def fake_get_file_info(p):
        if p == str(unlocked):
            return None
        return {"name": os.path.basename(p), "path": p, "size": os.path.getsize(p)}

    pm.get_file_info = fake_get_file_info

    mgr._update_unlocked_file_info(task2)
    assert task2.unlocked_path is None
    assert task2.status == pm.TASK_STATUS_UPLOADED


def test_get_task_status_not_found(pdf_env):
    pm = pdf_env
    mgr = pm.PdfMgr()

    code, msg, data = mgr.get_task_status("nope.pdf")
    assert code == -1
    assert data is None


def test_get_task_status_exception_returns_error(pdf_env, monkeypatch):
    pm = pdf_env
    mgr = pm.PdfMgr()

    class DummyLock:

        def __enter__(self):
            raise RuntimeError("boom")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(mgr, "_task_lock", DummyLock())

    code, msg, data = mgr.get_task_status("x")
    assert code == -1
    assert data is None


def test_decrypt_task_validation_and_already_success(pdf_env, tmp_path):
    pm = pdf_env
    os.makedirs(tmp_path / "pdf" / "upload", exist_ok=True)

    mgr = pm.PdfMgr()

    code, msg = mgr.decrypt("nope.pdf")
    assert code == -1

    upload_path = tmp_path / "pdf" / "upload" / "a.pdf"
    upload_path.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_SUCCESS,
        uploaded_path=str(upload_path),
        uploaded_info={"name": "a.pdf"},
        unlocked_path=str(tmp_path / "pdf" / "unlock" / "a_unlocked.pdf"),
        unlocked_info={"name": "a_unlocked.pdf"},
        create_time=1,
        update_time=1,
    )

    mgr._tasks = {"a.pdf": t}

    code, msg = mgr.decrypt("a.pdf")
    assert code == 0


def test_decrypt_validations_processing_and_missing_upload(pdf_env, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    up = tmp_path / "pdf" / "upload" / "a.pdf"
    os.makedirs(up.parent, exist_ok=True)
    up.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_PROCESSING,
        uploaded_path=str(up),
        uploaded_info={"name": "a.pdf"},
        create_time=1,
        update_time=1,
    )
    mgr._tasks = {"a.pdf": t}

    code, msg = mgr.decrypt("a.pdf")
    assert code == -1

    t.status = pm.TASK_STATUS_UPLOADED
    t.uploaded_path = str(tmp_path / "pdf" / "upload" / "missing.pdf")
    code, msg = mgr.decrypt("a.pdf")
    assert code == -1


def test_decrypt_submits_thread_and_sets_pending(pdf_env, monkeypatch, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    os.makedirs(upload_dir, exist_ok=True)

    up = upload_dir / "a.pdf"
    up.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(up),
        uploaded_info=pm.get_file_info(str(up)),
        create_time=1,
        update_time=1,
    )
    mgr._tasks = {"a.pdf": t}

    # Make thread synchronous and avoid actual decrypt
    def fake_decrypt_async(*args, **kwargs):
        return

    monkeypatch.setattr(mgr, "_decrypt_file_async", fake_decrypt_async)

    class FakeThread:

        def __init__(self, target, args=(), daemon=True):
            self._target = target
            self._args = args

        def start(self):
            self._target(*self._args)

    monkeypatch.setattr(pm.threading, "Thread", FakeThread)

    code, msg = mgr.decrypt("a.pdf")
    assert code == 0
    assert mgr._tasks["a.pdf"].status == pm.TASK_STATUS_PENDING


def test_decrypt_submission_exception(pdf_env, monkeypatch, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    os.makedirs(upload_dir, exist_ok=True)

    up = upload_dir / "a.pdf"
    up.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(up),
        uploaded_info=pm.get_file_info(str(up)),
        create_time=1,
        update_time=1,
    )
    mgr._tasks = {"a.pdf": t}

    monkeypatch.setattr(pm.threading, "Thread", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))

    code, msg = mgr.decrypt("a.pdf")
    assert code == -1


def test_decrypt_file_async_success_and_failures(pdf_env, monkeypatch, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    unlock_dir = tmp_path / "pdf" / "unlock"
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(unlock_dir, exist_ok=True)

    in_path = upload_dir / "a.pdf"
    out_path = unlock_dir / "a_unlocked.pdf"
    in_path.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(in_path),
        uploaded_info=pm.get_file_info(str(in_path)),
        create_time=1,
        update_time=1,
    )
    mgr._tasks = {"a.pdf": t}

    # success -> create output and return code=0
    def fake_decrypt(input_path, output_path, password):
        with open(output_path, "wb") as f:
            f.write(b"ok")
        return 0, "ok"

    monkeypatch.setattr(mgr, "_decrypt_with_pikepdf", fake_decrypt)

    mgr._decrypt_file_async("a.pdf", str(in_path), str(out_path), None)
    assert mgr._tasks["a.pdf"].status == pm.TASK_STATUS_SUCCESS

    # decrypt returns failure
    t2 = pm.PdfTask(
        task_id="b.pdf",
        filename="b.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(in_path),
        uploaded_info=pm.get_file_info(str(in_path)),
        create_time=1,
        update_time=1,
    )
    mgr._tasks["b.pdf"] = t2

    monkeypatch.setattr(mgr, "_decrypt_with_pikepdf", lambda *a, **kw: (-1, "bad"))
    mgr._decrypt_file_async("b.pdf", str(in_path), str(out_path), None)
    assert mgr._tasks["b.pdf"].status == pm.TASK_STATUS_FAILED


def test_decrypt_file_async_missing_task_is_noop(pdf_env, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    mgr._decrypt_file_async("nope.pdf", str(tmp_path / "a.pdf"), str(tmp_path / "b.pdf"), None)


def test_decrypt_file_async_success_but_unlocked_info_missing(pdf_env, monkeypatch, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    unlock_dir = tmp_path / "pdf" / "unlock"
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(unlock_dir, exist_ok=True)

    in_path = upload_dir / "a.pdf"
    out_path = unlock_dir / "a_unlocked.pdf"
    in_path.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(in_path),
        uploaded_info=pm.get_file_info(str(in_path)),
        create_time=1,
        update_time=1,
    )
    mgr._tasks = {"a.pdf": t}

    monkeypatch.setattr(mgr, "_decrypt_with_pikepdf", lambda *a, **kw: (0, "ok"))
    monkeypatch.setattr(pm, "get_file_info", lambda p: None)

    mgr._decrypt_file_async("a.pdf", str(in_path), str(out_path), None)
    assert mgr._tasks["a.pdf"].status == pm.TASK_STATUS_FAILED


def test_decrypt_file_async_exception_sets_failed(pdf_env, monkeypatch, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    unlock_dir = tmp_path / "pdf" / "unlock"
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(unlock_dir, exist_ok=True)

    in_path = upload_dir / "a.pdf"
    out_path = unlock_dir / "a_unlocked.pdf"
    in_path.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(in_path),
        uploaded_info=pm.get_file_info(str(in_path)),
        create_time=1,
        update_time=1,
    )
    mgr._tasks = {"a.pdf": t}

    monkeypatch.setattr(mgr, "_decrypt_with_pikepdf", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))

    mgr._decrypt_file_async("a.pdf", str(in_path), str(out_path), None)
    assert mgr._tasks["a.pdf"].status == pm.TASK_STATUS_FAILED


def test_load_history_tasks_handles_non_dict_and_invalid_json(monkeypatch, tmp_path):
    import core.services.pdf_mgr as pm

    monkeypatch.setattr(pm, "PDF_BASE_DIR", str(tmp_path / "pdf"))
    task_meta_file = tmp_path / "pdf" / pm.PdfMgr.TASK_META_FILE
    os.makedirs(tmp_path / "pdf", exist_ok=True)

    # invalid json
    task_meta_file.write_text("not json", encoding="utf-8")
    pm.PdfMgr()  # should not raise

    # non-dict json
    task_meta_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    pm.PdfMgr()  # should not raise


def test_load_history_tasks_skips_missing_upload_or_info(monkeypatch, tmp_path):
    import core.services.pdf_mgr as pm

    monkeypatch.setattr(pm, "PDF_BASE_DIR", str(tmp_path / "pdf"))
    os.makedirs(tmp_path / "pdf", exist_ok=True)

    # tasks.json includes missing upload
    task_meta_file = tmp_path / "pdf" / pm.PdfMgr.TASK_META_FILE
    task_meta_file.write_text(json.dumps({"a.pdf": {"uploaded_path": str(tmp_path / "nope.pdf")}}), encoding="utf-8")

    pm.PdfMgr()


def test_delete_task_paths(pdf_env, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    unlock_dir = tmp_path / "pdf" / "unlock"
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(unlock_dir, exist_ok=True)

    up = upload_dir / "a.pdf"
    up.write_bytes(b"a")
    unlocked = unlock_dir / "a_unlocked.pdf"
    unlocked.write_bytes(b"u")

    t = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(up),
        uploaded_info=pm.get_file_info(str(up)),
        unlocked_path=str(unlocked),
        unlocked_info=pm.get_file_info(str(unlocked)),
        create_time=1,
        update_time=1,
    )
    mgr._tasks = {"a.pdf": t}

    code, msg = mgr.delete("a.pdf")
    assert code == 0

    # deleting missing task
    code, msg = mgr.delete("a.pdf")
    assert code == -1


def test_delete_task_processing_not_allowed(pdf_env, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    os.makedirs(upload_dir, exist_ok=True)
    up = upload_dir / "a.pdf"
    up.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_PROCESSING,
        uploaded_path=str(up),
        uploaded_info=pm.get_file_info(str(up)),
        create_time=1,
        update_time=1,
    )
    mgr._tasks = {"a.pdf": t}

    code, msg = mgr.delete("a.pdf")
    assert code == -1


def test_delete_task_no_files_returns_error(pdf_env, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    os.makedirs(upload_dir, exist_ok=True)

    up = upload_dir / "a.pdf"
    up.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(tmp_path / "missing.pdf"),
        uploaded_info={},
        unlocked_path=str(tmp_path / "missing_unlocked.pdf"),
        unlocked_info=None,
        create_time=1,
        update_time=1,
    )

    mgr._tasks = {"a.pdf": t}

    code, msg = mgr.delete("a.pdf")
    assert code == -1


def test_delete_task_remove_raises(pdf_env, monkeypatch, tmp_path):
    pm = pdf_env
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    os.makedirs(upload_dir, exist_ok=True)

    up = upload_dir / "a.pdf"
    up.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        filename="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(up),
        uploaded_info=pm.get_file_info(str(up)),
        create_time=1,
        update_time=1,
    )

    mgr._tasks = {"a.pdf": t}

    monkeypatch.setattr(pm.os, "remove", lambda p: (_ for _ in ()).throw(RuntimeError("boom")))

    code, msg = mgr.delete("a.pdf")
    assert code == -1


def test_decrypt_with_pikepdf_paths(pdf_env, monkeypatch, tmp_path):
    pm = pdf_env

    mgr = pm.PdfMgr()

    class FakePasswordError(Exception):
        pass

    class FakePdf:

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def save(self, output_path):
            with open(output_path, "wb") as f:
                f.write(b"ok")

    def fake_open_ok(input_path, password=None):
        return FakePdf()

    def fake_open_password_error(input_path, password=None):
        raise FakePasswordError("bad")

    fake_pikepdf = types.SimpleNamespace(open=fake_open_ok, PasswordError=FakePasswordError)
    monkeypatch.setattr(pm, "pikepdf", fake_pikepdf)

    in_path = tmp_path / "in.pdf"
    out_path = tmp_path / "out.pdf"
    in_path.write_bytes(b"x")

    code, msg = mgr._decrypt_with_pikepdf(str(in_path), str(out_path), password=None)
    assert code == 0
    assert out_path.exists()

    fake_pikepdf = types.SimpleNamespace(open=fake_open_password_error, PasswordError=FakePasswordError)
    monkeypatch.setattr(pm, "pikepdf", fake_pikepdf)

    code, msg = mgr._decrypt_with_pikepdf(str(in_path), str(out_path), password=None)
    assert code == -1

    code, msg = mgr._decrypt_with_pikepdf(str(in_path), str(out_path), password="wrong")
    assert code == -1


def test_decrypt_with_pikepdf_generic_exception(pdf_env, monkeypatch, tmp_path):
    pm = pdf_env

    mgr = pm.PdfMgr()

    class FakePasswordError(Exception):
        pass

    def fake_open_raises(input_path, password=None):
        raise RuntimeError("boom")

    fake_pikepdf = types.SimpleNamespace(open=fake_open_raises, PasswordError=FakePasswordError)
    monkeypatch.setattr(pm, "pikepdf", fake_pikepdf)

    in_path = tmp_path / "in.pdf"
    out_path = tmp_path / "out.pdf"
    in_path.write_bytes(b"x")

    code, msg = mgr._decrypt_with_pikepdf(str(in_path), str(out_path), password=None)
    assert code == -1
