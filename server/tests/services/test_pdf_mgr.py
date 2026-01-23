import io
import json
import os
import types

import pytest
from unittest.mock import patch
import core.services.pdf_mgr as pm
from core.config import TASK_STATUS_SUCCESS, TASK_STATUS_FAILED, TASK_STATUS_UPLOADED, TASK_STATUS_PROCESSING


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


def test_create_task_rejects_non_pdf(pdf_env, monkeypatch):
    monkeypatch.setattr(pm, "is_allowed_pdf_file", lambda name: False)

    mgr = pm.PdfMgr()
    code, msg, info = mgr.create_task(_FakeFile(), "a.txt")
    assert code == -1
    assert info is None


def test_create_task_success_and_duplicate_rename(pdf_env, monkeypatch):
    monkeypatch.setattr(pm, "is_allowed_pdf_file", lambda name: True)

    mgr = pm.PdfMgr()

    f1 = _FakeFile(b"1")
    code, msg, task_id1 = mgr.create_task(f1, "a.pdf")
    assert code == 0
    assert task_id1 is not None

    f2 = _FakeFile(b"2")
    code, msg, task_id2 = mgr.create_task(f2, "a.pdf")
    assert code == 0
    assert task_id2 is not None
    assert task_id2 != task_id1


def test_create_task_get_file_info_failed_returns_error(pdf_env, monkeypatch):
    monkeypatch.setattr(pm, "is_allowed_pdf_file", lambda name: True)
    monkeypatch.setattr(pm, "get_file_info", lambda p: None)

    mgr = pm.PdfMgr()
    code, msg, info = mgr.create_task(_FakeFile(b"x"), "a.pdf")
    assert code == -1
    assert info is None


def test_create_task_exception_returns_error(pdf_env, monkeypatch):
    monkeypatch.setattr(pm, "is_allowed_pdf_file", lambda name: True)

    mgr = pm.PdfMgr()

    monkeypatch.setattr(pm, "secure_filename", lambda x: (_ for _ in ()).throw(RuntimeError("boom")))

    code, msg, info = mgr.create_task(_FakeFile(b"x"), "a.pdf")
    assert code == -1
    assert info is None


def test_list_tasks_exception_returns_empty(pdf_env, monkeypatch):
    mgr = pm.PdfMgr()

    monkeypatch.setattr(mgr, "_save_all_tasks", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    assert mgr.list_tasks() == []


def test_get_task_not_found(pdf_env):
    mgr = pm.PdfMgr()

    task = mgr.get_task("nope.pdf")
    assert task is None


def test_start_task_validations(pdf_env, tmp_path):
    os.makedirs(tmp_path / "pdf" / "upload", exist_ok=True)

    mgr = pm.PdfMgr()

    code, msg = mgr.start_task("nope.pdf")
    assert code == -1

    upload_path = tmp_path / "pdf" / "upload" / "a.pdf"
    upload_path.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        name="a.pdf",
        status=pm.TASK_STATUS_SUCCESS,
        uploaded_path=str(upload_path),
        uploaded_info={"name": "a.pdf"},
        unlocked_path=str(tmp_path / "pdf" / "unlock" / "a_unlocked.pdf"),
        unlocked_info={"name": "a_unlocked.pdf"},
        create_time=1,
        update_time=1,
    )

    mgr._tasks = {"a.pdf": t}

    code, msg = mgr.start_task("a.pdf")
    assert code == 0


def test_delete_task_no_files_is_ok(pdf_env, tmp_path):
    mgr = pm.PdfMgr()

    t = pm.PdfTask(
        task_id="a.pdf",
        name="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(tmp_path / "missing.pdf"),
        uploaded_info={},
        unlocked_path=str(tmp_path / "missing_unlocked.pdf"),
        unlocked_info=None,
        create_time=1,
        update_time=1,
    )

    mgr._tasks = {"a.pdf": t}

    code, msg = mgr.delete_task("a.pdf")
    assert code == 0


