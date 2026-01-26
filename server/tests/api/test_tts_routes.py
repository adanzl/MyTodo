import os
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask

import core.api.tts_routes as tr


@pytest.fixture
def app(monkeypatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(tr.tts_bp)

    # Mock tts_mgr methods to avoid filesystem/threads
    monkeypatch.setattr(tr.tts_mgr, "create_task", lambda **kw: (0, "任务创建成功", "t1"))
    monkeypatch.setattr(tr.tts_mgr, "update_task", lambda **kw: (0, "任务更新成功"))
    monkeypatch.setattr(tr.tts_mgr, "start_task", lambda task_id: (0, "TTS 任务已启动"))
    monkeypatch.setattr(tr.tts_mgr, "stop_task", lambda task_id: (0, "已请求停止任务"))
    monkeypatch.setattr(tr.tts_mgr, "delete_task", lambda task_id: (0, "任务删除成功"))
    monkeypatch.setattr(tr.tts_mgr, "get_task", lambda task_id: {"task_id": task_id, "name": "n", "status": "pending"})
    monkeypatch.setattr(tr.tts_mgr, "list_tasks", lambda: [{"task_id": "t1"}])

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_create_tts_task_ok(client):
    resp = client.post('/tts/create', json={"text": "hello"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 0
    assert data["data"]["task_id"] == "t1"


def test_create_tts_task_with_all_params(client):
    """测试创建任务时传递所有参数"""
    resp = client.post('/tts/create', json={
        "text": "hello",
        "name": "test task",
        "role": "test_role",
        "speed": 1.5,
        "vol": 75
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 0


def test_create_tts_task_failure(client, monkeypatch):
    """测试创建任务失败的情况"""
    monkeypatch.setattr(tr.tts_mgr, "create_task", lambda **kw: (-1, "创建失败", None))
    resp = client.post('/tts/create', json={"text": "hello"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "创建失败" in data["msg"]


def test_create_tts_task_invalid_json(client):
    """测试无效的 JSON 请求"""
    resp = client.post('/tts/create', data="invalid json", content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1


def test_update_tts_task_ok(client):
    resp = client.post('/tts/update', json={"task_id": "t1", "text": "x"})
    assert resp.status_code == 200
    assert resp.get_json()["code"] == 0


def test_update_tts_task_with_all_params(client):
    """测试更新任务时传递所有参数"""
    resp = client.post('/tts/update', json={
        "task_id": "t1",
        "name": "new name",
        "text": "new text",
        "role": "new_role",
        "speed": 1.2,
        "vol": 80
    })
    assert resp.status_code == 200
    assert resp.get_json()["code"] == 0


def test_update_tts_task_failure(client, monkeypatch):
    """测试更新任务失败的情况"""
    monkeypatch.setattr(tr.tts_mgr, "update_task", lambda **kw: (-1, "更新失败"))
    resp = client.post('/tts/update', json={"task_id": "t1", "text": "x"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "更新失败" in data["msg"]


def test_update_tts_task_invalid_body(client):
    """测试更新任务时请求体验证失败"""
    # 缺少必填字段 task_id
    resp = client.post('/tts/update', json={"text": "x"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1


def test_start_stop_delete_ok(client):
    resp = client.post('/tts/start', json={"task_id": "t1"})
    assert resp.get_json()["code"] == 0

    resp = client.post('/tts/stop', json={"task_id": "t1"})
    assert resp.get_json()["code"] == 0

    resp = client.post('/tts/delete', json={"task_id": "t1"})
    assert resp.get_json()["code"] == 0


def test_start_task_failure(client, monkeypatch):
    """测试启动任务失败的情况"""
    monkeypatch.setattr(tr.tts_mgr, "start_task", lambda task_id: (-1, "启动失败"))
    resp = client.post('/tts/start', json={"task_id": "t1"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "启动失败" in data["msg"]


def test_start_task_invalid_body(client):
    """测试启动任务时请求体验证失败"""
    # 缺少必填字段 task_id
    resp = client.post('/tts/start', json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1


def test_stop_task_failure(client, monkeypatch):
    """测试停止任务失败的情况"""
    monkeypatch.setattr(tr.tts_mgr, "stop_task", lambda task_id: (-1, "停止失败"))
    resp = client.post('/tts/stop', json={"task_id": "t1"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "停止失败" in data["msg"]


def test_stop_task_invalid_body(client):
    """测试停止任务时请求体验证失败"""
    # 缺少必填字段 task_id
    resp = client.post('/tts/stop', json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1


def test_delete_task_failure(client, monkeypatch):
    """测试删除任务失败的情况"""
    monkeypatch.setattr(tr.tts_mgr, "delete_task", lambda task_id: (-1, "删除失败"))
    resp = client.post('/tts/delete', json={"task_id": "t1"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "删除失败" in data["msg"]


def test_delete_task_invalid_body(client):
    """测试删除任务时请求体验证失败"""
    # 缺少必填字段 task_id
    resp = client.post('/tts/delete', json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1


def test_get_tts_task_requires_task_id(client):
    resp = client.get('/tts/get')
    assert resp.get_json()["code"] == -1


def test_get_tts_task_empty_task_id(client):
    """测试空 task_id 的情况"""
    resp = client.get('/tts/get?task_id=')
    assert resp.get_json()["code"] == -1


def test_get_tts_task_ok(client):
    resp = client.get('/tts/get?task_id=t1')
    assert resp.get_json()["code"] == 0
    assert resp.get_json()["data"]["task_id"] == "t1"


def test_get_tts_task_not_found(client, monkeypatch):
    """测试任务不存在的情况"""
    monkeypatch.setattr(tr.tts_mgr, "get_task", lambda task_id: None)
    resp = client.get('/tts/get?task_id=nonexistent')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "任务不存在" in data["msg"]


def test_list_tts_tasks_ok(client):
    resp = client.get('/tts/list')
    assert resp.get_json()["code"] == 0
    assert isinstance(resp.get_json()["data"], list)


def test_download_tts_file_success(client, monkeypatch, tmp_path):
    """测试下载 TTS 文件成功"""
    import os
    test_file = tmp_path / "output.mp3"
    test_file.write_bytes(b"fake audio data")
    
    monkeypatch.setattr(tr.tts_mgr, "get_task", lambda task_id: {"task_id": task_id, "status": "success"})
    monkeypatch.setattr(tr.tts_mgr, "get_output_file_path", lambda task_id: str(test_file))
    
    resp = client.get('/tts/download?task_id=t1')
    assert resp.status_code == 200
    assert resp.data == b"fake audio data"
    assert 'attachment' in resp.headers.get('Content-Disposition', '')


def test_download_tts_file_no_task_id(client):
    """测试下载时没有提供 task_id"""
    resp = client.get('/tts/download')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "task_id 参数必填" in data["msg"]


def test_download_tts_file_empty_task_id(client):
    """测试下载时 task_id 为空"""
    resp = client.get('/tts/download?task_id=')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "task_id 参数必填" in data["msg"]


def test_download_tts_file_task_not_found(client, monkeypatch):
    """测试下载时任务不存在"""
    monkeypatch.setattr(tr.tts_mgr, "get_task", lambda task_id: None)
    resp = client.get('/tts/download?task_id=nonexistent')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "任务不存在" in data["msg"]


def test_download_tts_file_task_not_success(client, monkeypatch):
    """测试下载时任务未完成"""
    monkeypatch.setattr(tr.tts_mgr, "get_task", lambda task_id: {"task_id": task_id, "status": "processing"})
    resp = client.get('/tts/download?task_id=t1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "任务未完成" in data["msg"]


def test_download_tts_file_not_exists(client, monkeypatch):
    """测试下载时文件不存在"""
    monkeypatch.setattr(tr.tts_mgr, "get_task", lambda task_id: {"task_id": task_id, "status": "success"})
    monkeypatch.setattr(tr.tts_mgr, "get_output_file_path", lambda task_id: None)
    resp = client.get('/tts/download?task_id=t1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "音频文件不存在" in data["msg"]


def test_download_tts_file_exception(client, monkeypatch):
    """测试下载时发生异常"""
    from unittest.mock import MagicMock
    mock_get_task = MagicMock(side_effect=Exception("测试异常"))
    monkeypatch.setattr(tr.tts_mgr, "get_task", mock_get_task)
    resp = client.get('/tts/download?task_id=t1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "下载文件失败" in data["msg"]


def test_tts_ocr_success(client, monkeypatch, tmp_path):
    """测试 TTS OCR 成功"""
    import tempfile
    import os
    
    # Mock tts_mgr 方法
    monkeypatch.setattr(tr.tts_mgr, "get_task", lambda task_id: {"task_id": task_id, "status": "pending"})
    monkeypatch.setattr(tr.tts_mgr, "start_ocr_task", lambda task_id, image_paths, temp_dir: (0, "OCR 任务已启动"))
    
    # 创建临时图片文件
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        tmp_file.write(b'fake image data')
        tmp_path_file = tmp_file.name
    
    try:
        with open(tmp_path_file, 'rb') as f:
            resp = client.post(
                '/tts/ocr',
                data={'task_id': 't1', 'file': (f, 'test.jpg')},
                content_type='multipart/form-data'
            )
        
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == 0
    finally:
        if os.path.exists(tmp_path_file):
            os.remove(tmp_path_file)


def test_tts_ocr_no_files(client):
    """测试 TTS OCR 没有上传文件"""
    resp = client.post('/tts/ocr', data={'task_id': 't1'}, content_type='multipart/form-data')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "请上传图片文件" in data["msg"]


def test_tts_ocr_empty_filenames(client, monkeypatch):
    """测试 TTS OCR 上传的文件名为空"""
    from core.config import TASK_STATUS_PENDING
    from core.services.tts_mgr import TTSTask
    
    def mock_get_task_or_err(task_id):
        task = TTSTask(task_id=task_id, name="test", status=TASK_STATUS_PENDING, text="test")
        return task, None
    monkeypatch.setattr(tr.tts_mgr, "_get_task_or_err", mock_get_task_or_err)
    
    # 创建一个空文件名的文件对象
    from werkzeug.datastructures import FileStorage
    empty_file = FileStorage(filename='', stream=None)
    
    resp = client.post('/tts/ocr', data={'task_id': 't1', 'file': empty_file}, content_type='multipart/form-data')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "未找到上传的图片文件" in data["msg"]


def test_tts_ocr_save_files_failure(client, monkeypatch):
    """测试 TTS OCR 保存文件失败"""
    from core.config import TASK_STATUS_PENDING
    from core.services.tts_mgr import TTSTask
    
    def mock_get_task_or_err(task_id):
        task = TTSTask(task_id=task_id, name="test", status=TASK_STATUS_PENDING, text="test")
        return task, None
    monkeypatch.setattr(tr.tts_mgr, "_get_task_or_err", mock_get_task_or_err)
    
    # Mock save_uploaded_files 返回 None（保存失败）
    monkeypatch.setattr('core.api.tts_routes.save_uploaded_files', lambda *args, **kwargs: (None, None))
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        tmp_file.write(b'fake image data')
        tmp_path_file = tmp_file.name
    
    try:
        with open(tmp_path_file, 'rb') as f:
            resp = client.post(
                '/tts/ocr',
                data={'task_id': 't1', 'file': (f, 'test.jpg')},
                content_type='multipart/form-data'
            )
        
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == -1
        assert "保存上传文件失败" in data["msg"]
    finally:
        if os.path.exists(tmp_path_file):
            os.remove(tmp_path_file)


def test_tts_ocr_exception(client, monkeypatch):
    """测试 TTS OCR 发生异常"""
    # Mock parse_with_model 抛出异常
    def mock_parse_with_model(*args, **kwargs):
        raise Exception("测试异常")
    
    monkeypatch.setattr('core.api.tts_routes.parse_with_model', mock_parse_with_model)
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        tmp_file.write(b'fake image data')
        tmp_path_file = tmp_file.name
    
    try:
        with open(tmp_path_file, 'rb') as f:
            resp = client.post(
                '/tts/ocr',
                data={'task_id': 't1', 'file': (f, 'test.jpg')},
                content_type='multipart/form-data'
            )
        
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == -1
        assert "OCR 识别失败" in data["msg"]
    finally:
        if os.path.exists(tmp_path_file):
            os.remove(tmp_path_file)


def test_tts_ocr_no_task_id(client):
    """测试 TTS OCR 没有提供 task_id"""
    resp = client.post('/tts/ocr', content_type='multipart/form-data')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1


def test_tts_ocr_task_not_found(client, monkeypatch):
    """测试 TTS OCR 任务不存在"""
    # Mock _get_task_or_err 返回错误（start_ocr_task 内部使用这个方法）
    def mock_get_task_or_err(task_id):
        return None, "任务不存在"
    monkeypatch.setattr(tr.tts_mgr, "_get_task_or_err", mock_get_task_or_err)
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        tmp_file.write(b'fake image data')
        tmp_path_file = tmp_file.name
    
    try:
        with open(tmp_path_file, 'rb') as f:
            resp = client.post(
                '/tts/ocr',
                data={'task_id': 'nonexistent', 'file': (f, 'test.jpg')},
                content_type='multipart/form-data'
            )
        
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == -1
        assert "任务不存在" in data["msg"]
    finally:
        if os.path.exists(tmp_path_file):
            os.remove(tmp_path_file)


def test_tts_ocr_task_processing(client, monkeypatch):
    """测试 TTS OCR 任务正在处理中"""
    from core.config import TASK_STATUS_PROCESSING
    from core.services.tts_mgr import TTSTask
    
    # Mock _get_task_or_err 返回一个 processing 状态的任务
    def mock_get_task_or_err(task_id):
        task = TTSTask(task_id=task_id, name="test", status=TASK_STATUS_PROCESSING, text="test")
        return task, None
    monkeypatch.setattr(tr.tts_mgr, "_get_task_or_err", mock_get_task_or_err)
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        tmp_file.write(b'fake image data')
        tmp_path_file = tmp_file.name
    
    try:
        with open(tmp_path_file, 'rb') as f:
            resp = client.post(
                '/tts/ocr',
                data={'task_id': 't1', 'file': (f, 'test.jpg')},
                content_type='multipart/form-data'
            )
        
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == -1
        assert "任务正在处理中" in data["msg"]
    finally:
        if os.path.exists(tmp_path_file):
            os.remove(tmp_path_file)


def test_tts_ocr_start_failure(client, monkeypatch, tmp_path):
    """测试 TTS OCR 启动失败"""
    import tempfile
    
    monkeypatch.setattr(tr.tts_mgr, "get_task", lambda task_id: {"task_id": task_id, "status": "pending"})
    monkeypatch.setattr(tr.tts_mgr, "start_ocr_task", lambda task_id, image_paths, temp_dir: (-1, "启动失败"))
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        tmp_file.write(b'fake image data')
        tmp_path_file = tmp_file.name
    
    try:
        with open(tmp_path_file, 'rb') as f:
            resp = client.post(
                '/tts/ocr',
                data={'task_id': 't1', 'file': (f, 'test.jpg')},
                content_type='multipart/form-data'
            )
        
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == -1
        assert "启动失败" in data["msg"]
    finally:
        if os.path.exists(tmp_path_file):
            os.remove(tmp_path_file)
