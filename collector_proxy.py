#!/usr/bin/env python3
r"""token-ledger · proxy-mode collector: a local pass-through reverse proxy for OpenAI-compatible
(/v1/chat/completions) and Anthropic-compatible (/v1/messages) backends. Every response's
`usage` object is authoritative (the provider counts it, so there is no log-parsing distortion),
and request arrival is the timestamp. Stdlib only.

  python collector_proxy.py --config <out_dir>/config.json

config keys used: out_dir, lock_port, listen ("127.0.0.1:8787"), upstream (https://api...),
upstream_key_env (env var holding the provider key; never stored on disk).

The client changes ONLY its base_url to the listen address; the proxy forwards to `upstream`
unchanged (adding Authorization from upstream_key_env when the client sent none) and writes one
canonical JSONL line per completed request, including the caller's IP (`ip`, plus `fwd` when an
X-Forwarded-For header is present).

RELAY CONTRACT (do not regress):
  1. A forwarder must never change the upstream's response rhythm. SSE responses go out as
     HTTP/1.1 chunks with headers sent immediately and every upstream chunk flushed as it
     arrives, so a long generation never looks like a dead connection to an idle-read-timeout
     gateway. The full body is accumulated only as a private copy for the final usage chunk
     (OpenAI: last data: chunk; Anthropic: message_start / message_delta), so byte-preserving
     relay costs no accounting accuracy.
  2. Non-stream responses still wait for the whole body because their Content-Length must be
     known before the headers go out; the engine itself emits nothing while it generates, so
     no forwarder can make that path incremental without changing the response. This is a
     protocol property, NOT the buffering bug that was fixed on 2026-11-09. The NAS read
     timeout has been raised on the device side to cover this path.
  3. All upstream response headers (Content-Encoding, CORS, ...) are relayed; only hop-by-hop
     and framing headers are dropped. Request headers are relayed the same way, so x-api-key /
     anthropic-version / Accept survive on every endpoint, not just the two chat endpoints.
  4. Once response headers have been sent, NO second HTTP response may be written to the same
     socket. A mid-stream upstream failure closes the connection and records an error instead.

Non-2xx responses are recorded with "error": <status> and zero tokens so failed spend attempts
stay visible. A body larger than 32 MiB stops being accumulated (relay continues untouched)
and the ledger row is marked body_truncated.

Since 2026-11-09 this process ALSO owns the daily-report trigger (formerly scheduler.py): a
daemon thread runs daily_report.run_daily(cfg) once at boot and once per new day, so the ledger
is a single resident process. The standalone scheduler.py is kept for manual use only.

Also since 2026-11-09 it owns the hardware monitor (formerly a separate 127.0.0.1:8089
process). Since 2026-11-16 the monitor is a fully self-owned page: /monitor
(monitor.html + /monitor.js, data from /ext.json) is served here on the SAME
origin as the console, so teammates see every GPU (including TCC cards Task
Manager cannot show), RAM, disks and network adapters at http://<host>:8080/monitor.
GPU cards and waveform history bind by the card's UUID, never by the drifting
nvidia-smi slot index. This process NEVER writes to a web page it does not own:
the old script-injection watcher is removed. /ext.js is kept only as a retired
shim for pages that still carry the old line. Local routes never reach the
upstream and never create ledger rows.
"""
import gzip
import hashlib
import json
import os
import socket
import sys
import threading
import time
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import request as urlreq
from urllib import error as urlerr

# The monitor extension lives next to this file. Import failure must never stop
# accounting: the proxy simply keeps forwarding everything to the engine.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import monitor_ext as _monitor_ext
except Exception:
    _monitor_ext = None

CANON_INT = ("prompt", "cached", "new_prompt", "gen")
BODY_ACCUM_CAP = 32 * 1024 * 1024        # stop keeping the private copy past 32 MiB; relay is unaffected
_HOP_HEADERS = {
    "host", "content-length", "transfer-encoding", "connection", "keep-alive",
    "upgrade", "trailer", "te", "proxy-authenticate", "proxy-authorization",
}


def client_ip(handler):
    """Caller address for the ledger. IPv4 peers on a dual-stack IPv6 listener
    arrive as ::ffff:a.b.c.d; store the plain IPv4 form so one machine is one label."""
    raw = (handler.client_address or ("", 0))[0]
    return raw[7:] if raw.startswith("::ffff:") else raw


