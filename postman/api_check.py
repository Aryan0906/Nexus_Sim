"""NexusSim full-stack API verification (2026-10-20).

Checks every endpoint on the gateway (:8000), each sidecar directly
(:9003-:9006), the engine WS (:9001) and the dashboard (:3000).
Uses requests for HTTP and a raw-socket WS client for the engine.
"""
import json
import socket
import ssl
import struct
import base64
import os
import time

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Trust the local self-signed cert for every HTTPS request.
_orig_request = requests.Session.request
def _patched_request(self, method, url, **kwargs):
    kwargs.setdefault("verify", False)
    return _orig_request(self, method, url, **kwargs)
requests.Session.request = _patched_request

RESULTS = []


def check(name, fn):
    # Retry transient connection drops (HTTPS handshake / vite dev server
    # can reset a connection under rapid sequential load).
    last_err = None
    for attempt in range(3):
        try:
            detail = fn()
            RESULTS.append((name, True, detail))
            print(f"PASS  {name}: {detail}")
            return
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(1.0)
    RESULTS.append((name, False, str(last_err)))
    print(f"FAIL  {name}: {last_err}")


# ---------------------------------------------------------------- raw WS client
def ws_connect(url, timeout=8):
    # url like wss://host:port/path
    rest = url.split("://", 1)[1]
    hostport, _, path = rest.partition("/")
    host, _, port = hostport.partition(":")
    path = "/" + path
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    raw = socket.create_connection((host, int(port)), timeout=timeout)
    raw.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s = ctx.wrap_socket(raw, server_hostname=host)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (f"GET {path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
           f"Sec-WebSocket-Version: 13\r\n\r\n")
    s.sendall(req.encode())
    resp = s.recv(4096)
    if b"101" not in resp:
        raise RuntimeError(f"upgrade refused: {resp[:120]!r}")
    return s


def ws_close(s):
    """Gracefully close: send WS close frame, then SSL close_notify, then TCP."""
    try:
        # WebSocket close frame (opcode 0x8), masked, code 1000
        mask = os.urandom(4)
        s.sendall(bytes([0x88, 0x80 | 4]) + mask + mask)
    except Exception:
        pass
    try:
        s.unwrap()  # SSL close_notify
    except Exception:
        pass
    try:
        s.close()
    except Exception:
        pass


def ws_recv_exact(s, n):
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("closed")
        buf += chunk
    return buf


def ws_read_frame(s):
    hdr = ws_recv_exact(s, 2)
    op = hdr[0] & 0x0F
    ln = hdr[1] & 0x7F
    if ln == 126:
        ln = struct.unpack(">H", ws_recv_exact(s, 2))[0]
    elif ln == 127:
        ln = struct.unpack(">Q", ws_recv_exact(s, 8))[0]
    return op, ws_recv_exact(s, ln)


def ws_send_text(s, payload):
    data = payload.encode()
    header = bytearray([0x81])
    n = len(data)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header += struct.pack(">H", n)
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", n)
    mask = os.urandom(4)
    header += mask
    s.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def ws_wait_for(s, pred, max_frames=400):
    for _ in range(max_frames):
        op, payload = ws_read_frame(s)
        if op != 1:
            continue
        d = json.loads(payload)
        if pred(d):
            return d
    raise RuntimeError("matching frame not received")


# ------------------------------------------------------------------- GW checks
def gw_health():
    r = requests.get("https://127.0.0.1:8000/api/health", timeout=8)
    r.raise_for_status()
    d = r.json()
    svcs = d["services"]
    status = {k: v["status"] for k, v in svcs.items()}
    bad = {k: v for k, v in status.items() if v not in ("ok", "healthy", "configured")}
    if bad:
        raise RuntimeError(f"unhealthy services: {bad}")
    return json.dumps(status)


def gw_root():
    r = requests.get("https://127.0.0.1:8000/", timeout=8)
    r.raise_for_status()
    return f"200, bytes={len(r.content)}"


def gw_chat():
    r = requests.post("https://127.0.0.1:8000/api/chat",
                      json={"query": "what is the average wait time", "city": "chicago"}, timeout=15)
    r.raise_for_status()
    keys = sorted(r.json().keys())
    return f"200, keys={keys}"


def gw_incident():
    r = requests.post("https://127.0.0.1:8000/api/incident",
                      json={"text": "accident on main street"}, timeout=15)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def gw_camera_feed():
    r = requests.get("https://127.0.0.1:8000/api/camera/feed", timeout=15)
    r.raise_for_status()
    ct = r.headers.get("content-type", "")
    return f"200, content-type={ct}, bytes={len(r.content)}"


def gw_algo():
    r = requests.get("https://127.0.0.1:8000/api/algo", timeout=8)
    r.raise_for_status()
    d = r.json()
    n = len(d.get("algorithms", d)) if isinstance(d, dict) else len(d)
    return f"200, algorithms={n}"


def gw_events_rest():
    # Gateway route is /api/events/{path}; publish is POST-only on the bus.
    r = requests.post("https://127.0.0.1:8000/api/events/publish/cv.anomaly",
                      json={"message": "api check", "severity": "low"}, timeout=8)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def gw_ws_engine():
    s = ws_connect("wss://127.0.0.1:8000/ws")
    try:
        ws_send_text(s, json.dumps({"type": "city", "city": "chicago"}))
        frame = ws_wait_for(s, lambda d: "agents" in d)
        return f"frame tick={frame.get('tick')} agents={len(frame.get('agents', []))} signals={len(frame.get('signals', []))}"
    finally:
        ws_close(s)