def test_delete_task_remove_raises_is_ok(pdf_env, monkeypatch, tmp_path):
    mgr = pm.PdfMgr()

    upload_dir = tmp_path / "pdf" / "upload"
    os.makedirs(upload_dir, exist_ok=True)

    up = upload_dir / "a.pdf"
    up.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        name="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(up),
        uploaded_info=pm.get_file_info(str(up)),
        create_time=1,
        update_time=1,
    )

    mgr._tasks = {"a.pdf": t}

    monkeypatch.setattr(pm.os, "remove", lambda p: (_ for _ in ()).throw(RuntimeError("boom")))

    code, msg = mgr.delete_task("a.pdf")
    assert code == 0


def test_start_task_processing_and_missing_file(pdf_env, tmp_path):
    mgr = pm.PdfMgr()

    up = tmp_path / "pdf" / "upload" / "a.pdf"
    os.makedirs(up.parent, exist_ok=True)
    up.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        name="a.pdf",
        status=pm.TASK_STATUS_PROCESSING,
        uploaded_path=str(up),
        uploaded_info={"name": "a.pdf"},
        create_time=1,
        update_time=1,
    )
    mgr._tasks = {"a.pdf": t}

    code, msg = mgr.start_task("a.pdf")
    assert code == -1

    t.status = pm.TASK_STATUS_UPLOADED
    t.uploaded_path = str(tmp_path / "pdf" / "upload" / "missing.pdf")
    code, msg = mgr.start_task("a.pdf")
    assert code == -1


def test_decrypt_with_pikepdf_paths(pdf_env, monkeypatch, tmp_path):
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

    def fake_open_ok(input_path, **kwargs):
        return FakePdf()

    def fake_open_password_error(input_path, **kwargs):
        raise FakePasswordError("bad")

    fake_pikepdf = types.SimpleNamespace(open=fake_open_ok, PasswordError=FakePasswordError)
    monkeypatch.setattr(pm, "pikepdf", fake_pikepdf)

    in_path = tmp_path / "in.pdf"
    out_path = tmp_path / "out.pdf"
    in_path.write_bytes(b"x")

    code, msg = mgr._decrypt_with_pikepdf(str(in_path), str(out_path), password=None)
    assert code == 0
    assert out_path.exists()

    fake_pikepdf.open = fake_open_password_error
    code, msg = mgr._decrypt_with_pikepdf(str(in_path), str(out_path), password="wrong")
    assert code == -1


def test_decrypt_with_pikepdf_other_exception(pdf_env, monkeypatch, tmp_path):
    mgr = pm.PdfMgr()

    class FakePasswordError(Exception):
        pass

    def fake_open_raises(*args, **kwargs):
        raise RuntimeError('boom')

    fake_pikepdf = types.SimpleNamespace(open=fake_open_raises, PasswordError=FakePasswordError)
    monkeypatch.setattr(pm, "pikepdf", fake_pikepdf)

    in_path = tmp_path / "in.pdf"
    out_path = tmp_path / "out.pdf"
    in_path.write_bytes(b"x")

    code, msg = mgr._decrypt_with_pikepdf(str(in_path), str(out_path), password=None)
    assert code == -1
    assert 'PDF 解密失败' in msg


def test_update_unlocked_file_info_exists_sets_success(pdf_env, tmp_path):
    mgr = pm.PdfMgr()

    os.makedirs(tmp_path / 'pdf' / 'unlock', exist_ok=True)
    unlocked_path = tmp_path / 'pdf' / 'unlock' / 'a_unlocked.pdf'
    unlocked_path.write_bytes(b'a')

    t = pm.PdfTask(
        task_id='a.pdf',
        name='a.pdf',
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(tmp_path / 'pdf' / 'upload' / 'a.pdf'),
        uploaded_info={'name': 'a.pdf'},
        create_time=1,
        update_time=1,
    )

    mgr._update_unlocked_file_info(t)

    assert t.unlocked_path == str(unlocked_path)
    assert t.unlocked_info is not None
    assert t.status == TASK_STATUS_SUCCESS