def load_config(path):
    # Portable paths: @here / @pkg / ~ / relative paths are resolved against
    # the config file's own directory, so one config works on any OS.
    from paths import load_config as portable_load_config
    return portable_load_config(path)


class Recorder:
    def __init__(self, out_dir):
        self.dir = out_dir
        self.lock = threading.Lock()
        self.day = None
        self.f = None

    def write(self, rec):
        day = (rec.get("ts") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))[:10]
        with self.lock:
            if day != self.day:
                if self.f is not None:
                    try:
                        self.f.close()
                    except OSError:
                        pass
                self.f = open(os.path.join(self.dir, f"requests-{day}.jsonl"), "a", encoding="utf-8", buffering=1)
                self.day = day
            self.f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def key_identity(headers, cfg):
    """Return (tag, fp): fp is the 8-hex SHA-256 prefix of the raw API key
    (or "none"); tag is the human label from key_labels, else fp itself.
    The ledger stores BOTH so a future label/fingerprint collision stays
    auditable and historical rows can still be split.
    """
    raw = headers.get("Authorization") or headers.get("x-api-key") or ""
    raw = raw.strip()
    # RFC 7235 auth-scheme is case-insensitive: "bearer"/"BEARER" must not
    # turn one person's key into a second, unlabelled identity.
    if raw[:7].lower() == "bearer ":
        raw = raw[7:].strip()
    if not raw:
        return ("none", "none")
    fp = hashlib.sha256(raw.encode()).hexdigest()[:8]
    return ((cfg.get("key_labels") or {}).get(fp, fp), fp)


def key_tag(headers, cfg):
    """Backward-compatible wrapper: just the display tag."""
    return key_identity(headers, cfg)[0]


def usage_from_openai(obj):
    u = obj.get("usage") or {}
    details = u.get("prompt_tokens_details") or {}
    return {"prompt": u.get("prompt_tokens", 0), "cached": details.get("cached_tokens", 0),
            "gen": u.get("completion_tokens", 0), "model": obj.get("model", "")}


def usage_from_anthropic(obj):
    u = obj.get("usage") or {}
    return {"prompt": u.get("input_tokens", 0), "cached": u.get("cache_read_input_tokens", 0),
            "gen": u.get("output_tokens", 0), "model": obj.get("model", "")}


