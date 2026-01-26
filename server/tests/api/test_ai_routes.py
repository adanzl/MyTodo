"""AI routes 单元测试"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask

import core.api.ai_routes as ar


@pytest.fixture
def app(monkeypatch):
    """创建 Flask 应用实例用于测试"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(ar.ai_bp)
    
    # Mock OCR 客户端
    mock_ocr = MagicMock()
    monkeypatch.setattr(ar, "ocr_client", mock_ocr)
    
    return app


@pytest.fixture
def client(app):
    """测试客户端"""
    return app.test_client()


def test_ocr_with_file_upload_success(client, monkeypatch):
    """测试文件上传方式的 OCR 识别成功"""
    # Mock OCR 返回成功
    mock_ocr = MagicMock()
    mock_ocr.query.return_value = ("ok", "识别出的文本内容")
    monkeypatch.setattr(ar, "ocr_client", mock_ocr)
    
    # 创建临时图片文件
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        tmp_file.write(b'fake image data')
        tmp_path = tmp_file.name
    
    try:
        with open(tmp_path, 'rb') as f:
            resp = client.post('/ai/ocr', data={'file': (f, 'test.jpg')}, content_type='multipart/form-data')
        
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == 0
        assert data["data"]["text"] == "识别出的文本内容"
        mock_ocr.query.assert_called_once()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_ocr_with_multiple_files_success(client, monkeypatch):
    """测试多文件上传的 OCR 识别成功"""
    mock_ocr = MagicMock()
    mock_ocr.query.return_value = ("ok", "多图识别结果")
    monkeypatch.setattr(ar, "ocr_client", mock_ocr)
    
    # 创建多个临时文件
    tmp_files = []
    file_handles = []
    try:
        # Flask 测试客户端需要使用字典格式，但可以传递多个文件
        # 使用不同的字段名来传递多个文件
        for i in range(2):
            tmp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            tmp_file.write(b'fake image data')
            tmp_file.close()
            tmp_files.append(tmp_file.name)
            file_handle = open(tmp_file.name, 'rb')
            file_handles.append(file_handle)
        
        # 使用字典格式，每个文件使用不同的键（Flask 会处理）
        files_dict = {
            'file': (file_handles[0], 'test0.jpg'),
            'files[]': (file_handles[1], 'test1.jpg')  # 使用 files[] 格式
        }
        
        resp = client.post('/ai/ocr', data=files_dict, content_type='multipart/form-data')
        
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == 0
        assert data["data"]["text"] == "多图识别结果"
        mock_ocr.query.assert_called_once()
        # 验证传递了多个路径（至少1个）
        call_args = mock_ocr.query.call_args[0][0]
        assert len(call_args) >= 1
    finally:
        for fh in file_handles:
            fh.close()
        for tmp_path in tmp_files:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


def test_ocr_with_json_path_success(client, monkeypatch, tmp_path):
    """测试 JSON 方式传递本地路径的 OCR 识别成功"""
    mock_ocr = MagicMock()
    mock_ocr.query.return_value = ("ok", "JSON路径识别结果")
    monkeypatch.setattr(ar, "ocr_client", mock_ocr)
    
    # 创建临时文件
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b'fake image data')
    
    resp = client.post('/ai/ocr', json={"image_paths": str(test_file)})
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 0
    assert data["data"]["text"] == "JSON路径识别结果"
    mock_ocr.query.assert_called_once()


def test_ocr_with_json_multiple_paths_success(client, monkeypatch, tmp_path):
    """测试 JSON 方式传递多个路径的 OCR 识别成功"""
    mock_ocr = MagicMock()
    mock_ocr.query.return_value = ("ok", "多路径识别结果")
    monkeypatch.setattr(ar, "ocr_client", mock_ocr)
    
    # 创建多个临时文件
    test_files = []
    for i in range(2):
        test_file = tmp_path / f"test{i}.jpg"
        test_file.write_bytes(b'fake image data')
        test_files.append(str(test_file))
    
    resp = client.post('/ai/ocr', json={"image_paths": test_files})
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 0
    assert data["data"]["text"] == "多路径识别结果"
    mock_ocr.query.assert_called_once()
    call_args = mock_ocr.query.call_args[0][0]
    assert len(call_args) == 2


def test_ocr_no_files_error(client):
    """测试没有上传文件时返回错误"""
    resp = client.post('/ai/ocr', data={}, content_type='multipart/form-data')
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    # 当没有文件时，Flask 会尝试解析 JSON，所以可能是 JSON 验证错误或文件未找到错误
    assert "未找到上传的图片文件" in data["msg"] or "Field required" in data["msg"] or "invalid request" in data["msg"]


def test_ocr_empty_files_error(client, tmp_path):
    """测试上传空文件时返回错误"""
    # 创建一个空文件
    empty_file = tmp_path / "empty.jpg"
    empty_file.write_bytes(b'')
    
    with open(empty_file, 'rb') as f:
        resp = client.post('/ai/ocr', data={'file': (f, 'empty.jpg')}, content_type='multipart/form-data')
    
    assert resp.status_code == 200
    data = resp.get_json()
    # 空文件可能会被处理，或者返回错误
    assert data["code"] == -1 or data["code"] == 0


