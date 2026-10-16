"""文字提取登录态：按站点选文件、扫码状态。不访问外网。"""
from http.cookiejar import Cookie

import requests

from core.services.tools import video_dump_auth as auth


def _use_dir(monkeypatch, directory: str) -> None:
    monkeypatch.setattr(auth, "_cookie_dir", lambda: directory)
    monkeypatch.setattr(auth.config, "VIDEO_DUMP_COOKIES_FILE", "")


def _write_douyin_cookie(directory):
    (directory / "douyin.txt").write_text(
        "# Netscape HTTP Cookie File\n\n.douyin.com\tTRUE\t/\tTRUE\t0\tsessionid\tabc\n",
        encoding="utf-8",
    )


def test_site_cookie_beats_env_file(tmp_path, monkeypatch):
    _use_dir(monkeypatch, str(tmp_path))
    env_file = tmp_path / "env.txt"
    env_file.write_text("env", encoding="utf-8")
    monkeypatch.setattr(auth.config, "VIDEO_DUMP_COOKIES_FILE", str(env_file))
    assert auth.cookies_file_for_url("https://www.bilibili.com/video/BV1") == str(env_file)
    _write_douyin_cookie(tmp_path)
    assert auth.site_ready("douyin")
    assert auth.cookies_file_for_url("https://www.douyin.com/video/1").endswith("douyin.txt")
    assert auth.cookies_file_for_url("https://www.bilibili.com/video/BV1") == str(env_file)


def test_logout_removes_saved_cookie(tmp_path, monkeypatch):
    _use_dir(monkeypatch, str(tmp_path))
    _write_douyin_cookie(tmp_path)
    assert auth.site_ready("douyin")
    assert auth.logout("douyin")[0] == 0
    assert not auth.site_ready("douyin")
    assert auth.logout("unknown")[0] != 0


class _FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self):
        self.headers: dict = {}
        self.cookies = requests.cookies.RequestsCookieJar()
        self.calls: list[dict] = []
        self._payloads: list[dict] = []

    def get(self, url, params=None, timeout=None, allow_redirects=None):
        self.calls.append({
            "url": url,
            "params": params,
            "timeout": timeout,
            "allow_redirects": allow_redirects,
        })
        payload = self._payloads.pop(0)
        return _FakeResponse(payload)


def _cookie(name: str, value: str, domain: str = ".bilibili.com") -> Cookie:
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=True,
        path="/",
        path_specified=True,
        secure=True,
        expires=1893456000,
        discard=False,
        comment=None,
        comment_url=None,
        rest={},
    )


def test_bilibili_qr_success_writes_sessdata_and_uses_timeout(tmp_path, monkeypatch):
    _use_dir(monkeypatch, str(tmp_path))
    session = _FakeSession()
    session._payloads = [
        {"code": 0, "data": {"url": "https://passport.bilibili.com/qr", "qrcode_key": "key-1"}},
        {"code": 0, "data": {"code": 0, "message": "ok"}},
    ]
    session.cookies.set_cookie(_cookie("SESSDATA", "sess"))
    session.cookies.set_cookie(_cookie("bili_jct", "jct"))
    monkeypatch.setattr(auth.requests, "Session", lambda: session)

    code, msg, data = auth.start_bilibili_qr()
    assert code == 0, msg
    assert data and data["url"].startswith("https://")
    assert session.calls[0]["timeout"] == (5, 10)

    code, msg, polled = auth.poll_bilibili_qr(data["login_id"])
    assert code == 0, msg
    assert polled == {"status": "success", "ready": True}
    assert session.calls[1]["timeout"] == (5, 10)
    assert session.calls[1]["params"] == {"qrcode_key": "key-1"}
    text = (tmp_path / "bilibili.txt").read_text(encoding="utf-8")
    assert "\tSESSDATA\tsess" in text
    assert auth.site_ready("bilibili")
    assert auth.cookies_file_for_url("https://www.bilibili.com/video/BV1").endswith("bilibili.txt")


class _DouyinSession:
    def __init__(self, qr_payload, poll_payload):
        self.headers: dict = {}
        self.cookies = requests.cookies.RequestsCookieJar()
        self.calls: list[dict] = []
        self.qr_payload = qr_payload
        self.poll_payload = poll_payload

    def get(self, url, params=None, timeout=None, allow_redirects=None):
        self.calls.append({
            "url": url,
            "params": params,
            "timeout": timeout,
            "allow_redirects": allow_redirects,
        })
        if "get_qrcode" in url:
            return _FakeResponse(self.qr_payload)
        if "check_qrconnect" in url:
            return _FakeResponse(self.poll_payload)
        return _FakeResponse({}, status_code=302, headers={"Location": "https://evil.example/nope"})


def test_douyin_qr_saves_session_and_ignores_offsite_redirect(tmp_path, monkeypatch):
    _use_dir(monkeypatch, str(tmp_path))
    session = _DouyinSession(
        {"data": {"token": "tok", "qrcode": "aGVsbG8=", "qrcode_index_url": "https://evil.example/qr"}},
        {"data": {"status": "3", "redirect_url": "https://www.douyin.com/passport/sso/login/?ticket=1"}},
    )
    session.cookies.set_cookie(_cookie("sessionid", "sid", domain=".douyin.com"))
    monkeypatch.setattr(auth.requests, "Session", lambda: session)

    code, msg, data = auth.start_douyin_qr()
    assert code == 0, msg
    assert data["image"] == "data:image/png;base64,aGVsbG8="
    assert "url" not in data
    assert "token" not in data
    assert session.calls[0]["timeout"] == (5, 10)

    code, msg, polled = auth.poll_douyin_qr(data["login_id"])
    assert code == 0, msg
    assert polled == {"status": "success", "ready": True}
    followed = [item["url"] for item in session.calls]
    assert "https://www.douyin.com/passport/sso/login/?ticket=1" in followed
    assert all("evil.example" not in item for item in followed)
    assert all(item["allow_redirects"] is False for item in session.calls if "passport" in item["url"])
    text = (tmp_path / "douyin.txt").read_text(encoding="utf-8")
    assert "\tsessionid\tsid" in text
    assert auth.cookies_file_for_url("https://www.douyin.com/video/1").endswith("douyin.txt")


def test_douyin_qr_does_not_follow_foreign_redirect(monkeypatch):
    session = _DouyinSession(
        {"data": {"token": "tok", "qrcode_index_url": "https://aweme.snssdk.com/qr"}},
        {"data": {"status": "3", "redirect_url": "http://evil.example/steal"}},
    )
    monkeypatch.setattr(auth.requests, "Session", lambda: session)
    _code, _msg, data = auth.start_douyin_qr()
    assert data and data["url"].startswith("https://aweme.snssdk.com/")
    code, msg, polled = auth.poll_douyin_qr(data["login_id"])
    assert code != 0
    assert polled is None
    assert "登录态" in msg
    assert all("evil.example" not in item["url"] for item in session.calls)


def test_bilibili_qr_waiting_then_missing_login_expires(monkeypatch):
    session = _FakeSession()
    session._payloads = [
        {"code": 0, "data": {"url": "https://passport.bilibili.com/qr", "qrcode_key": "key-2"}},
        {"code": 0, "data": {"code": 86101}},
    ]
    monkeypatch.setattr(auth.requests, "Session", lambda: session)
    _code, _msg, data = auth.start_bilibili_qr()
    assert data
    code, _msg, polled = auth.poll_bilibili_qr(data["login_id"])
    assert code == 0
    assert polled["status"] == "waiting"
    assert auth.poll_bilibili_qr("missing")[2]["status"] == "expired"