def usage_from_sse(body, kind):
    """Scan an SSE body and MERGE every usage it carries. Anthropic splits usage across two
    events (message_start: input+cache, message_delta: output); OpenAI streams usage only in
    the final chunk. A nonzero field from any event wins over a zero from another."""
    out = {"prompt": 0, "cached": 0, "gen": 0, "model": ""}
    for raw in body.split(b"\n"):
        line = raw.strip()
        if not line.startswith(b"data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == b"[DONE]":
            continue
        try:
            obj = json.loads(payload)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        if kind == "anthropic":
            src = (obj.get("usage") or (obj.get("message") or {}).get("usage")) or {}
            got = {"prompt": src.get("input_tokens", 0), "cached": src.get("cache_read_input_tokens", 0),
                   "gen": src.get("output_tokens", 0), "model": obj.get("model", "") or (obj.get("message") or {}).get("model", "")}
        else:
            got = usage_from_openai(obj)
        for k in ("prompt", "cached", "gen"):
            if got.get(k):
                out[k] = got[k]
        if got.get("model"):
            out["model"] = got["model"]
        met = obj.get("metrics")          # vLLM --enable-per-request-metrics (engine-side timing)
        if isinstance(met, dict):
            if met.get("tokens_per_second"):
                out["engine_tps"] = met["tokens_per_second"]
            if met.get("generation_time_ms"):
                out["engine_gen_ms"] = met["generation_time_ms"]
    return out


class Handler(BaseHTTPRequestHandler):
    # HTTP/1.1 is required for Transfer-Encoding: chunked, which is how SSE is
    # relayed without buffering. Every non-chunked branch sends an exact
    # Content-Length, so keep-alive framing stays well-formed.
    protocol_version = "HTTP/1.1"
    recorder = None
    cfg = None

    def log_message(self, *a):            # silence default stderr logging
        pass

    # ---- shared relay helpers -------------------------------------------------

    @staticmethod
    def _clean_headers(source, skip=()):
        """Drop hop-by-hop / framing headers; normalize key spelling so later
        lookups such as headers['Authorization'] behave predictably."""
        out = {}
        for k, v in source.items():
            lk = k.lower()
            if lk in _HOP_HEADERS or lk in skip:
                continue
            out["-".join(p.capitalize() for p in k.split("-"))] = v
        return out

    def _forward_headers(self):
        """All client headers except hop-by-hop ones. Never send an empty
        Authorization when the client sent none: some engines reject an empty
        credential even in no-key mode."""
        h = self._clean_headers(self.headers)
        if not any(k.lower() == "content-type" for k in h):
            h["Content-Type"] = "application/json"
        return h

    def _read_body(self):
        """Honor both Content-Length and chunked request bodies. A client that
        sends TE: chunked used to be read as zero bytes, silently losing the
        whole request and desynchronizing keep-alive."""
        te = (self.headers.get("Transfer-Encoding") or "").lower()
        if "chunked" in te:
            parts = []
            while True:
                line = self.rfile.readline(65536)
                if not line:
                    break
                try:
                    size = int(line.split(b";", 1)[0].strip(), 16)
                except ValueError:
                    break
                if size == 0:
                    while True:                      # consume trailers up to the blank line
                        t = self.rfile.readline(65536)
                        if not t or t in (b"\r\n", b"\n"):
                            break
                    break
                buf = b""
                while len(buf) < size:
                    piece = self.rfile.read(size - len(buf))
                    if not piece:
                        break
                    buf += piece
                parts.append(buf)
                self.rfile.read(2)                   # trailing CRLF
            return b"".join(parts)
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            n = 0
        return self.rfile.read(n) if n > 0 else b""

    def _send_fixed(self, status, source, data, extra=None):
        """Send a complete response with an exact Content-Length, relaying
        upstream headers (Content-Encoding, CORS, ...) verbatim."""
        self.send_response(status)
        sent = set()
        for k, v in self._clean_headers(source).items():
            self.send_header(k, v)
            sent.add(k.lower())
        if "content-type" not in sent:
            self.send_header("Content-Type", "application/json")
        for k, v in (extra or {}).items():
            if v and k.lower() not in sent:
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _start_chunked(self, status, source):
        """Send response headers IMMEDIATELY, before any body byte exists."""
        self.send_response(status)
        sent = set()
        for k, v in self._clean_headers(source, skip={"cache-control"}).items():
            self.send_header(k, v)
            sent.add(k.lower())
        if "content-type" not in sent:
            self.send_header("Content-Type", "application/json")
        if "cache-control" not in sent:
            self.send_header("Cache-Control", "no-cache, no-transform")
        if "x-accel-buffering" not in sent:
            self.send_header("X-Accel-Buffering", "no")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

    def _pump(self, resp, keep_body):
        """Relay every upstream chunk as it arrives. Returns
        (private_body_copy, client_still_connected, body_truncated).
        If the client disconnects we keep draining upstream so the final usage
        chunk is still accounted for."""
        parts, total, truncated, client_ok = [], 0, False, True
        while True:
            chunk = resp.read1(65536)
            if not chunk:
                break
            if keep_body and not truncated:
                if total + len(chunk) <= BODY_ACCUM_CAP:
                    parts.append(chunk)
                    total += len(chunk)
                else:
                    truncated = True
                    parts = []
            if client_ok:
                try:
                    frame = ("%x\r\n" % len(chunk)).encode("ascii") + chunk + b"\r\n"
                    self.wfile.write(frame)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    client_ok = False
                    self.close_connection = True
        if client_ok:
            try:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except OSError:
                client_ok = False
                self.close_connection = True
        body = b"".join(parts) if (keep_body and not truncated) else b""
        return body, client_ok, truncated

    # ---- endpoints ------------------------------------------------------------

    def _pass_post(self, body):           # non-chat endpoints (stop/unload/images/...): relay, no ledger row
        req = urlreq.Request(self.cfg["upstream"].rstrip("/") + self.path, data=body,
                             headers=self._forward_headers(), method="POST")
        responded = False
        try:
            with urlreq.urlopen(req, timeout=1800) as resp:
                ctype = resp.headers.get("Content-Type", "application/json")
                if "event-stream" in ctype.lower() and hasattr(resp, "read1"):
                    self._start_chunked(resp.status, resp.headers)
                    responded = True
                    self._pump(resp, False)
                else:
                    data = resp.read()
                    responded = True
                    self._send_fixed(resp.status, resp.headers, data)
        except urlerr.HTTPError as e:
            try:
                data = e.read() or b""
            except Exception:
                data = b""
            if not responded:
                self._send_fixed(e.code, e.headers, data)
            else:
                self.close_connection = True
        except Exception as e:
            if responded:
                self.close_connection = True     # never append a 2nd HTTP response to a live stream
                return
            data = json.dumps({"error": {"message": f"{type(e).__name__}: {e}"}}).encode()
            self._send_fixed(502, {}, data)

    def do_POST(self):
        cfg = self.cfg
        path = self.path.split("?", 1)[0]
        body = self._read_body()
        if path not in ("/v1/chat/completions", "/v1/messages"):
            return self._pass_post(body)
        kind = "anthropic" if path.startswith("/v1/messages") else "openai"
        t0 = time.monotonic()
        req_obj = {}
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):         # a JSON array/string must not crash .get() below
                req_obj = parsed
        except (ValueError, TypeError):
            pass
        up = cfg["upstream"].rstrip("/") + self.path
        headers = self._forward_headers()
        key = os.environ.get(cfg.get("upstream_key_env", ""), "")
        auth = self.headers.get("Authorization")
        if auth:
            headers["Authorization"] = auth
        elif key and kind == "openai":
            headers["Authorization"] = f"Bearer {key}"
        elif key and kind == "anthropic":
            headers["x-api-key"] = key
        if kind == "anthropic":
            headers.setdefault("Anthropic-Version", self.headers.get("anthropic-version", "2023-06-01"))
        # vLLM/SGLang/Ollama do NOT emit usage on a stream unless the client asks for it
        # (stream_options.include_usage). Without this the whole request is recorded as 0 tokens,
        # silently. Anthropic always reports usage in message_start/message_delta, so it needs nothing.
        if cfg.get("force_include_usage") and kind == "openai" and req_obj.get("stream") is True:
            opts = req_obj.get("stream_options")
            opts = dict(opts) if isinstance(opts, dict) else {}
            opts["include_usage"] = True
            req_obj = dict(req_obj)
            req_obj["stream_options"] = opts
            body = json.dumps(req_obj).encode()
        req = urlreq.Request(up, data=body, headers=headers, method="POST")
        tag, fp = key_identity(self.headers, cfg)
        rec = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "src": "proxy",
               "model": req_obj.get("model", ""), "key": tag, "fp": fp,
               "ip": client_ip(self)}
        fwd = self.headers.get("X-Forwarded-For")
        if fwd:
            rec["fwd"] = fwd.split(",", 1)[0].strip()
        responded = False                     # once headers are out, no second response is allowed
        truncated = False
        try:
            with urlreq.urlopen(req, timeout=1800) as resp:
                ctype = resp.headers.get("Content-Type", "application/json")
                is_sse = (("event-stream" in ctype.lower()
                           or req_obj.get("stream") is True)
                          and hasattr(resp, "read1"))
                if is_sse:
                    self._start_chunked(resp.status, resp.headers)
                    responded = True
                    data, client_ok, truncated = self._pump(resp, True)
                else:
                    data = resp.read()
                    responded = True
                    self._send_fixed(resp.status, resp.headers, data)
                if resp.status == 200:
                    # Relay bytes stay untouched; only the private accounting copy
                    # is decompressed. A gzip upstream must not silently record 0 tokens.
                    parse_body = data
                    if "gzip" in (resp.headers.get("Content-Encoding") or "").lower():
                        try:
                            parse_body = gzip.decompress(data)
                        except (OSError, ValueError):
                            pass
                    if "event-stream" in ctype.lower() or parse_body.lstrip().startswith(b"event:"):
                        got = usage_from_sse(parse_body, kind)
                    else:
                        got = {}
                        try:
                            obj = json.loads(parse_body)
                            if isinstance(obj, dict):
                                got = usage_from_anthropic(obj) if kind == "anthropic" else usage_from_openai(obj)
                                met = obj.get("metrics")
                                if isinstance(met, dict):
                                    got["engine_tps"] = met.get("tokens_per_second")
                                    got["engine_gen_ms"] = met.get("generation_time_ms")
                        except ValueError:
                            pass
                    for k in ("prompt", "cached", "gen"):
                        rec[k] = got.get(k, 0)
                    for k in ("engine_tps", "engine_gen_ms"):   # vLLM --enable-per-request-metrics
                        if got.get(k):
                            rec[k] = got[k]
                    if got.get("model"):
                        rec["model"] = got["model"]
                else:
                    rec["error"] = resp.status
        except urlerr.HTTPError as e:
            rec["error"] = e.code
            if responded:
                self.close_connection = True
            else:
                try:
                    data = e.read() or b""
                except Exception:
                    data = b""
                self._send_fixed(e.code, e.headers, data)
        except Exception as e:            # record the failure, then surface a 502 if nothing was sent yet
            rec["error"] = f"{type(e).__name__}: {e}"[:120]
            if responded:
                self.close_connection = True
            else:
                data = json.dumps({"error": {"message": rec["error"]}}).encode()
                self._send_fixed(502, {}, data)
        if truncated:
            rec["body_truncated"] = True
        rec["gen_ms"] = int((time.monotonic() - t0) * 1000)
        rec["new_prompt"] = rec.get("prompt", 0) - rec.get("cached", 0)
        if rec.get("gen") and rec["gen_ms"]:
            rec["decode_tok_s"] = round(rec["gen"] / (rec["gen_ms"] / 1000), 1)
        for k in CANON_INT:
            rec.setdefault(k, 0)
        self.recorder.write(rec)

    def do_GET(self):                     # pass-through: /v1/models, console pages, /metrics, ...
        # Local monitor routes are answered here and never forwarded. "/" is NOT
        # one of them: on 8080 it is the Strata console itself.
        local = None
        if _monitor_ext is not None:
            try:
                local = _monitor_ext.answer(self.path.split("?", 1)[0])
            except Exception:
                local = None
        if local is not None:
            body, ctype = local
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        cfg = self.cfg
        req = urlreq.Request(cfg["upstream"].rstrip("/") + self.path, method="GET",
                             headers=self._forward_headers())
        # forward the browser's credentials so engine-served pages (/metrics, #monitor) keep working
        auth = self.headers.get("Authorization")
        if not auth:
            auth = os.environ.get(cfg.get("upstream_key_env", ""), "")
            if auth:
                auth = f"Bearer {auth}"
        if auth:
            req.add_header("Authorization", auth)
        responded = False
        try:
            with urlreq.urlopen(req, timeout=30) as resp:
                data = resp.read()
                responded = True
                self._send_fixed(resp.status, resp.headers, data)
        except urlerr.HTTPError as e:      # pass real status through (401 etc.), don't mask as 502
            try:
                data = e.read() or b""
            except Exception:
                data = b""
            responded = True
            self._send_fixed(e.code, e.headers, data)
        except Exception:
            if responded:
                # Headers are already on the wire (client dropped mid-write):
                # appending a 502 would corrupt the stream. Close instead.
                self.close_connection = True
                return
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()