def test_update_unlocked_file_info_exists_but_get_info_none_reverts_status(pdf_env, monkeypatch, tmp_path):
    mgr = pm.PdfMgr()

    os.makedirs(tmp_path / 'pdf' / 'unlock', exist_ok=True)
    unlocked_path = tmp_path / 'pdf' / 'unlock' / 'a_unlocked.pdf'
    unlocked_path.write_bytes(b'a')

    monkeypatch.setattr(pm, 'get_file_info', lambda p: None)

    t = pm.PdfTask(
        task_id='a.pdf',
        name='a.pdf',
        status=pm.TASK_STATUS_SUCCESS,
        uploaded_path=str(tmp_path / 'pdf' / 'upload' / 'a.pdf'),
        uploaded_info={'name': 'a.pdf'},
        unlocked_path=str(unlocked_path),
        unlocked_info={'name': 'a_unlocked.pdf'},
        create_time=1,
        update_time=1,
    )

    mgr._update_unlocked_file_info(t)
    assert t.unlocked_path is None
    assert t.unlocked_info is None
    assert t.status == TASK_STATUS_UPLOADED


def test_update_unlocked_file_info_missing_reverts_success_to_uploaded(pdf_env, tmp_path):
    mgr = pm.PdfMgr()

    t = pm.PdfTask(
        task_id='a.pdf',
        name='a.pdf',
        status=pm.TASK_STATUS_SUCCESS,
        uploaded_path=str(tmp_path / 'pdf' / 'upload' / 'a.pdf'),
        uploaded_info={'name': 'a.pdf'},
        unlocked_path=str(tmp_path / 'pdf' / 'unlock' / 'a_unlocked.pdf'),
        unlocked_info={'name': 'a_unlocked.pdf'},
        create_time=1,
        update_time=1,
    )

    mgr._update_unlocked_file_info(t)
    assert t.unlocked_path is None
    assert t.unlocked_info is None
    assert t.status == TASK_STATUS_UPLOADED


def test_update_unlocked_file_info_processing_does_not_change_status(pdf_env, tmp_path):
    mgr = pm.PdfMgr()

    os.makedirs(tmp_path / 'pdf' / 'unlock', exist_ok=True)
    unlocked_path = tmp_path / 'pdf' / 'unlock' / 'a_unlocked.pdf'
    unlocked_path.write_bytes(b'a')

    t = pm.PdfTask(
        task_id='a.pdf',
        name='a.pdf',
        status=TASK_STATUS_PROCESSING,
        uploaded_path=str(tmp_path / 'pdf' / 'upload' / 'a.pdf'),
        uploaded_info={'name': 'a.pdf'},
        create_time=1,
        update_time=1,
    )

    mgr._update_unlocked_file_info(t)
    assert t.status == TASK_STATUS_PROCESSING


def test_load_history_tasks_removes_task_without_upload_path(monkeypatch, tmp_path):
    monkeypatch.setattr(pm, "PDF_BASE_DIR", str(tmp_path / "pdf"))
    os.makedirs(tmp_path / 'pdf', exist_ok=True)

    meta = {
        'a.pdf': {
            'task_id': 'a.pdf',
            'name': 'a.pdf',
            'status': TASK_STATUS_UPLOADED,
            'uploaded_path': '',
            'uploaded_info': {},
            'unlocked_path': None,
            'unlocked_info': None,
            'error_message': None,
            'create_time': 1,
            'update_time': 1,
        }
    }
    (tmp_path / 'pdf' / 'tasks.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')

    mgr = pm.PdfMgr()
    assert mgr.get_task('a.pdf') is None


