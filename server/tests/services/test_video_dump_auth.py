"""文字提取登录态：按站点选文件、扫码状态。不访问外网。"""
import os
import subprocess
import sys
import time
from http.cookiejar import Cookie
from pathlib import Path

import pytest
import requests

from core.services.tools import video_dump_auth as auth
from core.services.tools import video_dump_douyin_browser as auth_browser

_SERVER_ROOT = Path(__file__).resolve().parents[2]


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


def test_douyin_cookie_rows_keep_login_cookie_only(tmp_path, monkeypatch):
    _use_dir(monkeypatch, str(tmp_path))
    assert not auth._save_douyin_cookie_rows([
        {"name": "ttwid", "value": "x", "domain": ".douyin.com", "path": "/", "secure": True, "expires": 0},
        {"name": "sessionid", "value": "sid", "domain": ".evil.example", "path": "/", "secure": True, "expires": 0},
    ])
    assert not (tmp_path / "douyin.txt").exists()
    assert auth._save_douyin_cookie_rows([
        {"name": "sessionid", "value": "sid", "domain": ".douyin.com", "path": "/", "secure": True, "expires": 10},
    ])
    text = (tmp_path / "douyin.txt").read_text(encoding="utf-8")
    assert "\tsessionid\tsid" in text
    assert "evil.example" not in text
    assert auth.site_ready("douyin")


def test_douyin_qr_returns_image_and_drops_foreign_url(tmp_path, monkeypatch):
    _use_dir(monkeypatch, str(tmp_path))

    def spawn(job_dir: str) -> None:
        auth_browser.write_json(os.path.join(job_dir, "qr.json"), {
            "image": "data:image/png;base64,aGVsbG8=",
            "url": "https://evil.example/qr",
        })
        auth_browser.write_state(job_dir, "waiting")

    monkeypatch.setattr(auth, "_spawn_douyin_worker", spawn)
    code, msg, data = auth.start_douyin_qr()
    assert code == 0, msg
    assert data["image"] == "data:image/png;base64,aGVsbG8="
    assert "url" not in data
    assert "token" not in data

    login_id = data["login_id"]
    code, msg, polled = auth.poll_douyin_qr(login_id)
    assert code == 0, msg
    assert polled == {"status": "waiting", "ready": False}

    job_dir = auth._douyin_jobs[login_id].directory
    auth_browser.write_state(job_dir, "scanned")
    assert auth.poll_douyin_qr(login_id)[2]["status"] == "scanned"

    _write_douyin_cookie(tmp_path)
    auth_browser.write_state(job_dir, "saved")
    code, msg, polled = auth.poll_douyin_qr(login_id)
    assert code == 0, msg
    assert polled == {"status": "success", "ready": True}
    assert os.path.exists(os.path.join(job_dir, "stop"))


def test_douyin_qr_reports_browser_error(tmp_path, monkeypatch):
    _use_dir(monkeypatch, str(tmp_path))

    def spawn(job_dir: str) -> None:
        auth_browser.write_state(job_dir, "error", "服务器还没安装 Chromium，暂时无法申请抖音二维码")

    monkeypatch.setattr(auth, "_spawn_douyin_worker", spawn)
    code, msg, data = auth.start_douyin_qr()
    assert code != 0
    assert data is None
    assert "Chromium" in msg


def test_douyin_worker_spawns_under_gevent_patch(tmp_path):
    """gevent 补丁过的进程里只能用 gevent 版 Popen。

    补丁前的 Popen 依赖 subprocess._fork_exec，而 gevent 会把它置成 None；
    get_original 拿回来的正是那个类，一调用就 TypeError，二维码申请不到。
    """
    pytest.importorskip("gevent")
    marker = tmp_path / "worker-ran.txt"
    child = tmp_path / "fake_worker.py"
    child.write_text(
        "import os, sys\n"
        "open(os.path.join(sys.argv[1], 'worker-ran.txt'), 'w').close()\n",
        encoding="utf-8",
    )
    program = "\n".join([
        "import gevent.monkey",
        "gevent.monkey.patch_all(subprocess=True, thread=False, queue=False)",
        "import sys",
        f"sys.path.insert(0, {str(_SERVER_ROOT)!r})",
        "from core.services.tools import video_dump_auth as auth",
        f"auth._WORKER_SCRIPT = {str(child)!r}",
        f"auth._spawn_douyin_worker({str(tmp_path)!r})",
    ])
    subprocess.run([sys.executable, "-c", program], cwd=str(_SERVER_ROOT), check=True, timeout=60)
    for _ in range(100):
        if marker.exists():
            break
        time.sleep(0.1)
    assert marker.exists(), "子进程没起来"


class _FakeChromium:
    """只记调用参数，第一次抛错，模拟自带 Chromium 没下载。"""

    def __init__(self, fail_times: int = 1) -> None:
        self.calls: list[dict] = []
        self._fail_times = fail_times

    def launch(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) <= self._fail_times:
            raise RuntimeError("Executable doesn't exist at /home/leo/.cache/ms-playwright/...")
        return "browser"


class _FakePlaywright:
    def __init__(self, fail_times: int = 1) -> None:
        self.chromium = _FakeChromium(fail_times)


def test_douyin_browser_falls_back_to_local_chrome(tmp_path, monkeypatch):
    """没有 Playwright 自带 Chromium 时，退回机器上装好的 Chrome。"""
    exe = tmp_path / "chrome"
    exe.write_text("", encoding="utf-8")
    monkeypatch.delenv(auth_browser._CHROME_ENV, raising=False)
    monkeypatch.setattr(auth_browser, "_CHROME_CANDIDATES", (str(exe),))
    playwright = _FakePlaywright()
    assert auth_browser.launch_browser(playwright) == "browser"
    assert playwright.chromium.calls == [
        {"headless": True},
        {"headless": True, "executable_path": str(exe)},
    ]


def test_douyin_browser_raises_without_any_chrome(monkeypatch):
    monkeypatch.delenv(auth_browser._CHROME_ENV, raising=False)
    monkeypatch.setattr(auth_browser, "_CHROME_CANDIDATES", ())
    with pytest.raises(RuntimeError):
        auth_browser.launch_browser(_FakePlaywright())


def test_douyin_browser_honours_chrome_env(tmp_path, monkeypatch):
    exe = tmp_path / "custom-chrome"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setenv(auth_browser._CHROME_ENV, str(exe))
    monkeypatch.setattr(auth_browser, "_CHROME_CANDIDATES", ())
    assert auth_browser.chrome_path() == str(exe)
    playwright = _FakePlaywright(fail_times=0)
    assert auth_browser.launch_browser(playwright) == "browser"
    assert playwright.chromium.calls == [{"headless": True, "executable_path": str(exe)}]


def test_douyin_scan_status_words():
    assert auth_browser.scan_status({"status": "new"}) == "waiting"
    assert auth_browser.scan_status({"status": "scanned"}) == "scanned"
    assert auth_browser.scan_status({"status": "confirmed"}) == "success"
    assert auth_browser.scan_status({"status": "expired"}) == "expired"
    assert auth_browser.scan_status({"status": "new", "redirect_url": "https://evil.example/"}) == "waiting"


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