def _append_line(path, line):
    """Append one UTF-8 line to a log file; never propagate IO errors to the caller."""
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _fire_daily(daily_report, cfg, runlog, why):
    """Run the idempotent daily report once and log the outcome.

    Log format is byte-for-byte compatible with the legacy scheduler.py so any
    existing consumer of daily-report.log keeps working. A failing fire is
    recorded and swallowed, so it can never take the HTTP server down.
    """
    try:
        daily_report.run_daily(cfg)
        _append_line(runlog, f"[{datetime.now():%Y-%m-%d %H:%M:%S}] scheduler fired ({why})")
    except Exception:
        _append_line(runlog, f"[{datetime.now():%Y-%m-%d %H:%M:%S}] scheduler ERROR: {traceback.format_exc()}")


def _report_scheduler_loop(cfg, out_dir):
    """Daemon-thread body replacing the legacy resident scheduler.py process.

    Fires one immediate "boot check" catch-up on start, then wakes about every
    20 s and fires again after crossing into a new calendar day at/after
    report_hour:report_minute. daily_report.run_daily(cfg) is idempotent, so a
    manually started legacy scheduler.py cannot produce duplicate reports and no
    extra lock port (lock_port + 1) is claimed here. Any exception is logged and
    swallowed so neither this thread nor the HTTP server can die from a bad fire.
    """
    rh = int(cfg.get("report_hour", 0))
    rm = int(cfg.get("report_minute", 0))
    runlog = os.path.join(out_dir, "daily-report.log")
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    boot_done = False
    today = datetime.now().strftime("%Y-%m-%d")
    while True:
        try:
            import daily_report  # cached after the first pass; lives next to this file
            now = datetime.now()
            if not boot_done:
                _fire_daily(daily_report, cfg, runlog, "boot check")
                boot_done = True
                today = now.strftime("%Y-%m-%d")
            else:
                day = now.strftime("%Y-%m-%d")
                if day != today and (now.hour, now.minute) >= (rh, rm):
                    _fire_daily(daily_report, cfg, runlog, f"new day {day}")
                    today = day
        except Exception:
            _append_line(runlog,
                         f"[{datetime.now():%Y-%m-%d %H:%M:%S}] scheduler loop ERROR: {traceback.format_exc()}")
        time.sleep(20)