def gw_ws_events():
    s = ws_connect("wss://127.0.0.1:8000/ws/events", timeout=8)
    try:
        # send a probe and expect at least one frame or a clean close
        ws_send_text(s, json.dumps({"type": "subscribe", "topic": "test"}))
        s.settimeout(6)
        try:
            op, payload = ws_read_frame(s)
            return f"frame op={op} bytes={len(payload)}"
        except socket.timeout:
            return "connected, no frames within 6s (probe only)"
    finally:
        ws_close(s)


# --------------------------------------------------------------- sidecar checks
def sc_camera_health():
    r = requests.get("https://127.0.0.1:9003/health", timeout=5)
    r.raise_for_status()
    return f"200 {r.json()}"


def sc_camera_feed():
    r = requests.get("https://127.0.0.1:9003/api/camera/feed", timeout=10)
    r.raise_for_status()
    return f"200, content-type={r.headers.get('content-type')}, bytes={len(r.content)}"


def sc_nlp_health():
    r = requests.get("https://127.0.0.1:9004/health", timeout=5)
    r.raise_for_status()
    return f"200 {r.json()}"


def sc_nlp_chat():
    r = requests.post("https://127.0.0.1:9004/chat",
                      json={"query": "what is the average wait time", "city": "chicago"}, timeout=10)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def sc_nlp_incident():
    r = requests.post("https://127.0.0.1:9004/incident",
                      json={"text": "road closed at 5th avenue"}, timeout=10)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def sc_nlp_feedback():
    r = requests.post("https://127.0.0.1:9004/feedback",
                      json={"text": "the simulation is great"}, timeout=10)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def sc_eventbus_health():
    r = requests.get("https://127.0.0.1:9005/health", timeout=5)
    r.raise_for_status()
    return f"200 {r.json()}"


def sc_eventbus_events():
    r = requests.get("https://127.0.0.1:9005/events", timeout=5)
    r.raise_for_status()
    return f"200, bytes={len(r.content)}"


def sc_eventbus_publish():
    r = requests.post("https://127.0.0.1:9005/publish/cv.anomaly",
                      json={"message": "test anomaly", "severity": "low"}, timeout=5)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def sc_algo_health():
    r = requests.get("https://127.0.0.1:9006/health", timeout=5)
    r.raise_for_status()
    return f"200 {r.json()}"


def sc_algo_algorithms():
    r = requests.get("https://127.0.0.1:9006/algorithms", timeout=5)
    r.raise_for_status()
    d = r.json()
    n = len(d) if isinstance(d, list) else len(d.get("algorithms", []))
    return f"200, algorithms={n}"


def sc_algo_toggle():
    r = requests.post("https://127.0.0.1:9006/algorithms/toggle",
                      json={"algo_id": "CV-1", "active": False}, timeout=5)
    r.raise_for_status()
    # restore so repeated runs stay green
    requests.post("https://127.0.0.1:9006/algorithms/toggle",
                  json={"algo_id": "CV-1", "active": True}, timeout=5)
    return f"200, keys={sorted(r.json().keys())}"


def dash_root():
    r = requests.get("https://127.0.0.1:3000/", timeout=8)
    r.raise_for_status()
    has_root = 'id="root"' in r.text or "root" in r.text
    return f"200, bytes={len(r.content)}, root_div={has_root}"


def dash_static():
    r = requests.get("https://127.0.0.1:3000/data/36_algo_matrix.json", timeout=8)
    r.raise_for_status()
    d = r.json()
    return f"200, total_algorithms={d.get('total_algorithms')}"


def engine_direct_ws():
    s = ws_connect("wss://127.0.0.1:9001")
    try:
        ws_send_text(s, json.dumps({"type": "city", "city": "chicago"}))
        frame = ws_wait_for(s, lambda d: "agents" in d)
        return f"direct 9001 frame: agents={len(frame.get('agents', []))}"
    finally:
        ws_close(s)


if __name__ == "__main__":
    print("=== Gateway (:8000) ===")
    check("GW GET /", gw_root)
    check("GW GET /api/health", gw_health)
    check("GW POST /api/chat", gw_chat)
    check("GW POST /api/incident", gw_incident)
    check("GW GET /api/camera/feed", gw_camera_feed)
    check("GW GET /api/algo", gw_algo)
    check("GW GET /api/events", gw_events_rest)
    check("GW WS /ws (engine proxy)", gw_ws_engine)
    check("GW WS /ws/events (event bus proxy)", gw_ws_events)

    print("=== Sidecars (direct) ===")
    check("CAM :9003 /health", sc_camera_health)
    check("CAM :9003 /api/camera/feed", sc_camera_feed)
    check("NLP :9004 /health", sc_nlp_health)
    check("NLP :9004 POST /chat", sc_nlp_chat)
    check("NLP :9004 POST /incident", sc_nlp_incident)
    check("NLP :9004 POST /feedback", sc_nlp_feedback)
    check("EVB :9005 /health", sc_eventbus_health)
    check("EVB :9005 GET /events", sc_eventbus_events)
    check("EVB :9005 POST /publish/cv.anomaly", sc_eventbus_publish)
    check("ALGO :9006 /health", sc_algo_health)
    check("ALGO :9006 GET /algorithms", sc_algo_algorithms)
    check("ALGO :9006 POST /algorithms/toggle", sc_algo_toggle)

    print("=== Dashboard (:3000) ===")
    check("DASH GET /", dash_root)
    check("DASH GET /data/36_algo_matrix.json", dash_static)

    print("=== Engine direct (:9001) ===")
    check("ENGINE WS direct", engine_direct_ws)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n=== SUMMARY: {passed}/{len(RESULTS)} passed ===")
    if failed:
        print("FAILED:")
        for n in failed:
            print(f"  - {n}")



