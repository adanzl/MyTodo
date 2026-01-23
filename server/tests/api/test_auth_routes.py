import pytest
from flask import Flask
from unittest.mock import patch, MagicMock

from core.api.auth_routes import auth_bp
from core.models.user import User


@pytest.fixture
def app(monkeypatch):
    app = Flask(__name__)
    app.config["TESTING"] = True

    # Minimal JWT config for tests
    app.config["JWT_SECRET_KEY"] = "test-secret"
    app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
    app.config["JWT_COOKIE_SECURE"] = False
    app.config["JWT_COOKIE_SAMESITE"] = "Lax"
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False
    # Use the same path as production for consistency
    app.config["JWT_REFRESH_COOKIE_PATH"] = "/api/auth/refresh"
    app.config["JWT_COOKIE_DOMAIN"] = None  # Allow cookies to work in test environment

    from flask_jwt_extended import JWTManager
    import json
    
    jwt = JWTManager(app)
    
    # Configure identity handling for flask-jwt-extended 4.7+
    # The library validates that subject is a string, but we use dict
    # We'll serialize dict to JSON string when creating tokens
    @jwt.user_identity_loader
    def user_identity_lookup(identity):
        # Serialize dict to JSON string for JWT subject claim
        if isinstance(identity, dict):
            return json.dumps(identity, sort_keys=True)
        return str(identity) if identity is not None else None
    
    # Mock utility function to get json from request - patch it before importing the blueprint
    def mock_read_json():
        from flask import request
        return request.get_json(silent=True) or {}
    
    monkeypatch.setattr('core.api.auth_routes.read_json_from_request', mock_read_json)

    # register auth blueprint at /api
    app.register_blueprint(auth_bp, url_prefix="/api")

    return app


@pytest.fixture
def client(app):
    # Use the test client with use_cookies=True to maintain cookies between requests
    with app.test_client(use_cookies=True) as client:
        yield client


def test_login_requires_username_and_password(client):
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 400
    assert resp.get_json()["msg"] == "username and password required"


@patch('core.api.auth_routes.db_obj')
def test_login_user_not_found(mock_db_obj, client):
    mock_db_obj.session.query.return_value.filter.return_value.first.return_value = None
    resp = client.post("/api/auth/login", json={"username": "nope", "password": "pw"})
    assert resp.status_code == 401
    assert resp.get_json()["msg"] == "invalid credentials"


@patch('core.api.auth_routes.db_obj')
def test_login_wrong_password(mock_db_obj, client):
    mock_user = User(id=1, name='test', icon='i', pwd='hashed_password', score=0, admin=0)
    mock_db_obj.session.query.return_value.filter.return_value.first.return_value = mock_user
    resp = client.post("/api/auth/login", json={"username": "test", "password": "wrong_password"})
    assert resp.status_code == 401
    assert resp.get_json()["msg"] == "invalid credentials"


@patch('core.api.auth_routes.db_obj')
def test_login_success_with_plaintext_password(mock_db_obj, client):
    mock_user = User(id=1, name='test', icon='i.png', pwd='password123', score=100, admin=1)
    mock_db_obj.session.query.return_value.filter.return_value.first.return_value = mock_user
    resp = client.post("/api/auth/login", json={"username": "test", "password": "password123"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 0
    assert "access_token" in data
    assert data["user"]["name"] == "test"
    assert "refresh_token_cookie" in resp.headers.get('Set-Cookie')


@patch('core.api.auth_routes.db_obj')
def test_login_success_with_md5_password(mock_db_obj, client):
    # MD5 of "password123" is "482c811da5d5b4bc6d497ffa98491e38"
    mock_user = User(id=1, name='test', icon='i.png', pwd='482c811da5d5b4bc6d497ffa98491e38', score=100, admin=0)
    mock_db_obj.session.query.return_value.filter.return_value.first.return_value = mock_user
    resp = client.post("/api/auth/login", json={"username": "test", "password": "password123"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 0
    assert "access_token" in data


@patch('core.api.auth_routes.db_obj')
def test_login_success_with_null_password(mock_db_obj, client):
    mock_user = User(id=1, name='test', icon='i.png', pwd=None, score=100, admin=0)
    mock_db_obj.session.query.return_value.filter.return_value.first.return_value = mock_user
    resp = client.post("/api/auth/login", json={"username": "test", "password": "any_password"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 0
    assert "access_token" in data


def test_refresh_requires_cookie(client):
    resp = client.post("/api/auth/refresh")
    assert resp.status_code == 401


@patch('core.api.auth_routes.db_obj')
def test_refresh_success(mock_db_obj, client, app):
    mock_user = User(id=1, name='test', icon='i.png', pwd='password123', score=100, admin=0)
    mock_db_obj.session.query.return_value.filter.return_value.first.return_value = mock_user
    login_resp = client.post("/api/auth/login", json={"username": "test", "password": "password123"})
    assert login_resp.status_code == 200
    
    # Verify cookie was set
    cookies = login_resp.headers.getlist('Set-Cookie')
    assert any('refresh_token_cookie' in c for c in cookies)

    # Extract refresh token cookie value
    import re
    refresh_token_value = None
    for cookie in cookies:
        if 'refresh_token_cookie' in cookie:
            match = re.search(r'refresh_token_cookie=([^;]+)', cookie)
            if match:
                refresh_token_value = match.group(1)
                break
    
    assert refresh_token_value is not None, "Refresh token cookie should be set"
    
    # Flask test client should automatically send cookies with use_cookies=True
    refresh_resp = client.post("/api/auth/refresh")
    
    assert refresh_resp.status_code == 200, f"Expected 200, got {refresh_resp.status_code}: {refresh_resp.get_json()}"
    data = refresh_resp.get_json()
    assert data["code"] == 0
    assert "access_token" in data


def test_logout_always_ok(client):
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == 0
    # Check that cookies are being cleared (check for empty value or expires in past)
    cookies = resp.headers.getlist('Set-Cookie')
    cookie_str = ' '.join(cookies).lower()
    # Check that refresh_token_cookie is being cleared (either empty value or expires in past)
    assert 'refresh_token_cookie' in cookie_str
    assert any('refresh_token_cookie=;' in c or 'expires=' in c.lower() for c in cookies)
