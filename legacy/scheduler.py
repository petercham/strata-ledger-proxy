#!/usr/bin/env python3
r"""token-ledger · daily trigger: a resident loop that checks roughly every 20 s whether a new
calendar day has started and, on the first wake of the day (or at boot after a night-off machine),
runs daily_report.run_daily(). Survives sleep/wake (the sleep is sliced), keeps looping after an
exception, and skips the day if daily_report.py already produced the report (it is idempotent).

  python scheduler.py --config <out_dir>/config.json

Prefer this over OS schedulers when the machine may be asleep/off at the trigger time: boot
recovery is built in (start the scheduler from startup; it fires the same-day check immediately).
Where an OS scheduler (cron/schtasks/systemd timer) is guaranteed to run at the time, calling
daily_report.py directly is equally fine - both are idempotent.

Single instance: bind on 127.0.0.1:(lock_port+1). report_hour/report_minute in the config choose
the generation time (the human-decided value).

NOTE (2026-11-09): on this machine the daily trigger has been MERGED into
collector_proxy.py as a daemon thread; the startup chain no longer launches this
file. It is kept for backward compatibility only (manual invocation still works).
daily_report.run_daily() is idempotent, so running this alongside the merged
process cannot duplicate reports, and no extra lock is needed.
"""
import json
import os
import socket
import sys
import time
import traceback
from datetime import datetime


def main():
    if "--config" not in sys.argv:
        sys.exit("usage: scheduler.py --config <out_dir>/config.json")
    cfg_path = os.path.abspath(sys.argv[sys.argv.index("--config") + 1])
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    out = cfg["out_dir"]
    os.makedirs(out, exist_ok=True)
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", int(cfg.get("lock_port", 43177)) + 1))
    except OSError:
        print("[scheduler] another scheduler already runs, nothing to do")
        return

    rh = int(cfg.get("report_hour", 0))
    rm = int(cfg.get("report_minute", 0))
    runlog = os.path.join(out, "daily-report.log")

    # import daily_report from the same directory
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import daily_report

    def fire(why):
        try:
            daily_report.run_daily(cfg)
            with open(runlog, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] scheduler fired ({why})\n")
        except Exception:
            with open(runlog, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] scheduler ERROR: {traceback.format_exc()}\n")

    today = datetime.now().strftime("%Y-%m-%d")
    # boot recovery: if yesterday-or-earlier days lack reports right now, catch up immediately
    fire("boot check")
    print(f"[scheduler] daily report at {rh:02d}:{rm:02d}; waking every 20 s; records dir {out}")
    while True:
        now = datetime.now()
        day = now.strftime("%Y-%m-%d")
        if day != today and (now.hour, now.minute) >= (rh, rm):
            fire(f"new day {day}")
            today = day
        time.sleep(20)


if __name__ == "__main__":
    main()
