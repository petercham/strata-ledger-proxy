#!/usr/bin/env python3
r"""Regression selftest for collector_proxy.py.

Boots a fake streaming upstream plus the REAL proxy on throwaway ports and a
throwaway ledger directory. Never touches production 8080 / 8787, never edits
the real web root, never needs a GPU or the Strata engine.

  python usage/selftest_proxy.py

It asserts the relay contract: SSE must not be buffered, response headers must
be relayed, a mid-stream failure must not produce a second HTTP response,
request headers / chunked bodies must survive, and every chat request must
leave exactly one correct ledger row. It also pins key attribution: the
Bearer auth-scheme is case-insensitive and every row keeps its raw 8-hex fp.
"""
import gzip
import hashlib
import http.client
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY_SCRIPT = os.path.join(HERE, "collector_proxy.py")
UP_PORT = 18787
PX_PORT = 18080
KEY = "sk-selftest-case-insensitive"
KEY_FP = hashlib.sha256(KEY.encode()).hexdigest()[:8]
KEY_LABEL = "Selftest User"
SEEN = []
SEEN_LOCK = threading.Lock()
RESULTS = []
HOLD_GATE = threading.Event()          # gate stage (T-3): case=hold blocks here; set() releases exactly one
KEY_WAIT = "sk-gate-wait-marker"       # stage-2 marker keys: ledger rows found by their fp
KEY_FAST = "sk-gate-fast-marker"
KEY_WAIT_FP = hashlib.sha256(KEY_WAIT.encode()).hexdigest()[:8]
KEY_FAST_FP = hashlib.sha256(KEY_FAST.encode()).hexdigest()[:8]
KEY_3RD = "sk-gate-3rd-marker"         # rev11 T-4 A1: marker for the queued 3rd stream's ledger row
KEY_3RD_FP = hashlib.sha256(KEY_3RD.encode()).hexdigest()[:8]
KEY_3DROP = "sk-gate-3rd-drop-marker"  # rev11 T-4 A3: marker for the disconnected queued stream's row
KEY_3DROP_FP = hashlib.sha256(KEY_3DROP.encode()).hexdigest()[:8]
# ---- rev11 T-0 stub state: fake engine /v1/status (gate-follow reading source) ----
STATUS_MODE = "good"                   # "good" -> 200 JSON concurrency.serving; "broken" -> 200 {} (unreadable)
STATUS_SERVING = 2                     # serving/requested value served in "good" mode
GET_STATUS_HITS = 0                    # /v1/status GET counter (module-level, lock-guarded)
GET_STATUS_LOCK = threading.Lock()


def status_hits():
    with GET_STATUS_LOCK:
        return GET_STATUS_HITS


def rec(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(("PASS  " if ok else "FAIL  ") + name + ("  " + detail if detail else ""))


def sse_payload(i):
    return {"choices": [{"delta": {"content": "tok%d " % i}}], "model": "fake-model"}


USAGE_TAIL = {"choices": [], "usage": {"prompt_tokens": 321, "completion_tokens": 87,
                                      "prompt_tokens_details": {"cached_tokens": 111}},
              "model": "fake-model"}


class FakeUpstream(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _body(self):
        te = (self.headers.get("Transfer-Encoding") or "").lower()
        if "chunked" in te:
            parts = []
            while True:
                line = self.rfile.readline()
                if not line:
                    break
                try:
                    size = int(line.split(b";", 1)[0].strip(), 16)
                except ValueError:
                    break
                if size == 0:
                    self.rfile.readline()
                    break
                parts.append(self.rfile.read(size))
                self.rfile.read(2)
            return b"".join(parts)
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    @staticmethod
    def _case(path):
        return urllib.parse.parse_qs(urllib.parse.urlparse(path).query).get("case", ["json"])[0]

    def _fixed(self, status, data, headers=None, close=False):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        if close:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        if close:
            self.close_connection = True

    def _chunk(self, raw):
        self.wfile.write(("%x\r\n" % len(raw)).encode("ascii") + raw + b"\r\n")
        self.wfile.flush()

    def _sse(self, break_early=False):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        for i in range(6):
            raw = b"data: " + json.dumps(sse_payload(i)).encode() + b"\n\n"
            self._chunk(raw)
            time.sleep(0.2)
            if break_early and i == 1:
                self.close_connection = True
                return
        self._chunk(b"data: " + json.dumps(USAGE_TAIL).encode() + b"\n\n")
        self._chunk(b"data: [DONE]\n\n")
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    def do_POST(self):
        body = self._body()
        case = self._case(self.path)
        if case == "hold":
            # gate stage only (T-3): block on HOLD_GATE until the test side
            # releases it. Edge semantics: each set() lets exactly one hold
            # request through, then the event re-arms (clear inside).
            with SEEN_LOCK:
                SEEN.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()},
                             "body": body, "hold": True, "t": time.monotonic()})
            HOLD_GATE.wait(timeout=60)
            HOLD_GATE.clear()
            return self._fixed(200, json.dumps(USAGE_TAIL).encode())
        with SEEN_LOCK:
            SEEN.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()},
                         "body": body})
        if case == "sse":
            return self._sse()
        if case == "ssebreak":
            return self._sse(break_early=True)
        if case == "echo":
            payload = {"headers": {k.lower(): v for k, v in self.headers.items()},
                       "body": body.decode("utf-8", "replace")}
            return self._fixed(200, json.dumps(payload).encode())
        if case == "401":
            return self._fixed(401, b'{"error":"unauthorized"}')
        if case == "500":
            return self._fixed(500, b'{"error":"upstream boom"}')
        if case == "gzip":
            raw = gzip.compress(json.dumps(USAGE_TAIL).encode())
            return self._fixed(200, raw, {"Content-Encoding": "gzip"})
        if case == "slow":
            time.sleep(0.8)
            return self._fixed(200, json.dumps(USAGE_TAIL).encode())
        return self._fixed(200, json.dumps(USAGE_TAIL).encode())

    def do_GET(self):
        case = self._case(self.path)
        # rev11 T-0: fake engine /v1/status for the gate-follow reader.
        # Path minus query exactly == "/v1/status" -> answer from module-level
        # mutable state and count the hit. Other GET cases keep old behaviour.
        if urllib.parse.urlparse(self.path).path == "/v1/status":
            with GET_STATUS_LOCK:
                global GET_STATUS_HITS
                GET_STATUS_HITS += 1
            if STATUS_MODE == "good":
                payload = {"concurrency": {"serving": STATUS_SERVING,
                                           "requested": STATUS_SERVING}}
                return self._fixed(200, json.dumps(payload).encode())
            return self._fixed(200, b"{}")          # field absent = reading unavailable
        if case == "401":
            return self._fixed(401, b'{"error":"need key"}')
        if case == "gzip":
            raw = gzip.compress(b'{"models":["fake-model"]}')
            return self._fixed(200, raw, {"Content-Encoding": "gzip"})
        return self._fixed(200, b'{"models":["fake-model"]}')


def conn():
    return http.client.HTTPConnection("127.0.0.1", PX_PORT, timeout=15)


def post(path, obj, extra=None, raw_body=None):
    c = conn()
    body = raw_body if raw_body is not None else json.dumps(obj).encode()
    h = {"Content-Type": "application/json"}
    h.update(extra or {})
    c.request("POST", path, body=body, headers=h)
    return c


def ledger(tmp, min_rows=0):
    """The client can receive the full response a few ms before the handler
    thread finishes writing the ledger row; poll briefly when an exact count
    matters."""
    p = os.path.join(tmp, "requests-%s.jsonl" % time.strftime("%Y-%m-%d"))
    deadline = time.monotonic() + 2.0
    while True:
        rows = []
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                rows = [json.loads(x) for x in f if x.strip()]
        if len(rows) >= min_rows or time.monotonic() >= deadline:
            return rows
        time.sleep(0.05)


def wait_port(port, timeout=12):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=0.4)
            s.close()
            return True
        except OSError:
            time.sleep(0.1)
    return False


def raw_chunked_request(path, body):
    s = socket.create_connection(("127.0.0.1", PX_PORT), timeout=15)
    head = ("POST %s HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\n"
            "Transfer-Encoding: chunked\r\nConnection: close\r\n\r\n" % path).encode()
    s.sendall(head + ("%x\r\n" % len(body)).encode() + body + b"\r\n0\r\n\r\n")
    out = b""
    while True:
        try:
            b = s.recv(65536)
        except socket.timeout:
            break
        if not b:
            break
        out += b
    s.close()
    return out