def test_load_history_tasks_removes_task_when_get_file_info_none(monkeypatch, tmp_path):
    monkeypatch.setattr(pm, "PDF_BASE_DIR", str(tmp_path / "pdf"))
    monkeypatch.setattr(pm, "PDF_UPLOAD_DIR", str(tmp_path / "pdf" / "upload"))
    monkeypatch.setattr(pm, "PDF_UNLOCK_DIR", str(tmp_path / "pdf" / "unlock"))
    os.makedirs(tmp_path / 'pdf', exist_ok=True)
    os.makedirs(tmp_path / 'pdf' / 'upload', exist_ok=True)

    up = tmp_path / 'pdf' / 'upload' / 'a.pdf'
    up.write_bytes(b'a')

    def fake_get_file_info(p):
        return None

    monkeypatch.setattr(pm, 'get_file_info', fake_get_file_info)

    meta = {
        'a.pdf': {
            'task_id': 'a.pdf',
            'name': 'a.pdf',
            'status': TASK_STATUS_UPLOADED,
            'uploaded_path': str(up),
            'uploaded_info': {
                'name': 'a.pdf'
            },
            'unlocked_path': None,
            'unlocked_info': None,
            'error_message': None,
            'create_time': 1,
            'update_time': 1,
        }
    }
    (tmp_path / 'pdf' / 'tasks.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')

    mgr = pm.PdfMgr()
    assert mgr.get_task('a.pdf') is None


def test_load_history_tasks_handles_invalid_json(monkeypatch, tmp_path):
    monkeypatch.setattr(pm, "PDF_BASE_DIR", str(tmp_path / "pdf"))
    task_meta_file = tmp_path / "pdf" / pm.PdfMgr.TASK_META_FILE
    os.makedirs(tmp_path / "pdf", exist_ok=True)

    # invalid json
    task_meta_file.write_text("not json", encoding="utf-8")
    pm.PdfMgr()  # should not raise


@pytest.mark.parametrize("decrypt_return, expected_status", [
    ((0, "ok"), TASK_STATUS_SUCCESS),
    ((-1, "bad"), TASK_STATUS_FAILED),
])
@patch('threading.Thread')
def test_start_task_runner(mock_thread, decrypt_return, expected_status, pdf_env, monkeypatch, tmp_path):

    def run_target(*args, **kwargs):
        thread_args = mock_thread.call_args.kwargs
        target_func = thread_args['target']
        target_func()

    mock_thread.return_value.start.side_effect = run_target

    mgr = pm.PdfMgr()

    up = tmp_path / "pdf" / "upload" / "a.pdf"
    os.makedirs(up.parent, exist_ok=True)
    up.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        name="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(up),
        uploaded_info=pm.get_file_info(str(up)),
        create_time=1,
        update_time=1,
    )
    mgr._tasks = {"a.pdf": t}

    def mock_decrypt(*args, **kwargs):
        if decrypt_return[0] == 0:
            unlocked_path = mgr._get_unlocked_path("a.pdf")
            os.makedirs(os.path.dirname(unlocked_path), exist_ok=True)
            with open(unlocked_path, "w") as f:
                f.write("unlocked")
        return decrypt_return

    monkeypatch.setattr(mgr, "_decrypt_with_pikepdf", mock_decrypt)

    mgr.start_task("a.pdf")

    task = mgr.get_task("a.pdf")
    assert task['status'] == expected_status


@patch('threading.Thread')
def test_start_task_runner_exception(mock_thread, pdf_env, monkeypatch, tmp_path):

    def run_target(*args, **kwargs):
        thread_args = mock_thread.call_args.kwargs
        target_func = thread_args['target']
        target_func()

    mock_thread.return_value.start.side_effect = run_target

    mgr = pm.PdfMgr()

    up = tmp_path / "pdf" / "upload" / "a.pdf"
    os.makedirs(up.parent, exist_ok=True)
    up.write_bytes(b"a")

    t = pm.PdfTask(
        task_id="a.pdf",
        name="a.pdf",
        status=pm.TASK_STATUS_UPLOADED,
        uploaded_path=str(up),
        uploaded_info=pm.get_file_info(str(up)),
        create_time=1,
        update_time=1,
    )
    mgr._tasks = {"a.pdf": t}

    monkeypatch.setattr(mgr, "_decrypt_with_pikepdf", lambda *a, **kw: (_ for _ in ()).throw(Exception("boom")))

    mgr.start_task("a.pdf")

    task = mgr.get_task("a.pdf")
    assert task['status'] == TASK_STATUS_FAILED
    assert "boom" in task['error_message']