def main():
    if "--fp" in sys.argv:                      # print the 8-hex label for a key (fills key_labels)
        print(hashlib.sha256(sys.argv[sys.argv.index("--fp") + 1].encode()).hexdigest()[:8])
        return
    if "--config" not in sys.argv:
        sys.exit("usage: collector_proxy.py --config <out_dir>/config.json")
    cfg = load_config(sys.argv[sys.argv.index("--config") + 1])
    out = cfg["out_dir"]
    os.makedirs(out, exist_ok=True)
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", int(cfg.get("lock_port", 43177))))
    except OSError:
        print("[proxy] another proxy already runs, nothing to do")
        return
    listen = cfg.get("listen", "127.0.0.1:8787")
    # rsplit, not partition: an IPv6 listen host like "::" or "2408::1" contains colons
    host, _, port = listen.rpartition(":")
    host = host or "0.0.0.0"
    Handler.cfg = cfg
    Handler.recorder = Recorder(out)

    class _Server(ThreadingHTTPServer):
        # Default backlog is 5; at 11:18 the engine alone had 5 in-flight
        # requests, so a burst could make the OS queue/refuse team connections.
        request_queue_size = 128
        # BUGFIX (2026-11-16, 000 deploy): socketserver creates the socket in
        # __init__ BEFORE server_bind() runs, so flipping address_family inside
        # server_bind() is too late — the socket was already AF_INET and
        # bind(('::', port)) dies with gaierror 11001. Pick the family as a
        # class attribute BEFORE instantiation instead.
        # "::" or "::1" -> AF_INET6; the default dual-stack socket then accepts
        # IPv4 too, so one listener serves both families (user runs IPv4+IPv6).
        address_family = socket.AF_INET6 if ":" in host else socket.AF_INET
        def server_bind(self):
            if self.address_family == socket.AF_INET6:
                try:
                    self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                except OSError:
                    pass
            super().server_bind()

    srv = _Server((host, int(port)), Handler)
    _append_line(os.path.join(out, "ledger-service.log"),
                 f"[{datetime.now():%Y-%m-%d %H:%M:%S}] ledger service started; "
                 f"listen={listen}; upstream={cfg['upstream']}; pid={os.getpid()}; "
                 "daily report merged into this process (daemon thread)")
    # Daily trigger now lives here (formerly the separate scheduler.py process).
    # daemon=True: it never blocks serve_forever() nor interpreter shutdown.
    reporter = threading.Thread(target=_report_scheduler_loop, args=(cfg, out),
                                name="ledger-daily-report", daemon=True)
    reporter.start()
    # Hardware monitor (formerly a separate 8089 process) is two more daemon
    # threads in this same process. A failure here cannot stop the ledger.
    monitor_on = False
    if _monitor_ext is not None:
        try:
            monitor_on = _monitor_ext.start(cfg) is not None
        except Exception:
            monitor_on = False
    print(f"[proxy] {listen} -> {cfg['upstream']}  records in {out}")
    print("[proxy] daily report scheduler merged in daemon thread (single resident process)")
    print(f"[proxy] hardware monitor merged: {'on (open /monitor; /ext.json feeds it)' if monitor_on else 'unavailable'}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
