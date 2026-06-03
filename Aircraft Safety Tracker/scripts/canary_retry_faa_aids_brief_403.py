#!/usr/bin/env python3
"""Canary retry for FAA AIDS page-18 audit after a 403-heavy run.

Purpose:
  - Avoid burning 45–70 minutes re-hammering ASIAS if we are WAF-blocked.
  - Test mitigations first: browser UA + lower concurrency + adaptive 403 backoff.

Workflow:
  1) Read a prior brief audit export (JSONL).
  2) Filter rows with http_status=403 (not_working).
  3) Sample N rows into an input JSONL compatible with `audit_faa_aids_urls.py`.
  4) Run `audit_faa_aids_urls.py` on that canary input with mitigations enabled.

Example:
  PYTHONPATH=. python scripts/canary_retry_faa_aids_brief_403.py \\
    --from-audit data/logs/faa_aids_url_audit_brief_2026-06-02.jsonl \\
    --sample 200
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-audit", type=Path, required=True)
    parser.add_argument("--sample", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--jitter-min-ms", type=int, default=50)
    parser.add_argument("--jitter-max-ms", type=int, default=200)
    args = parser.parse_args()

    rows = _load_jsonl(args.from_audit)
    blocked = [
        r
        for r in rows
        if r.get("bucket") == "not_working" and r.get("http_status") == 403
    ]
    if not blocked:
        print(f"No 403 not_working rows found in {args.from_audit}")
        return 0

    import random

    rng = random.Random(args.seed)
    picked = blocked if len(blocked) <= args.sample else rng.sample(blocked, args.sample)

    today = date.today().isoformat()
    canary_in = ROOT / f"data/logs/faa_aids_brief_403_canary_in_{today}.jsonl"
    canary_out = ROOT / f"data/logs/faa_aids_brief_403_canary_out_{today}.jsonl"
    canary_summary = ROOT / f"data/logs/faa_aids_brief_403_canary_summary_{today}.json"

    canary_in.parent.mkdir(parents=True, exist_ok=True)
    with canary_in.open("w", encoding="utf-8") as f:
        f.write(f"# canary input from 403 rows — n={len(picked)} — seed={args.seed}\n")
        for r in picked:
            f.write(
                json.dumps(
                    {
                        "source_record_id": r.get("source_record_id"),
                        # `audit_faa_aids_urls.py` prefers `faa_aids_url` if present in input.
                        "faa_aids_url": r.get("faa_aids_url"),
                        "imported_incident_id": r.get("imported_incident_id"),
                        "imported_aircraft_id": r.get("imported_aircraft_id"),
                        "make_model": r.get("make_model"),
                        "date": r.get("date"),
                        "operator": r.get("operator"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    cmd = [
        sys.executable,
        str(ROOT / "scripts/audit_faa_aids_urls.py"),
        "--input",
        str(canary_in),
        "--out",
        str(canary_out),
        "--summary-out",
        str(canary_summary),
        "--url-mode",
        "brief",
        "--dry-run",
        "--concurrency",
        str(args.concurrency),
        "--timeout",
        str(args.timeout),
        "--jitter-min-ms",
        str(args.jitter_min_ms),
        "--jitter-max-ms",
        str(args.jitter_max_ms),
        "--user-agent",
        "browser",
    ]

    print("=" * 60)
    print("FAA AIDS 403 canary retry (brief mode)")
    print(f"From audit:   {args.from_audit}")
    print(f"403 rows:     {len(blocked):,}")
    print(f"Canary size:  {len(picked):,}")
    print(f"Input:        {canary_in}")
    print(f"Output:       {canary_out}")
    print(f"Summary:      {canary_summary}")
    print(f"Concurrency:  {args.concurrency}")
    print("Mitigations:  browser UA + adaptive 403 backoff (default on)")
    print("=" * 60)

    # Run with PYTHONPATH=. so imports work in repo context.
    env = dict(**dict(**__import__("os").environ))
    env["PYTHONPATH"] = "."
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

