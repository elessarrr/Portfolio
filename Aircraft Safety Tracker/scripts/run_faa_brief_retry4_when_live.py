#!/usr/bin/env python3
"""Probe ASIAS liveness every cron tick; start FAA brief retry4 when portal is up.

Designed for cron every 30 minutes (see scripts/run_faa_brief_retry4_when_live.sh).
Runs the same audit flags as retry3. Exits quickly when retry4 is already done or running.

State: data/logs/faa_brief_retry4_watch_state.json
Audit log: data/logs/faa_brief_retry4_audit_run.log
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "data/logs/faa_brief_retry4_watch_state.json"
LOCK_FILE = ROOT / "data/logs/faa_brief_retry4_watch.lock"
AUDIT_RUN_LOG = ROOT / "data/logs/faa_brief_retry4_audit_run.log"

INPUT = ROOT / "data/logs/faa_aids_brief_retry4_in_2026-06-02.jsonl"
OUTPUT = ROOT / "data/logs/faa_aids_url_audit_brief_2026-06-02_retry4_browserua.jsonl"
SUMMARY = ROOT / "data/logs/faa_aids_url_audit_brief_2026-06-02_retry4_browserua_summary.json"

EXPECTED_ROWS = 368
TIMEOUT_PROBE = 20


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"status": "pending", "checks": 0}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _count_jsonl_rows(path: Path) -> int:
    """Count valid audit rows by source_record_id (not raw lines — corrupt JSONL happens)."""
    if not path.exists():
        return 0
    ids: set[str] = set()
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = obj.get("source_record_id") if isinstance(obj, dict) else None
        if sid:
            ids.add(str(sid))
    return len(ids)


def _probe_liveness() -> bool:
    sys.path.insert(0, str(ROOT))
    from app.ingestion.url_builders.faa_aids_viability import probe_asias_liveness

    return probe_asias_liveness(timeout=TIMEOUT_PROBE)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _notify(title: str, message: str) -> None:
    script = f'display notification "{message}" with title "{title}" sound name "Glass"'
    try:
        subprocess.run(["osascript", "-e", script], check=False, timeout=5)
    except Exception:
        pass


def _start_audit(python: str) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONUNBUFFERED"] = "1"
    env["DATABASE_URL"] = f"sqlite:///{ROOT}/data/aircraft_safety_v3.db"

    cmd = [
        python,
        str(ROOT / "scripts/audit_faa_aids_urls.py"),
        "--input",
        str(INPUT),
        "--out",
        str(OUTPUT),
        "--summary-out",
        str(SUMMARY),
        "--url-mode",
        "brief",
        "--user-agent",
        "browser",
        "--concurrency",
        "6",
        "--timeout",
        "15",
        "--jitter-min-ms",
        "200",
        "--jitter-max-ms",
        "700",
        "--dry-run",
    ]

    AUDIT_RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_f = AUDIT_RUN_LOG.open("a", encoding="utf-8")
    log_f.write(f"\n\n=== retry4 started {_now()} ===\n")
    log_f.flush()

    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return proc.pid


def main() -> int:
    python = os.environ.get(
        "PYTHON", "/Users/Bhavesh/opt/anaconda3/bin/python"
    )
    now = _now()
    state = _load_state()
    state["checks"] = state.get("checks", 0) + 1
    state["last_checked"] = now

    row_count = _count_jsonl_rows(OUTPUT)
    if SUMMARY.exists() and row_count >= EXPECTED_ROWS:
        state["status"] = "completed"
        state["output_rows"] = row_count
        _save_state(state)
        print(f"[{now}] retry4 already complete ({row_count} rows). Nothing to do.")
        return 0

    if state.get("status") == "running":
        pid = int(state.get("pid") or 0)
        if _pid_alive(pid):
            print(f"[{now}] retry4 still running (pid={pid}).")
            _save_state(state)
            return 0
        LOCK_FILE.unlink(missing_ok=True)
        if SUMMARY.exists() and row_count >= EXPECTED_ROWS:
            state["status"] = "completed"
            state["output_rows"] = row_count
            state["completed_at"] = now
            _save_state(state)
            _notify(
                "FAA brief retry4 done",
                f"{row_count} URLs audited. Run merge_faa_aids_audit_overlay.py merge next.",
            )
            print(
                f"[{now}] retry4 finished ({row_count} ids). "
                "Next: scripts/merge_faa_aids_audit_overlay.py merge ..."
            )
            return 0
        print(f"[{now}] retry4 pid {pid} gone; output has {row_count}/{EXPECTED_ROWS} rows.")
        state["status"] = "pending"

    if LOCK_FILE.exists():
        try:
            lock_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
            if _pid_alive(lock_pid):
                print(f"[{now}] lock held by pid {lock_pid}.")
                _save_state(state)
                return 0
        except Exception:
            pass
        LOCK_FILE.unlink(missing_ok=True)

    alive = _probe_liveness()
    state["last_liveness"] = alive
    print(f"[{now}] ASIAS liveness={alive} checks={state['checks']}")

    if not alive:
        _save_state(state)
        return 1

    if not INPUT.exists():
        print(f"[{now}] ERROR: missing input {INPUT}", file=sys.stderr)
        _save_state(state)
        return 2

    pid = _start_audit(python)
    LOCK_FILE.write_text(str(pid), encoding="utf-8")
    state["status"] = "running"
    state["pid"] = pid
    state["started_at"] = now
    _save_state(state)

    print(f"[{now}] retry4 started pid={pid} → log {AUDIT_RUN_LOG}")
    _notify(
        "FAA brief retry4 started",
        f"ASIAS up; auditing {EXPECTED_ROWS} non-brief URLs in background.",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