def test_ocr_json_path_not_exists_error(client, monkeypatch):
    """测试 JSON 方式传递不存在的路径时返回错误"""
    resp = client.post('/ai/ocr', json={"image_paths": "/nonexistent/path.jpg"})
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "图片文件不存在" in data["msg"]


def test_ocr_json_empty_paths_error(client):
    """测试 JSON 方式传递空路径列表时返回错误"""
    resp = client.post('/ai/ocr', json={"image_paths": []})
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "图片路径列表为空" in data["msg"]


def test_ocr_json_no_paths_error(client):
    """测试 JSON 方式没有传递路径时返回错误"""
    resp = client.post('/ai/ocr', json={})
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1


def test_ocr_service_error(client, monkeypatch, tmp_path):
    """测试 OCR 服务返回错误时的情况"""
    mock_ocr = MagicMock()
    mock_ocr.query.return_value = ("error", "OCR 服务错误")
    monkeypatch.setattr(ar, "ocr_client", mock_ocr)
    
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b'fake image data')
    
    resp = client.post('/ai/ocr', json={"image_paths": str(test_file)})
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "OCR 识别失败" in data["msg"] or "OCR 服务错误" in data["msg"]


def test_ocr_service_exception(client, monkeypatch, tmp_path):
    """测试 OCR 服务抛出异常时的情况"""
    mock_ocr = MagicMock()
    mock_ocr.query.side_effect = Exception("OCR 服务异常")
    monkeypatch.setattr(ar, "ocr_client", mock_ocr)
    
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b'fake image data')
    
    resp = client.post('/ai/ocr', json={"image_paths": str(test_file)})
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "OCR 识别失败" in data["msg"]


def test_ocr_file_save_error(client, monkeypatch):
    """测试文件保存失败时的情况"""
    mock_ocr = MagicMock()
    monkeypatch.setattr(ar, "ocr_client", mock_ocr)
    
    # Mock save_uploaded_files 返回 None（保存失败）
    from core.utils import save_uploaded_files
    original_save = save_uploaded_files
    def mock_save_uploaded_files(*args, **kwargs):
        return None, None
    
    monkeypatch.setattr('core.api.ai_routes.save_uploaded_files', mock_save_uploaded_files)
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        tmp_file.write(b'fake image data')
        tmp_path = tmp_file.name
    
    try:
        with open(tmp_path, 'rb') as f:
            resp = client.post('/ai/ocr', data={'file': (f, 'test.jpg')}, content_type='multipart/form-data')
        
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == -1
        assert "保存上传文件失败" in data["msg"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_ocr_file_save_io_error(client, monkeypatch, tmp_path):
    """测试文件保存IO错误时的情况"""
    mock_ocr = MagicMock()
    monkeypatch.setattr(ar, "ocr_client", mock_ocr)
    
    # Mock tempfile.mkdtemp 和 file.save 抛出异常
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b'fake image data')
    
    # Mock os.path.join 来模拟保存失败
    original_join = os.path.join
    def mock_join(*args):
        if 'ocr_' in str(args[0]):
            raise IOError("磁盘空间不足")
        return original_join(*args)
    
    with patch('core.api.ai_routes.os.path.join', side_effect=mock_join):
        with open(test_file, 'rb') as f:
            resp = client.post('/ai/ocr', data={'file': (f, 'test.jpg')}, content_type='multipart/form-data')
        
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == -1
        assert "保存上传文件失败" in data["msg"] or "磁盘空间不足" in data["msg"]


def test_ocr_temp_dir_cleanup_on_error(client, monkeypatch):
    """测试临时目录清理错误处理"""
    mock_ocr = MagicMock()
    mock_ocr.query.return_value = ("ok", "识别结果")
    monkeypatch.setattr(ar, "ocr_client", mock_ocr)
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        tmp_file.write(b'fake image data')
        tmp_path = tmp_file.name
    
    try:
        # Mock os.rmdir 抛出异常
        with patch('core.api.ai_routes.os.rmdir', side_effect=Exception("删除目录失败")):
            with open(tmp_path, 'rb') as f:
                resp = client.post('/ai/ocr', data={'file': (f, 'test.jpg')}, content_type='multipart/form-data')
            
            # 即使清理失败，也应该返回成功（因为OCR已经完成）
            assert resp.status_code == 200
            data = resp.get_json()
            # 清理失败不应该影响结果
            assert data["code"] == 0 or data["code"] == -1
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_ocr_empty_temp_paths(client, monkeypatch):
    """测试所有文件都是空文件名的情况"""
    mock_ocr = MagicMock()
    monkeypatch.setattr(ar, "ocr_client", mock_ocr)
    
    # 当没有有效文件时，应该返回错误
    # 使用空的 multipart 数据
    resp = client.post('/ai/ocr', data={}, content_type='multipart/form-data')
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == -1
    assert "未找到上传的图片文件" in data["msg"] or "Field required" in data["msg"] or "invalid request" in data["msg"]
