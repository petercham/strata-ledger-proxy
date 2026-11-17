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
        with SEEN_LOCK:
            SEEN.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()},
                         "body": body})
        case = self._case(self.path)
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


def main():
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