def read_ext():
    c = conn()
    c.request("GET", "/ext.json")
    r = c.getresponse()
    try:
        d = json.loads(r.read())
    except ValueError:
        d = {}
    c.close()
    return d


def wait_gate(pred, timeout=10):
    """Poll /ext.json until the gate section satisfies pred. Pushes happen at
    acquire/release/beat, so a fresh reading lands within one request event."""
    end = time.monotonic() + timeout
    g = None
    while time.monotonic() < end:
        g = read_ext().get("gate")
        if g is not None and pred(g):
            return g
        time.sleep(0.1)
    return g


def gate_touch():
    """Local /health GET = a snapshot push point (same route rev10's probes use)."""
    c = conn()
    try:
        c.request("GET", "/health")
        c.getresponse().read()
    except Exception:
        pass
    c.close()


def wait_gate_fresh(pred, timeout=10, touch_every=1.0):
    """rev11 variant: /ext.json's gate section is freshness-gated (push older
    than 30s = field absent, monitor_ext contract). When a raw streaming
    request holds the wire past that window, the snapshot goes absent mid-test;
    this polls with a periodic local /health push to keep the pushed state
    fresh, so queued/inflight readings stay observable during long streams.
    Same pred contract; returns the satisfying gate dict or the last reading."""
    end = time.monotonic() + timeout
    g = None
    last_touch = time.monotonic()
    while time.monotonic() < end:
        g = read_ext().get("gate")
        if g is not None and pred(g):
            return g
        if time.monotonic() - last_touch >= touch_every:
            gate_touch()
            last_touch = time.monotonic()
        time.sleep(0.1)
    return g


def seen_holds():
    with SEEN_LOCK:
        return [s for s in SEEN if s.get("hold")]


def find_row(tmp, fp, timeout=3.0):
    """Poll the day ledger for the row written under key fingerprint fp."""
    end = time.monotonic() + timeout
    while True:
        row = next((x for x in ledger(tmp) if x.get("fp") == fp), None)
        if row is not None or time.monotonic() >= end:
            return row
        time.sleep(0.1)


def start_hold(tag, results):
    """Fire one chat request pinned on the fake upstream (case=hold)."""
    def run():
        try:
            cc = post("/v1/chat/completions?case=hold", {"model": "m", "fx": tag})
            rr = cc.getresponse()
            results[tag] = (rr.status, rr.read())
            cc.close()
        except Exception as e:
            results[tag] = (None, str(e))
    t = threading.Thread(target=run)
    t.start()
    return t


def pin_slot(tag, held):
    """Deterministic slot pinning: wait until the gate is clean, fire one hold,
    return only after THAT hold reached the upstream (so it verifiably occupies
    the only slot)."""
    wait_gate(lambda g: g.get("inflight") == 0 and g.get("queued") == 0, timeout=15)
    before = len(seen_holds())
    t = start_hold(tag, held)
    end = time.monotonic() + 10
    while time.monotonic() < end:
        if len(seen_holds()) > before:
            return t
        time.sleep(0.05)
    return t


def hold_extra(tag, held):
    """Occupy one MORE slot while another hold is already in flight (limit>=2).
    pin_slot's clean-gate wait would spin to its timeout by design here, so
    additional pins use this: fire a hold, return once it reached upstream,
    then settle /ext.json until the gate snapshot shows the new inflight —
    without that settle the NEXT request reads a stale snapshot on the server
    side too? No: the gate state itself is already incremented, but the push
    only rides request events; the settle exists so queued-state assertions in
    later code observe a consistent snapshot (the real race fixed here is the
    test's own wait_gate baseline going stale between pin and next fire)."""
    before = len(seen_holds())
    t = start_hold(tag, held)
    end = time.monotonic() + 10
    while time.monotonic() < end:
        if len(seen_holds()) > before:
            break
        time.sleep(0.05)
    return t


def settle_gate_inflight(n, timeout=3.0):
    """Block until /ext.json gate.inflight >= n (the pin is gate-visible)."""
    return wait_gate(lambda g: (g.get("inflight") or 0) >= n, timeout=timeout) is not None


def read_http_chunks(sock, t0, pings):
    """Consume ONE HTTP/1.1 chunk-framed response from a raw socket (rev11 T-4).
    `pings` is a SHARED list: every `: ping` comment-chunk arrival appends its
    monotonic offset (sec, from t0) immediately, so the test side can react to
    heartbeats while the stream is still running (keep-alive proof stream).
    stats: raw bytes, head, status_lines, data_frames, done([DONE]),
    terminal_zero(final 0-chunk = clean stream end), reset, timeout."""
    st = {"raw": b"", "head": b"", "status_lines": 0, "data_frames": 0,
          "done": False, "terminal_zero": False, "reset": False, "timeout": False}
    buf = b""
    head_done = False
    while True:
        try:
            b = sock.recv(65536)
        except socket.timeout:
            st["timeout"] = True
            break
        except ConnectionResetError:
            st["reset"] = True
            break
        except OSError:
            break
        if not b:
            break
        now = time.monotonic() - t0
        st["raw"] += b
        buf += b
        if not head_done:
            sep = buf.find(b"\r\n\r\n")
            if sep == -1:
                continue
            st["head"] = buf[:sep]
            st["status_lines"] = st["head"].count(b"HTTP/1.1 ")
            buf = buf[sep + 4:]
            head_done = True
        while True:
            sep = buf.find(b"\r\n")
            if sep == -1:
                break
            try:
                size = int(buf[:sep].split(b";", 1)[0].strip(), 16)
            except ValueError:
                break
            if size == 0:
                st["terminal_zero"] = True
                break
            if len(buf) < sep + 2 + size + 2:
                break
            payload = buf[sep + 2:sep + 2 + size]
            buf = buf[sep + 2 + size + 2:]
            # count OCCURRENCES inside payload, not payload count: TCP may
            # coalesce two flushed frames into one read — same tally rev10
            # used (full.count(b"data: ")), just timestamped per arrival.
            np_ = payload.count(b": ping")
            if np_:
                pings.extend([now] * np_)
            st["data_frames"] += payload.count(b"data: ")
            if b"[DONE]" in payload:
                st["done"] = True
        if st["terminal_zero"]:
            break
    return st


