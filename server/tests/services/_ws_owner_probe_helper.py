"""发送线程归属探针的源码。

两个独立进程：
- **服务端**（`/usr/bin/python` 直接跑，**不** import gevent）：自签名 TLS 的
  WebSocket 服务端，握手后不再读，制造 TCP 背压。用独立进程是为了忠实模拟外部
  服务（同进程内无法既 patch 又不 patch）。
- **客户端**（gevent patch 过）：连接 wss 后从**非所属线程**发送。

客户端三种模式：
- `unfixed`：恢复 WebSocketApp 原始的 send（复现故障）
- `fixed-worker`：装好接管后，从**普通工作线程**发送（阻塞路径 —— TTS SDK 的场景）
- `fixed-hub`：装好接管后，从 **hub 线程**发送（不阻塞路径 —— ASR 音频的场景）
"""

TLS_SERVER_SOURCE = r'''
import base64, datetime, hashlib, ipaddress, os, socket, ssl, sys, tempfile, threading, time

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
PORT_FILE = sys.argv[1]


def make_cert():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName(
                [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
            .sign(key, hashes.SHA256()))
    d = tempfile.mkdtemp()
    cert_path, key_path = os.path.join(d, "c.pem"), os.path.join(d, "k.pem")
    with open(cert_path, "wb") as fh:
        fh.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as fh:
        fh.write(key.private_bytes(serialization.Encoding.PEM,
                                   serialization.PrivateFormat.TraditionalOpenSSL,
                                   serialization.NoEncryption()))
    return cert_path, key_path


def main():
    cert_path, key_path = make_cert()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, key_path)
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(4)
    with open(PORT_FILE, "w") as fh:
        fh.write(str(srv.getsockname()[1]))

    def handle(raw):
        try:
            tls = ctx.wrap_socket(raw, server_side=True)
        except Exception:
            return
        try:
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = tls.recv(4096)
                if not chunk:
                    return
                data += chunk
            headers = {}
            for line in data.decode("latin1").split("\r\n")[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
            key = headers.get("sec-websocket-key", "")
            accept = base64.b64encode(
                hashlib.sha1((key + GUID).encode()).digest()).decode()
            tls.sendall(("HTTP/1.1 101 Switching Protocols\r\n"
                         "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                         "Sec-WebSocket-Accept: " + accept + "\r\n\r\n").encode())
            print("HANDSHAKE_OK", flush=True)
            time.sleep(60)      # 不读：制造背压
        except Exception:
            pass
        finally:
            try:
                tls.close()
            except Exception:
                pass

    while True:
        raw, _ = srv.accept()
        threading.Thread(target=handle, args=(raw,), daemon=True).start()


main()
'''


CLIENT_PROBE_SOURCE = r'''
import os
import ssl as ssl_module
import sys
import threading
import time

from gevent import monkey

monkey.patch_all(subprocess=True, thread=False, queue=False)

MODE = sys.argv[2]
PORT_FILE = sys.argv[1]

from websocket import ABNF, WebSocketApp  # noqa: E402

import core.tools.ws_owner_send as wos  # noqa: E402

# 导入 core 时各 ASR/TTS 模块已调用过 install()
print(f"INSTALLED={wos.is_installed()}", flush=True)

if MODE == "unfixed":
    # 显式还原原始 send，复现故障（证明本用例有检测能力）
    for _name, _orig in wos._original_methods.items():
        setattr(WebSocketApp, _name, _orig)

port = None
deadline = time.monotonic() + 15
while port is None and time.monotonic() < deadline:
    try:
        with open(PORT_FILE) as fh:
            port = int(fh.read().strip())
    except Exception:
        time.sleep(0.05)
assert port, "服务端未就绪"

opened = threading.Event()
app = WebSocketApp(f"wss://127.0.0.1:{port}/")
app.on_open = lambda ws: opened.set()
errors = []
app.on_error = lambda ws, err: errors.append(f"{type(err).__name__}: {err}")
SSLOPT = {"cert_reqs": ssl_module.CERT_NONE, "check_hostname": False}
threading.Thread(
    target=lambda: app.run_forever(ping_interval=0, sslopt=SSLOPT), daemon=True
).start()

if not opened.wait(15):
    print("OPENED=False")
    print("DONE")
    sys.exit(0)
print("OPENED=True", flush=True)

payload = b"x" * 65536
state = {"sent": 0, "err": None, "done": False}


def sender():
    try:
        for _ in range(400):
            app.send(payload, opcode=ABNF.OPCODE_BINARY)
            state["sent"] += 1
    except BaseException as e:  # noqa: BLE001
        state["err"] = f"{type(e).__name__}: {str(e)[:70]}"
    finally:
        state["done"] = True


if MODE == "fixed-hub":
    # 从 hub 线程发送（探针主线程即 install() 记录的 hub 线程）
    # → 走「不阻塞、只入队」分支：必须在背压下也能迅速返回
    t0 = time.monotonic()
    sender()
    elapsed = time.monotonic() - t0
    print(f"SEND_CALL_ELAPSED={elapsed:.3f}")
    print(f"QUEUED={wos._state_for(app).queue.qsize()}")
    time.sleep(1.0)     # 给所属线程一点时间消费
    print(f"QUEUE_AFTER={wos._state_for(app).queue.qsize()}")
else:
    t = threading.Thread(target=sender, daemon=True)
    t.start()
    t.join(8)

print(f"SENT={state['sent']}")
print(f"ERR={state['err']}")
print(f"ON_ERROR={errors[0] if errors else None}")
print("DONE")
'''


def write_scripts(tmp_dir):
    """把两段源码写到临时目录，返回路径。"""
    import os

    server = os.path.join(str(tmp_dir), '_owner_send_server.py')
    client = os.path.join(str(tmp_dir), '_owner_send_client.py')
    with open(server, 'w', encoding='utf-8') as fh:
        fh.write(TLS_SERVER_SOURCE)
    with open(client, 'w', encoding='utf-8') as fh:
        fh.write(CLIENT_PROBE_SOURCE)
    return server, client
