#!/usr/bin/env python3
r"""token-ledger · log-mode collector: tail a backend log, parse each finished-request line and
event line with the profile's named-group regexes, stamp the arrival time, append one JSONL line
per calendar day. Stdlib only.

  python collector_log.py --config <out_dir>/config.json

config keys used: out_dir, lock_port, log_path_file (optional pointer file whose content is the
current log path), log_fallback, profile {request: regex, events: [{kind, regex}]}.
Single instance: a bind on 127.0.0.1:lock_port is the "already running" flag.
Offset file (out_dir/collector.offset) replays what arrived while the collector was down;
those replayed lines get ts=null and are attributed to the day the offset was last written.
"""
import json
import os
import re
import socket
import sys
import time
from datetime import datetime

CANON = {"prompt": int, "cached": int, "new_prompt": int, "gen": int, "gen_ms": int,
         "gen_ms_s": float, "decode_tok_s": float, "prefill_tok_s": float}
# gen_ms_s exists because backends disagree on the unit: Strata prints milliseconds, SGLang's
# e2e_latency is SECONDS (float). A profile maps whichever it has; gen_ms_s is converted below.


def load_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["_dir"] = os.path.dirname(os.path.abspath(path))
    return cfg


def log_path(cfg):
    p = cfg.get("log_path_file")
    if p:
        try:
            with open(p, encoding="utf-8") as f:
                s = f.read().strip()
            if s:
                return s
        except OSError:
            pass
    return cfg["log_fallback"]


def compile_profile(prof):
    req = re.compile(prof["request"]) if prof.get("request") else None
    evs = [(e["kind"], re.compile(e["regex"])) for e in prof.get("events", [])]
    return req, evs


def match(line, req_re, evs):
    m = req_re.search(line) if req_re else None
    if m:
        rec = {"src": "log"}
        for k, v in m.groupdict().items():
            if v is None:
                continue
            if k in CANON:
                rec[k] = CANON[k](v)
            else:                          # pass through: model, slot, rid ... (reporter ignores what it does not know)
                try:
                    rec[k] = int(v)
                except ValueError:
                    try:
                        rec[k] = float(v)
                    except ValueError:
                        rec[k] = v
        if "gen_ms_s" in rec:              # seconds -> ms, the canonical unit
            rec["gen_ms"] = int(rec["gen_ms_s"] * 1000)
            del rec["gen_ms_s"]
        return rec
    for kind, rx in evs:
        m = rx.search(line)
        if m:
            rec = {"src": "log", "kind": kind}
            for k, v in m.groupdict().items():
                if v is not None:
                    try:
                        rec[k] = int(v)
                    except ValueError:
                        rec[k] = float(v)
            return rec
    return None


class OffsetWriter:
    """offset rewritten in place (seek 0 + truncate): re-opening per line costs ~1 ms on Windows
    with AV hooks; an open handle + seek is ~6 us."""

    def __init__(self, path):
        self.f = open(path, "w", encoding="ascii")

    def write(self, offset):
        self.f.seek(0)
        self.f.write(str(offset))
        self.f.truncate()
        self.f.flush()

    def close(self):
        try:
            self.f.close()
        except OSError:
            pass


class DayWriter:
    def __init__(self, out_dir):
        self.dir = out_dir
        self.day = None
        self.f = None

    def write(self, day, text):
        if day != self.day:
            if self.f is not None:
                try:
                    self.f.close()
                except OSError:
                    pass
            self.f = open(os.path.join(self.dir, f"requests-{day}.jsonl"), "a", encoding="utf-8", buffering=1)
            self.day = day
        self.f.write(text + "\n")

    def close(self):
        if self.f is not None:
            try:
                self.f.close()
            except OSError:
                pass
            self.f = None


def read_offset(path):
    try:
        with open(path, encoding="ascii") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def main():
    if "--config" not in sys.argv:
        sys.exit("usage: collector_log.py --config <out_dir>/config.json")
    cfg = load_config(sys.argv[sys.argv.index("--config") + 1])
    out = cfg["out_dir"]
    os.makedirs(out, exist_ok=True)
    offset_path = os.path.join(out, "collector.offset")

    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", int(cfg.get("lock_port", 43177))))
    except OSError:
        print("[collector] another collector already runs, nothing to do")
        return

    req_re, evs = compile_profile(cfg["profile"])
    LOG = log_path(cfg)
    while not os.path.exists(LOG):
        time.sleep(1.0)
    start = read_offset(offset_path)
    try:
        size = os.path.getsize(LOG)
    except OSError:
        size = 0
    if start is None or start > size:
        start = size                       # first run or the log was replaced: count from now on
    elif size > start:                     # lines arrived while down: replay, no re-stamp
        died = datetime.fromtimestamp(os.path.getmtime(offset_path)).strftime("%Y-%m-%d")
        writer = DayWriter(out)
        with open(LOG, "rb") as rf:
            rf.seek(start)
            for raw in rf:
                rec = match(raw.decode("utf-8", "replace"), req_re, evs)
                if rec:
                    writer.write(died, json.dumps(dict(rec, ts=None), ensure_ascii=False))
        writer.close()

    f = open(LOG, "rb")
    f.seek(start)
    writer, off = DayWriter(out), OffsetWriter(offset_path)
    print(f"[collector] tailing {LOG} from byte {start:,}, records in {out}")
    while True:
        line = f.readline()
        if not line:
            try:                           # rotation/truncation: reopen from the head
                if os.path.getsize(LOG) < f.tell():
                    f.close()
                    f = open(LOG, "rb")
            except OSError:
                pass
            time.sleep(0.5)
            continue
        if not line.endswith(b"\n"):       # half-written line: rewind and wait
            f.seek(f.tell() - len(line))
            time.sleep(0.2)
            continue
        offset = f.tell()
        rec = match(line.decode("utf-8", "replace"), req_re, evs)
        if rec:
            now = datetime.now()
            rec["ts"] = now.strftime("%Y-%m-%d %H:%M:%S")
            writer.write(now.strftime("%Y-%m-%d"), json.dumps(rec, ensure_ascii=False))
        off.write(offset)


if __name__ == "__main__":
    main()