def fire_raw_stream(path, body_obj, auth_key, stats_box):
    """Raw-socket streaming chat POST (rev11 T-4). The reader thread fills
    stats_box["st"]/["pings"]; stats_box["sock"] exposes the live socket so the
    test side can force a client-side disconnect mid-heartbeat (A3)."""
    def run():
        t0 = time.monotonic()
        try:
            s = socket.create_connection(("127.0.0.1", PX_PORT), timeout=20)
        except OSError as e:
            stats_box["st"] = {"connect_err": str(e)}
            return
        stats_box["sock"] = s
        pings = stats_box.setdefault("pings", [])    # shared live list (GIL-atomic appends)
        bj = json.dumps(body_obj).encode()
        s.sendall(("POST %s HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer %s\r\n"
                   "Content-Type: application/json\r\nContent-Length: %d\r\n"
                   "Connection: close\r\n\r\n" % (path, auth_key, len(bj))).encode() + bj)
        st = read_http_chunks(s, t0, pings)
        stats_box["st"] = st
        stats_box["elapsed"] = time.monotonic() - t0
        try:
            s.close()
        except OSError:
            pass
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def main():
    global STATUS_MODE, STATUS_SERVING, GET_STATUS_HITS
    tmp = tempfile.mkdtemp(prefix="proxy-selftest-")
    os.makedirs(os.path.join(tmp, "web"), exist_ok=True)
    cfg = {"name": "selftest", "mode": "proxy", "out_dir": tmp,
           "lock_port": 43991, "listen": "127.0.0.1:%d" % PX_PORT,
           "upstream": "http://127.0.0.1:%d" % UP_PORT,
           "web_root": os.path.join(tmp, "web"), "force_include_usage": True,
           "report_hour": 0, "report_minute": 0,
           "key_labels": {KEY_FP: KEY_LABEL}}
    cfg_path = os.path.join(tmp, "config.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)

    upstream = ThreadingHTTPServer(("127.0.0.1", UP_PORT), FakeUpstream)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    # Bash sessions carry HTTP_PROXY, which answers 127.0.0.1 urllib calls with a
    # fake 502. The production process never has it; strip it for the child too.
    child_env = os.environ.copy()
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        child_env.pop(k, None)
    child_env["NO_PROXY"] = "127.0.0.1,localhost"
    proc = subprocess.Popen([sys.executable, PROXY_SCRIPT, "--config", cfg_path],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=child_env)
    try:
        if not wait_port(PX_PORT):
            rec("proxy boots on throwaway port", False, "port %d never opened" % PX_PORT)
            return 1
        rec("proxy boots on throwaway port", True)

        # 1. plain non-stream response: exact body + Content-Length + ledger usage
        c = post("/v1/chat/completions?case=json", {"model": "m", "stream": False})
        r = c.getresponse(); data = r.read(); c.close()
        rows = ledger(tmp, 1)
        rec("non-stream: status, Content-Length, ledger usage",
            r.status == 200 and r.getheader("Content-Length") == str(len(data))
            and len(rows) == 1 and rows[-1]["prompt"] == 321 and rows[-1]["gen"] == 87,
            "status=%s rows=%d" % (r.status, len(rows)))

        # 2. SSE: headers must arrive BEFORE the upstream finishes generating
        t0 = time.monotonic()
        c = post("/v1/chat/completions?case=sse", {"model": "m", "stream": True})
        r = c.getresponse()
        ttfb = time.monotonic() - t0
        body = r.read()
        total = time.monotonic() - t0
        c.close()
        rows = ledger(tmp)
        rec("SSE: not buffered (headers arrive early)",
            ttfb < 0.5 and total > 1.0 and r.getheader("Transfer-Encoding") == "chunked"
            and r.getheader("Content-Length") is None,
            "ttfb=%.3fs total=%.3fs TE=%s" % (ttfb, total, r.getheader("Transfer-Encoding")))
        rec("SSE: byte-preserving relay + final usage accounting",
            body.count(b"data: ") == 8 and b"[DONE]" in body
            and len(rows) == 2 and rows[-1]["prompt"] == 321
            and rows[-1]["cached"] == 111 and rows[-1]["gen"] == 87,
            "chunks=%d rows=%d usage=%s" % (body.count(b"data: "), len(rows),
                                            {k: rows[-1].get(k) for k in ("prompt", "cached", "gen")}))

        # 3. force_include_usage must be injected without losing other fields
        rec("stream_options.include_usage injected",
            any(b'"include_usage": true' in s["body"] for s in SEEN),
            "seen=%d" % len(SEEN))

        # 4. non-chat POST must relay x-api-key / anthropic-version, no empty Authorization
        c = post("/v1/embeddings?case=echo", {"input": "hi"},
                 {"x-api-key": "secret-xyz", "Anthropic-Version": "2023-06-01"})
        r = c.getresponse(); echo = json.loads(r.read()); c.close()
        h = echo["headers"]
        rec("non-chat POST: auth headers survive",
            h.get("x-api-key") == "secret-xyz" and h.get("anthropic-version") == "2023-06-01"
            and h.get("authorization", "") == "",
            "x-api-key=%s anthropic-version=%s" % (h.get("x-api-key"), h.get("anthropic-version")))
        rec("non-chat POST: no ledger row", len(ledger(tmp)) == 2)

        # 5. chunked request body must not be silently lost
        want = b'{"model":"m","stream":false}'
        out = raw_chunked_request("/v1/chat/completions?case=echo", want)
        echoed = ""
        sep = out.split(b"\r\n\r\n", 1)
        if len(sep) == 2:
            try:
                echoed = json.loads(sep[1])["body"]
            except Exception:
                pass
        ok = b"HTTP/1.1 200" in out and echoed == want.decode()
        rec("chunked request body arrives intact", ok, "echoed=%r bytes=%d" % (echoed, len(out)))

        # 6. a JSON array body must not crash the handler thread
        c = post("/v1/chat/completions?case=json", {}, raw_body=b"[1,2,3]")
        r = c.getresponse(); r.read(); c.close()
        rec("non-object JSON body does not crash", r.status == 200, "status=%s" % r.status)

        # 7. real upstream error status must be passed through, not masked as 502
        c = post("/v1/chat/completions?case=401", {"model": "m"})
        r = c.getresponse(); b401 = r.read(); c.close()
        rows = ledger(tmp)
        rec("upstream 401 passes through + is recorded",
            r.status == 401 and b401 == b'{"error":"unauthorized"}' and rows[-1].get("error") == 401,
            "status=%s error=%s" % (r.status, rows[-1].get("error")))
        c = post("/v1/chat/completions?case=500", {"model": "m"})
        r = c.getresponse(); r.read(); c.close()
        rec("upstream 500 passes through", r.status == 500)

        # 8. gzip / Content-Encoding header must survive the relay
        c = post("/v1/chat/completions?case=gzip", {"model": "m"})
        r = c.getresponse(); z = r.read(); c.close()
        rows = ledger(tmp)
        rec("Content-Encoding relayed + usage still accounted",
            r.getheader("Content-Encoding") == "gzip"
            and json.loads(gzip.decompress(z))["model"] == "fake-model"
            and rows[-1]["prompt"] == 321 and rows[-1]["gen"] == 87,
            "usage=%s" % {k: rows[-1].get(k) for k in ("prompt", "gen")})

        # 9. mid-stream upstream failure: no second HTTP response on the same socket
        c = post("/v1/chat/completions?case=ssebreak", {"model": "m", "stream": True})
        r = c.getresponse()
        broken = b""
        incomplete = False
        try:
            broken = r.read()
        except http.client.IncompleteRead as e:
            broken = e.partial or b""
            incomplete = True
        except Exception:
            incomplete = True
        c.close()
        rows = ledger(tmp, 1)
        rec("mid-stream failure: no second HTTP response",
            incomplete and broken.count(b"HTTP/1.1") == 0
            and rows[-1].get("error") is not None,
            "incomplete=%s partial_bytes=%d status-lines-in-body=%d ledger_error=%s"
            % (incomplete, len(broken), broken.count(b"HTTP/1.1"), rows[-1].get("error")))

        # 10. client disconnect: upstream still drained and accounted
        before = len(ledger(tmp))
        c = post("/v1/chat/completions?case=sse", {"model": "m", "stream": True})
        r = c.getresponse()
        c.close()                                  # hang up immediately
        time.sleep(1.8)
        rows = ledger(tmp)
        rec("client disconnect still records full usage",
            len(rows) == before + 1 and rows[-1].get("gen") == 87,
            "rows %d->%d gen=%s" % (before, len(rows), rows[-1].get("gen")))

        # 11. concurrent streams do not serialize
        before = len(ledger(tmp))
        errs = []
        def one(i):
            try:
                cc = post("/v1/chat/completions?case=sse", {"model": "m", "stream": True, "i": i})
                rr = cc.getresponse(); rr.read(); cc.close()
                if rr.status != 200: errs.append(i)
            except Exception as e:
                errs.append((i, str(e)))
        t0 = time.monotonic()
        ts = [threading.Thread(target=one, args=(i,)) for i in range(5)]
        [t.start() for t in ts]; [t.join() for t in ts]
        elapsed = time.monotonic() - t0
        rec("5 concurrent streams stay parallel",
            not errs and elapsed < 3.0 and len(ledger(tmp)) == before + 5,
            "elapsed=%.2fs rows+%d errs=%s" % (elapsed, len(ledger(tmp)) - before, errs))

        # 12. GET: local /health, upstream 401 passthrough, GET gzip header
        c = conn(); c.request("GET", "/health"); r = c.getresponse(); r.read(); c.close()
        rec("GET /health local route", r.status == 200)
        c = conn(); c.request("GET", "/v1/models?case=401"); r = c.getresponse(); r.read(); c.close()
        rec("GET upstream 401 passes through", r.status == 401)
        c = conn(); c.request("GET", "/v1/models?case=gzip"); r = c.getresponse(); z = r.read(); c.close()
        rec("GET Content-Encoding relayed", r.getheader("Content-Encoding") == "gzip"
            and json.loads(gzip.decompress(z))["models"] == ["fake-model"])

        # 13. RFC 7235 auth-scheme is case-insensitive: one key stays ONE
        #     identity, and every ledger row keeps its raw 8-hex fingerprint.
        before = len(ledger(tmp))
        for scheme in ("Bearer", "bearer", "BEARER"):
            c = post("/v1/chat/completions?case=json", {"model": "m"},
                     {"Authorization": "%s %s" % (scheme, KEY)})
            r = c.getresponse(); r.read(); c.close()
        auth_rows = ledger(tmp, before + 3)[before:]
        rec("Bearer / bearer -> same key + fp",
            len(auth_rows) == 3
            and auth_rows[0].get("key") == KEY_LABEL
            and auth_rows[1].get("key") == KEY_LABEL
            and auth_rows[0].get("fp") == KEY_FP
            and auth_rows[1].get("fp") == KEY_FP,
            "keys=%s fps=%s" % ([x.get("key") for x in auth_rows],
                                [x.get("fp") for x in auth_rows]))
        rec("mixed-case BEARER -> same key + fp",
            len(auth_rows) == 3
            and auth_rows[2].get("key") == KEY_LABEL
            and auth_rows[2].get("fp") == KEY_FP,
            "key=%s fp=%s" % (auth_rows[2].get("key") if len(auth_rows) > 2 else "?",
                              auth_rows[2].get("fp") if len(auth_rows) > 2 else "?"))

        # 14. a chat request authenticated via x-api-key also records a valid fp.
        before = len(ledger(tmp))
        c = post("/v1/chat/completions?case=json", {"model": "m"},
                 {"x-api-key": "sk-via-x-api-key"})
        r = c.getresponse(); r.read(); c.close()
        rows = ledger(tmp, before + 1)
        xrow = rows[-1]
        rec("x-api-key chat request records fp",
            bool(re.fullmatch(r"[0-9a-f]{8}", str(xrow.get("fp", "")))),
            "key=%s fp=%s" % (xrow.get("key"), xrow.get("fp")))

        # 15. EVERY ledger row (including the no-key "none" rows) carries a
        #     valid fp: 8 lowercase hex chars, or the literal "none".
        allrows = ledger(tmp)
        fp_re = re.compile(r"^(?:[0-9a-f]{8}|none)$")
        bad_fp = [i for i, row in enumerate(allrows)
                  if not isinstance(row.get("fp"), str)
                  or not fp_re.fullmatch(row.get("fp"))]
        none_rows = [row for row in allrows if row.get("key") == "none"]
        rec("every ledger row has valid fp (8 lowercase hex or none)",
            not bad_fp and all(row.get("fp") == "none" for row in none_rows),
            "rows=%d bad=%s none_rows=%d" % (len(allrows), bad_fp, len(none_rows)))

        # 16. gate closed by default: /ext.json carries NO gate section (absent field)
        ext1 = read_ext()
        rec("gate:default no gate section in ext.json", "gate" not in ext1,
            "gate=%s keys=%s" % (ext1.get("gate"), sorted(ext1)[:6]))

        # 16b. rev11 T-2 (1) 判据③-4: default cfg (NO gate_follow key) -> the
        #      gate-follow thread polls nothing. Stub-side counter is the proof:
        #      zero /v1/status GETs across the whole default stage.
        hits_default = status_hits()
        rec("gate:follow off by default never polls status", hits_default == 0,
            "hits=%d (default cfg has no gate_follow key; stub counter; urlopen side-evidence: grep -c urlopen = 4 in collector_proxy.py)" % hits_default)

        # ================= T-2 stage two: gate ON (small test values, never
        # production defaults). Same cfg path, same lock_port, same ports.
        cfg2 = dict(cfg)
        cfg2["max_inflight"] = 1
        cfg2["queue_beat_s"] = 0.4
        cfg2["gate_wait_s"] = 1.0
        cfg2["key_labels"] = dict(cfg.get("key_labels") or {})
        cfg2["key_labels"][KEY_WAIT_FP] = "Gate Wait"
        cfg2["key_labels"][KEY_FAST_FP] = "Gate Fast"
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg2, f)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        HOLD_GATE.clear()
        proc = subprocess.Popen([sys.executable, PROXY_SCRIPT, "--config", cfg_path],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=child_env)
        if not wait_port(PX_PORT):
            rec("gate:proxy restarts with gate config", False, "port %d never opened" % PX_PORT)
            bad = [n for n, ok, _ in RESULTS if not ok]
            print("\n%d/%d PASS" % (len(RESULTS) - len(bad), len(RESULTS)))
            return 1

        # 17. 判据② limit=1: a held request pins the only slot; the second request
        #     is queued and then gets the REAL upstream answer (never 429/409).
        held = {}
        tA = pin_slot("judge2", held)
        res2 = {}
        def second():
            try:
                cc = post("/v1/chat/completions?case=json", {"model": "m"})
                rr = cc.getresponse()
                res2["status"] = rr.status
                res2["body"] = rr.read()
                res2["te"] = rr.getheader("Transfer-Encoding")
                cc.close()
            except Exception as e:
                res2["err"] = str(e)
        tB = threading.Thread(target=second)
        tB.start()
        time.sleep(0.6)                       # the 2nd request is queued by now (queueing
        # itself is not a push point, so no ext wait for queued here)
        HOLD_GATE.set()                       # free the slot -> handed to the queue head
        tB.join(timeout=10)
        tA.join(timeout=10)
        want = json.dumps(USAGE_TAIL).encode()
        rec("gate:2nd request gets real upstream under limit1",
            res2.get("status") == 200 and res2.get("body") == want
            and res2.get("status") not in (429, 409)
            and held.get("judge2", (None,))[0] == 200,
            "2nd status=%s refused=%s 1st status=%s 1st unaffected=%s body==upstream:%s"
            % (res2.get("status"), res2.get("status") in (429, 409),
               held.get("judge2", (None,))[0],
               held.get("judge2", (None,))[0] == 200, res2.get("body") == want))

        # 18. 判据③ SSE waiting past queue_beat_s: headers + `: ping` comment frames
        #     arrive FIRST, then the real engine stream joins the same socket.
        held = {}
        tA = pin_slot("judge3", held)
        buf = []
        def raw_sse():
            s = socket.create_connection(("127.0.0.1", PX_PORT), timeout=20)
            bj = json.dumps({"model": "m", "stream": True}).encode()
            s.sendall(("POST /v1/chat/completions?case=sse HTTP/1.1\r\nHost: x\r\n"
                       "Content-Type: application/json\r\nContent-Length: %d\r\n"
                       "Connection: close\r\n\r\n" % len(bj)).encode() + bj)
            try:
                while True:
                    b = s.recv(65536)
                    if not b:
                        break
                    buf.append(b)
            except OSError:
                pass
            s.close()
        tR = threading.Thread(target=raw_sse)
        tR.start()
        t0sse = time.monotonic()
        ping_seen_at = None
        end = time.monotonic() + 3.0
        while time.monotonic() < end:
            bb = b"".join(buf)
            if b": ping" in bb:
                ping_seen_at = time.monotonic() - t0sse
                break
            time.sleep(0.05)
        HOLD_GATE.set()                       # slot frees -> stream starts
        tR.join(timeout=20)
        tA.join(timeout=10)
        full = b"".join(buf)
        head = full.split(b"\r\n\r\n", 1)[0]
        rec("gate:sse heartbeat before slot",
            ping_seen_at is not None and head.startswith(b"HTTP/1.1 200")
            and b"Transfer-Encoding: chunked" in head and b"text/event-stream" in head
            and b": ping" in full and full.count(b"data: ") == 8 and b"[DONE]" in full
            and full.find(b": ping") < full.find(b"data: ")
            and full.count(b"HTTP/1.1 ") == 1,
            "ttfb_ping=%ss head=%r ping_before_data=%s data_frames=%d has_DONE=%s status_lines=%d"
            % (("%0.2f" % ping_seen_at) if ping_seen_at else "never",
               head[:70], full.find(b": ping") < full.find(b"data: "),
               full.count(b"data: "), b"[DONE]" in full, full.count(b"HTTP/1.1 ")))

        # 19. 判据④ waited out gate_wait_s with no free slot -> still forwarded, never refused
        held = {}
        tA = pin_slot("judge4", held)         # slot verifiably occupied (no free slot ahead)
        t0 = time.monotonic()
        c = post("/v1/chat/completions?case=json", {"model": "m"})
        r = c.getresponse(); r.read(); c.close()
        waited = time.monotonic() - t0
        HOLD_GATE.set()
        tA.join(timeout=10)
        rec("gate:gate_wait_s expiry forwards", r.status == 200 and waited >= 0.9,
            "waited=%.2fs (gate_wait_s=1.0) status=%s refused=%s"
            % (waited, r.status, r.status in (429, 409)))

        # 20. 判据⑤ FIFO order: fa pins the slot, fb then fc queue at the gate
        #     (serialized arrivals; beat_s=0.4 < 0.5 spacing guarantees the queue
        #     order), slots released one at a time -> upstream arrival order ==
        #     initiation order. A non-FIFO gate could not pass.
        wait_gate(lambda g: g.get("inflight") == 0 and g.get("queued") == 0, timeout=10)
        held = {}
        order = []
        tA = start_hold("fa", held)
        wait_gate(lambda g: (g.get("inflight") or 0) >= 1, timeout=10)
        hs = seen_holds()
        # fa already reached the upstream (that is what occupies the slot): the
        # newest SEEN hold must be fa -> first element of the arrival order
        for tag in ("fa", "fb", "fc"):
            if hs and b'"fx": "%s"' % tag.encode() in hs[-1]["body"]:
                order.append(tag)
                break
        tB = start_hold("fb", held)
        time.sleep(0.5)                       # fb is in the gate queue by now
        tC = start_hold("fc", held)
        time.sleep(0.5)                       # fc queued behind fb
        for _ in range(2):                    # two queued waits get handed the freed slot
            before = len(seen_holds())
            HOLD_GATE.set()
            end = time.monotonic() + 12
            while time.monotonic() < end:
                hs = seen_holds()
                if len(hs) > before:
                    for s in hs[before:]:
                        for tag in ("fa", "fb", "fc"):
                            if b'"fx": "%s"' % tag.encode() in s["body"]:
                                order.append(tag)
                    break
                time.sleep(0.05)
        HOLD_GATE.set()                       # release the last in-flight hold
        for t in (tA, tB, tC):
            t.join(timeout=15)
        g = wait_gate(lambda g: g.get("inflight") == 0 and g.get("queued") == 0, timeout=10)
        ok = order == ["fa", "fb", "fc"]
        rec("gate:fifo order preserved", ok,
            "arrival_order=%s initiation_order=[fa, fb, fc] final=%s"
            % (order, {k: (g or {}).get(k) for k in ("inflight", "queued")}))

        # 21. 判据⑥ failure injections must not leak slots
        wait_gate(lambda g: g.get("inflight") == 0 and g.get("queued") == 0, timeout=10)
        infl = []
        c = post("/v1/chat/completions?case=500", {"model": "m"})
        r = c.getresponse(); r.read(); c.close()
        g = wait_gate(lambda g: g.get("inflight") == 0, timeout=10)
        infl.append((g or {}).get("inflight"))
        c = post("/v1/chat/completions?case=ssebreak", {"model": "m", "stream": True})
        r = c.getresponse()
        try:
            r.read()
        except Exception:
            pass
        c.close()
        g = wait_gate(lambda g: g.get("inflight") == 0, timeout=10)
        infl.append((g or {}).get("inflight"))
        c = post("/v1/chat/completions?case=sse", {"model": "m", "stream": True})
        c.getresponse()
        c.close()                              # client hangs up immediately
        g = wait_gate(lambda g: g.get("inflight") == 0, timeout=10)
        infl.append((g or {}).get("inflight"))
        rec("gate:no slot leak after failures", infl == [0, 0, 0],
            "inflight after upstream500 / ssebreak / client-disconnect = %s" % infl)

        # 22. 判据⑦ non-chat paths never gated: gate open AND saturated, then gate
        #     closed — both readings must show immediate answers and queued==0.
        held = {}
        tA = pin_slot("judge7", held)
        t0 = time.monotonic()
        c = conn(); c.request("GET", "/v1/models"); r = c.getresponse(); r.read(); c.close()
        dt_get = time.monotonic() - t0
        t0 = time.monotonic()
        c = post("/v1/embeddings?case=echo", {"input": "hi"})
        r2 = c.getresponse(); r2.read(); c.close()
        dt_emb = time.monotonic() - t0
        g_open = read_ext().get("gate") or {}
        HOLD_GATE.set()
        tA.join(timeout=10)
        wait_gate(lambda g: g.get("inflight") == 0, timeout=10)
        # counter-example with the gate closed: rewrite the SAME cfg path (per-request
        # re-read means this takes effect without a restart) and repeat the probes
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        t0 = time.monotonic()
        c = conn(); c.request("GET", "/v1/models"); r3 = c.getresponse(); r3.read(); c.close()
        dt_get_off = time.monotonic() - t0
        t0 = time.monotonic()
        c = post("/v1/embeddings?case=echo", {"input": "hi"})
        r4 = c.getresponse(); r4.read(); c.close()
        dt_emb_off = time.monotonic() - t0
        rec("gate:non-chat never gated",
            r.status == 200 and r2.status == 200 and r3.status == 200 and r4.status == 200
            and max(dt_get, dt_emb) < 0.9 and max(dt_get_off, dt_emb_off) < 0.9
            and (g_open.get("queued") or 0) == 0,
            "gate ON + saturated: GET %.2fs POST %s %.2fs gate.queued=%s | gate OFF: GET %.2fs POST %.2fs"
            % (dt_get, "embeddings", dt_emb, g_open.get("queued"), dt_get_off, dt_emb_off))
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg2, f)

        # 23. 判据⑧ queue_wait_ms: written only for requests that actually waited
        held = {}
        tA = pin_slot("judge8", held)         # slot occupied -> the next request must wait
        c = post("/v1/chat/completions?case=json", {"model": "m"},
                 {"Authorization": "Bearer %s" % KEY_WAIT})
        r = c.getresponse(); r.read(); c.close()   # waited, then gate_wait_s expiry
        HOLD_GATE.set()
        tA.join(timeout=10)
        wait_gate(lambda g: g.get("inflight") == 0, timeout=10)
        c = post("/v1/chat/completions?case=json", {"model": "m"},
                 {"Authorization": "Bearer %s" % KEY_FAST})
        r = c.getresponse(); r.read(); c.close()   # slot free: never waited
        rows = []
        for _ in range(40):                        # poll until the last row landed
            rows = ledger(tmp)
            if any(x.get("fp") == KEY_FAST_FP for x in rows):
                break
            time.sleep(0.1)
        wrow = next((x for x in rows if x.get("fp") == KEY_WAIT_FP), None)
        frow = next((x for x in rows if x.get("fp") == KEY_FAST_FP), None)
        ledger_path = os.path.join(tmp, "requests-%s.jsonl" % time.strftime("%Y-%m-%d"))
        rec("gate:queue_wait_ms written only when waited",
            wrow is not None and wrow.get("queue_wait_ms", -1) >= 0
            and frow is not None and "queue_wait_ms" not in frow,
            "ledger=%s waited row fp=%s queue_wait_ms=%s | unwaited row fp=%s has field=%s"
            % (ledger_path, KEY_WAIT_FP, wrow.get("queue_wait_ms") if wrow else None,
               KEY_FAST_FP, "queue_wait_ms" in (frow or {})))

        # 24. /ext.json gate section shape (five keys, limit echoed back)
        g = wait_gate(lambda g: set(g) >= {"inflight", "queued", "limit",
                                           "waited_total", "beat_total"}, timeout=10)
        rec("gate:ext.json gate section shape",
            g is not None and set(g) >= {"inflight", "queued", "limit", "waited_total", "beat_total"}
            and g.get("limit") == 1,
            "gate=%s" % g)

        # 25. rev10a T-2: queued visible in /ext.json at the INSTANT of enrolment,
        #     long before the first queue_beat_s heartbeat. Per-request config
        #     re-read lets us push queue_beat_s to 10.0 with NO restart: under the
        #     old behaviour the first post-enrolment push would be the 10s beat, so
        #     a 3s poll window could never see queued>=1 (fails pre-fix, passes post).
        BEAT_T2 = 10.0
        cfg3 = dict(cfg2)
        cfg3["queue_beat_s"] = BEAT_T2               # far beyond the 3s poll window
        cfg3["gate_wait_s"] = 8.0                    # no expiry-forced forward inside the window
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg3, f)
        held = {}
        tA = pin_slot("t2vis", held)                 # the only slot is verifiably pinned
        t0q = time.monotonic()
        tB = start_hold("t2q", held)                 # 2nd request enters the gate queue
        t_seen, q_seen = None, 0
        endq = time.monotonic() + 3.0                # poll window: 3s << queue_beat_s
        while time.monotonic() < endq:
            gq = (read_ext().get("gate") or {})
            q_seen = gq.get("queued") or 0
            if q_seen >= 1:
                t_seen = time.monotonic() - t0q
                break
            time.sleep(0.05)
        HOLD_GATE.set()                              # release -> queued request completes (红线二 safe)
        tB.join(timeout=15)
        tA.join(timeout=10)
        rec("gate:queued visible in ext before first beat",
            t_seen is not None and t_seen < BEAT_T2,
            "queued first seen=%s t_seen=%ss queue_beat_s=%s (3s poll window << first beat)"
            % (q_seen, "%0.2f" % t_seen if t_seen is not None else "never", BEAT_T2))
        with open(cfg_path, "w", encoding="utf-8") as f:   # restore gate-stage cfg (per-request re-read)
            json.dump(cfg2, f)

        # ================================================================
        # rev11 T-2 follow-assertion group. All run inside the gate-ON stage
        # using rev10's per-request config re-read (cfg edits need no restart).
        # Each parameterising assertion restores cfg on exit (rev10a lesson).
        # ================================================================
        # ---- T-2 (2) 判据③-5: boot fallback to static max_inflight -------
        # follow ON but stub serves an UNREADABLE status (broken) AND a serving
        # value (2) deliberately DIFFERENT from the static fallback (1). The
        # effective limit must fall back to static 1 -> a 2nd request queues.
        STATUS_MODE = "broken"; STATUS_SERVING = 2   # stub pinned BEFORE the switch flips
        cfgf = dict(cfg2)                            # gate_wait_s stays at the stage's 1.0
        cfgf["max_inflight"] = 1
        cfgf["gate_follow"] = True
        cfgf["gate_follow_poll_s"] = 0.5
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfgf, f)
        held = {}
        tA = pin_slot("bootfb", held)               # occupies the (fallback) single slot
        res_fb = {}
        def second_fb():
            try:
                cc = post("/v1/chat/completions?case=json", {"model": "m"})
                rr = cc.getresponse()
                res_fb["status"] = rr.status
                res_fb["body"] = rr.read()
                cc.close()
            except Exception as e:
                res_fb["err"] = str(e)
        t_fb0 = time.monotonic()
        tB = threading.Thread(target=second_fb); tB.start()
        # Discriminator: fallback used static 1 -> the 2nd QUEUES (waits, only
        # expiry-forwards at gate_wait_s=1.0). It must still be waiting at
        # 0.65s (wrong fallback 2 would fast-path it done in ~0.05s).
        remain = 0.65 - (time.monotonic() - t_fb0)
        if remain > 0:
            time.sleep(remain)
        still_queued = tB.is_alive()                # not released inside the gate_wait_s window
        q_fb = (read_ext().get("gate") or {}).get("queued") or 0   # supplementary ext read
        #                                      (sampler-merged, may lag ~2.5s; the
        #                                      liveness reading above is the primary)
        HOLD_GATE.set()
        tB.join(timeout=10); tA.join(timeout=10)
        rec("gate:follow boot fallback to static max_inflight",
            still_queued,
            "2nd still waiting at 0.65s (gate_wait_s=1.0 stage value; fast-path would be done by now): %s; ext queued read=%s; static_fallback=1 stub_serving_fake=2 (broken status)"
            % (still_queued, q_fb))
        # cfgf STAYS for assertions (3)-(5) (same cfg per ticket); restored once at group end.

        # ---- T-2 (3) 判据③-5/③-9: limit tracks engine serving -------------
        # Same follow-ON cfg, but gate_wait_s raised to 8.0 so the queued 2nd
        # request stays queued while the 3rd fast-paths in on the new engine
        # value (static max_inflight stays 1; the future engine value is 2 ->
        # discriminating). Stub good/serving=1: the reader thread must wake and
        # poll; then serving flips to 2 and a third request must see limit 2
        # (ext gate.limit 1->2 = the monitor-page dynamisation behaviour proof).
        cfgf3 = dict(cfgf)
        cfgf3["gate_wait_s"] = 8.0
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfgf3, f)
        STATUS_MODE = "good"; STATUS_SERVING = 1
        h0_follow = status_hits()
        hpoll = None
        endp = time.monotonic() + 8.0        # stage-1 thread slept at default 5s: allow one full cycle
        while time.monotonic() < endp:
            if status_hits() > h0_follow:
                hpoll = status_hits()
                break
            time.sleep(0.05)
        held = {}
        tA = pin_slot("tracks1", held)                # slot pinned (limit=1 either way)
        res_tr2 = {}
        def second_tr():
            try:
                cc = post("/v1/chat/completions?case=json", {"model": "m"})
                rr = cc.getresponse()
                res_tr2["status"] = rr.status
                res_tr2["body"] = rr.read()
                cc.close()
            except Exception as e:
                res_tr2["err"] = str(e)
        tB = threading.Thread(target=second_tr); tB.start()
        g_q1 = wait_gate_fresh(lambda g: (g.get("queued") or 0) >= 1, timeout=6.0)
        lim1 = (g_q1 or {}).get("limit")
        STATUS_SERVING = 2
        h1_flip = status_hits()
        hpoll2 = None
        endp2 = time.monotonic() + 3.0                 # poll_s=0.5 -> two cycles fit easily
        while time.monotonic() < endp2:
            if status_hits() >= h1_flip + 2:
                hpoll2 = status_hits()
                break
            time.sleep(0.05)
        time.sleep(0.15)                               # settle margin: the last in-flight GET
        #                                      response must be parsed into _engine_reading
        res_tr3 = {}
        def third_tr():
            try:
                cc = post("/v1/chat/completions?case=json", {"model": "m"})
                rr = cc.getresponse()
                res_tr3["status"] = rr.status
                res_tr3["body"] = rr.read()
                cc.close()
            except Exception as e:
                res_tr3["err"] = str(e)
        tC = threading.Thread(target=third_tr); tC.start()
        g_tr = wait_gate(lambda g: g.get("limit") == 2, timeout=3.0)  # ext limit FOLLOWED engine 1->2
        lim2 = (g_tr or {}).get("limit")
        tC.join(timeout=15)                            # 3rd: real 200 (never refused)
        HOLD_GATE.set()                                # release the pinned hold
        tB.join(timeout=15); tA.join(timeout=15)
        want_tr = json.dumps(USAGE_TAIL).encode()
        rec("gate:follow limit tracks engine serving",
            hpoll is not None and hpoll2 is not None and lim1 == 1 and lim2 == 2
            and res_tr3.get("status") == 200 and res_tr3.get("body") == want_tr
            and res_tr2.get("status") == 200 and res_tr2.get("body") == want_tr,
            "hits %d->%d->%s (poll cycles) limit 1\u21922 (ext gate.limit=%s\u2192%s) 3rd status=%s 2nd status=%s"
            % (h0_follow, h1_flip, hpoll2, lim1, lim2, res_tr3.get("status"), res_tr2.get("status")))

        # ---- T-2 (4) 判据③-8: last-good value survives status loss ---------
        # _engine_reading=(2,...) carried over. Stub goes broken again; after
        # >=2 poll cycles the effective limit must STILL be the last good 2,
        # NOT the static fallback 1 (v3 discriminating read: ext gate.limit==2;
        # without it both states would show queued>=1 and could read false-green).
        STATUS_MODE = "broken"
        time.sleep(1.0)                                # >=2 poll cycles (poll_s=0.5)
        g_lg0 = read_ext().get("gate") or {}
        lim_lg0 = g_lg0.get("limit")
        held = {}
        tA = pin_slot("lg1", held)                     # last-good 2 -> two slots fillable
        infl_lg1 = (read_ext().get("gate") or {}).get("inflight")
        tB = hold_extra("lg2", held)
        settle_gate_inflight(2)
        infl_lg2 = (read_ext().get("gate") or {}).get("inflight")
        res_lg3 = {}
        t_lg3_start = time.monotonic()
        def third_lg():
            try:
                cc = post("/v1/chat/completions?case=json", {"model": "m"})
                rr = cc.getresponse()
                res_lg3["status"] = rr.status
                res_lg3["body"] = rr.read()
                cc.close()
            except Exception as e:
                res_lg3["err"] = str(e)
        tC = threading.Thread(target=third_lg); tC.start()
        # ext queued read widened for the sampler tick (~2.3s observed); the
        # primary discriminator is unchanged: liveness at >=0.65s into the wait
        # (gate_wait_s here is 8.0 via cfgf3, so expiry-forward is excluded).
        g_lgq = wait_gate_fresh(lambda g: (g.get("queued") or 0) >= 1, timeout=6.0)
        q_lg = (g_lgq or {}).get("queued") or 0
        early = 0.65 - (time.monotonic() - t_lg3_start)
        if early > 0:
            time.sleep(early)
        not_fast = tC.is_alive()                       # queued, NOT fast-pathed (no "all-open" fallback)
        t_queued_elapsed = time.monotonic() - t_lg3_start
        # post-pin ext read: every gate request pushes _last_limit, so this is
        # the discriminating reading (last-good -> 2 vs a cache-dropping bug
        # that falls back to static 1 would show 1 here and queue pin#2).
        lim_lg_post = (read_ext().get("gate") or {}).get("limit")
        HOLD_GATE.set()                                # one set wakes both waiting holds; drain all
        tA.join(timeout=15); tB.join(timeout=15); tC.join(timeout=15)
        HOLD_GATE.clear()                              # two waiters release on the first set; the
        #                                      redundant second set must not leak into later pins
        want_lg = json.dumps(USAGE_TAIL).encode()
        rec("gate:follow last-good on status loss",
            lim_lg0 == 2 and lim_lg_post == 2 and q_lg >= 1 and not_fast
            and res_lg3.get("status") == 200 and res_lg3.get("body") == want_lg
            and held.get("lg1", (None,))[0] == 200 and held.get("lg2", (None,))[0] == 200,
            "ext gate.limit=%s (pre-pin) / %s (post-pin; last-good 2 vs static fallback 1) 3rd queued=%s not_fast_within_0.6s=%s elapsed=%0.2fs final status=%s holds=%s,%s"
            % (lim_lg0, lim_lg_post, q_lg, not_fast, t_queued_elapsed, res_lg3.get("status"),
               held.get("lg1", (None,))[0], held.get("lg2", (None,))[0]))
        # ---- T-2 (5) 判据③-11: poll bypasses the gate, records nothing ------
        # Gate full with a queued chat request; the follow thread keeps polling
        # (hits grow) yet the queue never drains and the ledger gains nothing:
        # the status GET never passes the gate nor writes a ledger row.
        # gate_wait_s is raised to 8.0 (cfgf3) so the queued request stays
        # queued for the whole >=1.2s two-sample window (no expiry-forward).
        held = {}
        tA = pin_slot("byp1", held)
        tB = hold_extra("byp2", held)
        res_byp = {}
        def queued_byp():
            try:
                cc = post("/v1/chat/completions?case=json", {"model": "m"})
                rr = cc.getresponse()
                res_byp["status"] = rr.status
                rr.read(); cc.close()
            except Exception as e:
                res_byp["err"] = str(e)
        tC = threading.Thread(target=queued_byp); tC.start()
        wait_gate_fresh(lambda g: (g.get("queued") or 0) >= 1, timeout=6.0)
        hits_a, rows_a = status_hits(), len(ledger(tmp))
        time.sleep(1.2)                                # >=2 poll cycles while gate stays full
        hits_b, rows_b = status_hits(), len(ledger(tmp))
        still_queued_byp = tC.is_alive()               # polling never opened the gate
        HOLD_GATE.set(); HOLD_GATE.set()
        tC.join(timeout=15); tA.join(timeout=15); tB.join(timeout=15)
        HOLD_GATE.clear()                            # defensive re-arm: never leave the flag set
        #                                      for the next group's pins (one set can wake both stubs)
        rec("gate:follow poll bypasses gate and records nothing",
            hits_b > hits_a and rows_b == rows_a and still_queued_byp,
            "hits %d->%d (gate full, queue stays blocked) ledger_rows %d->%d (delta 0 == completed chat requests 0 in window; queued 3rd still pending: alive=%s; chat requests completed in window=0)"
            % (hits_a, hits_b, rows_a, rows_b, still_queued_byp))
        with open(cfg_path, "w", encoding="utf-8") as f:   # restore gate-stage cfg (T-3 self-restore)
            json.dump(cfg2, f)

        # ================================================================
        # rev11 T-4 anti-misjudge group (验收重心·人类 21:18 补令「第 3 路不会被
        # 误杀，一定有心跳机制通讯保活」). Shared cfg pinned per v4: gate_follow
        # false (fixed-value gate — this family tests queueing + heartbeat,
        # orthogonal to where limit comes from; mixed follow×queue state is
        # carried by T-2 (3) + the Gate-zero-change freeze), max_inflight 2
        # (= on-duty engine parallel), queue_beat_s 0.4, gate_wait_s 8.0.
        # Stub stays "broken" from T-2 (5) — with follow off it is never polled.
        # ================================================================
        cfgt = dict(cfg2)
        cfgt["gate_follow"] = False
        cfgt["max_inflight"] = 2
        cfgt["queue_beat_s"] = 0.4
        cfgt["gate_wait_s"] = 8.0
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfgt, f)
        STATUS_MODE = "good"; STATUS_SERVING = 2     # v4 pinned stub state (explicit)
        time.sleep(1.2)                              # >=2 cycles: the thread must have RE-read
        #                                      cfgt (follow off) before the baseline is pinned,
        #                                      so a follow:true-era in-flight poll can't race it
        t4_hits0 = status_hits()                     # v4 group-head hits baseline

        # ---- T-4 A1 判据③-13: 3rd stream survives a full queue, heartbeats ----
        held = {}
        tA = pin_slot("a1h1", held)
        tB = hold_extra("a1h2", held)                # both slots pinned (limit=2)
        box = {}
        tR = fire_raw_stream("/v1/chat/completions?case=sse",
                             {"model": "m", "stream": True}, KEY_3RD, box)
        gq = wait_gate(lambda g: (g.get("queued") or 0) >= 1, timeout=3.0)
        endp = time.monotonic() + 3.0                # receive >=2 : ping frames BEFORE releasing
        while time.monotonic() < endp:               # (>=1 full beat waited => queue_wait_ms >= 400)
            if len(box.get("pings") or []) >= 2:
                break
            time.sleep(0.05)
        HOLD_GATE.set()                              # one set wakes both stubs; the slot frees
        #                                      -> 3rd gets the REAL stream (Event self-clears)
        tR.join(timeout=25)
        tA.join(timeout=15); tB.join(timeout=15)
        HOLD_GATE.clear()                            # defensive re-arm for the next group's pins
        st1 = box.get("st") or {}
        tp = box.get("pings") or []
        first_ok = bool(tp) and tp[0] <= 0.8         # first frame <= queue_beat_s(0.4)+0.4 tol
        gaps_ok = all(tp[i] - tp[i - 1] <= 0.8 for i in range(1, len(tp)))
        raw1 = st1.get("raw") or b""
        row1 = find_row(tmp, KEY_3RD_FP, timeout=8.0)
        rec("gate:3rd stream survives full queue with heartbeats",
            len(tp) >= 2 and first_ok and gaps_ok
            and st1.get("status_lines") == 1 and not st1.get("reset") and st1.get("terminal_zero")
            and b"HTTP/1.1 429" not in raw1 and b"HTTP/1.1 409" not in raw1 and b"HTTP/1.1 502" not in raw1
            and st1.get("data_frames") == 8 and st1.get("done")
            and row1 is not None and row1.get("queue_wait_ms", -1) >= 400 and "error" not in row1,
            "t_pings=[%s] first_ping=%ss (<=0.8) data_frames=%s DONE=%s status_lines=%s refused(429/409/502)=%s queue_wait_ms=%s row_error=%s queued_first=%s"
            % (",".join("%0.2f" % x for x in tp), ("%0.2f" % tp[0]) if tp else "never",
               st1.get("data_frames"), st1.get("done"), st1.get("status_lines"),
               any(s in raw1 for s in (b"HTTP/1.1 429", b"HTTP/1.1 409", b"HTTP/1.1 502")),
               row1.get("queue_wait_ms") if row1 else None,
               "error" in (row1 or {}), (gq or {}).get("queued")))

        # ---- T-4 A2 判据③-14: in-flight pair rate unaffected by queued 3rd ----
        box0 = {}
        t0_ = fire_raw_stream("/v1/chat/completions?case=sse",
                              {"model": "m", "stream": True}, KEY, box0)
        t0_.join(timeout=25)
        t_base = box0.get("elapsed") or 0.0          # uncontended single stream baseline
        bA, bB = {}, {}
        tA = fire_raw_stream("/v1/chat/completions?case=sse",
                             {"model": "m", "stream": True, "i": 1}, KEY, bA)
        tB = fire_raw_stream("/v1/chat/completions?case=sse",
                             {"model": "m", "stream": True, "i": 2}, KEY, bB)
        # Both streams run ~1.2s (6x0.2s frames + tail). The /ext.json inflight
        # reading lags the sampler tick (~1-2.3s) so it cannot gate the 3rd's
        # firing — timing does: at 0.35s both are verifiably in the gate
        # (limit=2, streams not finished until ~1.2s), so the 3rd must queue.
        time.sleep(0.35)
        boxC = {}
        tC = fire_raw_stream("/v1/chat/completions?case=sse",
                             {"model": "m", "stream": True, "i": 3}, KEY, boxC)
        endp = time.monotonic() + 3.0                # 3rd queued >= 1 live heartbeat
        while time.monotonic() < endp:
            if len(boxC.get("pings") or []) >= 1:
                break
            time.sleep(0.05)
        queued_pings_c = len(boxC.get("pings") or [])
        for t in (tA, tB, tC):
            t.join(timeout=25)                       # in-flight finish -> slot hands over -> 3rd runs
        stA, stB, stC = bA.get("st") or {}, bB.get("st") or {}, boxC.get("st") or {}
        eA, eB = bA.get("elapsed") or 99.0, bB.get("elapsed") or 99.0
        rec("gate:in-flight pair rate unaffected by queued 3rd",
            stA.get("data_frames") == 8 and stA.get("done")
            and stB.get("data_frames") == 8 and stB.get("done")
            and eA <= t_base + 1.0 and eB <= t_base + 1.0
            and (stC.get("head") or b"").startswith(b"HTTP/1.1 200") and stC.get("data_frames") == 8
            and stC.get("done") and queued_pings_c >= 1,
            "t_base=%0.2fs in-flight elapsed=%0.2fs,%0.2fs (each <= t_base+1.0) 3rd heartbeat frames while queued=%s (live : ping => queued behind the pair) final_3rd_head=%r 3rd data_frames=%s DONE=%s"
            % (t_base, eA, eB, queued_pings_c,
               (stC.get("head") or b"")[:14], stC.get("data_frames"), stC.get("done")))

        # ---- T-4 A3 判据③-15: queued client drops mid-heartbeat -> slot clean ----
        held = {}
        tA = pin_slot("a3h1", held)
        tB = hold_extra("a3h2", held)
        box = {}
        tR = fire_raw_stream("/v1/chat/completions?case=sse",
                             {"model": "m", "stream": True}, KEY_3DROP, box)
        endp = time.monotonic() + 3.0
        while time.monotonic() < endp:               # >=1 heartbeat frame arrives first
            if len(box.get("pings") or []) >= 1:
                break
            time.sleep(0.05)
        pings_at_drop = len(box.get("pings") or [])
        s_drop = box.get("sock")
        try:                                         # forceful client-side disconnect
            s_drop.shutdown(socket.SHUT_RDWR)        # unblock the reader's pending recv first
        except OSError:
            pass
        try:
            s_drop.close()
        except OSError:
            pass
        tR.join(timeout=10)                          # the drop must not crash anything
        HOLD_GATE.set()                              # one set wakes both waiting stubs: the two
        #                                      holds proceed as normal (flag self-clears on wake)
        tA.join(timeout=15); tB.join(timeout=15)
        HOLD_GATE.clear()                            # defensive re-arm before the next group's pins
        g_fin = wait_gate_fresh(lambda g: (g.get("inflight") or 0) == 0 and (g.get("queued") or 0) == 0,
                                timeout=6.0)          # no ghost slot (window widened for the
        #                                      sampler tick; pushes ride the drain's acquire/release)
        rowd = find_row(tmp, KEY_3DROP_FP, timeout=8.0)
        rec("gate:queued drop after heartbeat releases slot clean",
            pings_at_drop >= 1
            and held.get("a3h1", (None,))[0] == 200 and held.get("a3h2", (None,))[0] == 200
            and g_fin is not None and g_fin.get("inflight") == 0 and g_fin.get("queued") == 0
            and rowd is not None,                    # its ledger row lands (honestly recorded)
            "pings_at_drop=%s holds_status=%s,%s final inflight=%s queued=%s dropped_row_present=%s (error_field=%s)"
            % (pings_at_drop, held.get("a3h1", (None,))[0], held.get("a3h2", (None,))[0],
               (g_fin or {}).get("inflight"), (g_fin or {}).get("queued"),
               rowd is not None, (rowd or {}).get("error")))

        # ---- T-4 A4 判据③-16: 3rd non-stream waits out gate_wait_s, forwarded ----
        # Full-queue silence is a protocol property (README §9 item 10) — bytes
        # are not asserted between beats. To keep the suite quick this assertion
        # alone lowers gate_wait_s to 1.0 (self-restores to 8.0 right after).
        cfgt4 = dict(cfgt)
        cfgt4["gate_wait_s"] = 1.0
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfgt4, f)
        held = {}
        tA = pin_slot("a4h1", held)
        tB = hold_extra("a4h2", held)                # both slots pinned, holds never released
        t0 = time.monotonic()
        c = post("/v1/chat/completions?case=json", {"model": "m"})
        res4 = {}
        def read4():
            try:
                r4 = c.getresponse()
                res4["status"] = r4.status
                res4["body"] = r4.read()
            except Exception as e:
                res4["err"] = str(e)
        tR4 = threading.Thread(target=read4, daemon=True)
        tR4.start()
        time.sleep(0.6)                              # observation: NOT forwarded early
        no_early_forward = not res4                  # while both slots held: still inside the queue
        tR4.join(timeout=15)
        body4 = res4.get("body")
        waited4 = time.monotonic() - t0              # waited ~gate_wait_s=1.0, then forwarded
        HOLD_GATE.set()                              # drain the holds (one set wakes both stubs)
        tA.join(timeout=15); tB.join(timeout=15)
        rec("gate:3rd non-stream waits out gate_wait_s and forwards",
            waited4 >= 0.9 and res4.get("status") == 200 and res4.get("status") not in (429, 409, 502)
            and body4 == json.dumps(USAGE_TAIL).encode(),
            "waited=%0.2fs (gate_wait_s lowered to 1.0 for this assertion only, then restored) no_early_forward(0.6s mark)=%s final status=%s refused=%s body==real upstream response=%s"
            % (waited4, no_early_forward, res4.get("status"), res4.get("status") in (429, 409, 502),
               body4 == json.dumps(USAGE_TAIL).encode()))
        with open(cfg_path, "w", encoding="utf-8") as f:   # T-4 group-end self-restore (rev10a discipline)
            json.dump(cfg2, f)
        t4_hits1 = status_hits()                     # whole family ran with follow OFF: zero new polls
        # sanity detail line for the v4 pinned-state (non-asserting observation)
        assert t4_hits1 == t4_hits0, "T-4 family must not poll /v1/status (gate_follow false)"

        bad = [n for n, ok, _ in RESULTS if not ok]
        print("\n%d/%d PASS" % (len(RESULTS) - len(bad), len(RESULTS)))
        if bad:
            print("FAILED:", ", ".join(bad))
        return 1 if bad else 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        upstream.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
