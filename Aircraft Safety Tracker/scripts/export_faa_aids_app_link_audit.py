#!/usr/bin/env python3
"""Export FAA app-link audit rows from merged brief-mode URL audit (PRD 0009 FR-3)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_MERGED = ROOT / "data/logs/faa_aids_url_audit_brief_2026-06-02_merged.jsonl"
DEFAULT_ROWS = ROOT / "data/logs/faa_aids_app_link_audit_rows.jsonl"
DEFAULT_SUMMARY = ROOT / "data/logs/faa_aids_app_link_audit_summary.json"
BUCKET_BRIEF = "working_brief_report"


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append(json.loads(line))
    return rows


def export_app_link_rows(merged_path: Path) -> tuple[list[dict], dict]:
    merged = _load_jsonl(merged_path)
    out_rows = []
    counts: dict[str, int] = {}
    for row in merged:
        bucket = row.get("bucket") or "not_working"
        counts[bucket] = counts.get(bucket, 0) + 1
        out_rows.append(
            {
                "bucket": bucket,
                "source_record_id": row.get("source_record_id"),
                "faa_aids_url": row.get("faa_aids_url"),
                "imported_incident_id": row.get("imported_incident_id"),
                "http_status": row.get("http_status"),
                "link_viable": row.get("link_viable"),
                "product_viable": row.get("product_viable"),
                "link_reason": row.get("link_reason"),
                "checked_at": row.get("checked_at"),
            }
        )
    summary = {
        "export_date": date.today().isoformat(),
        "source_merged_audit": str(merged_path),
        "total_rows": len(out_rows),
        "bucket_counts": counts,
        "product_viable_count": counts.get(BUCKET_BRIEF, 0),
        "gate_pct_brief": round(counts.get(BUCKET_BRIEF, 0) / len(out_rows) * 100, 2) if out_rows else 0,
    }
    return out_rows, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merged", type=Path, default=DEFAULT_MERGED)
    parser.add_argument("--rows-out", type=Path, default=DEFAULT_ROWS)
    parser.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    rows, summary = export_app_link_rows(args.merged)
    args.rows_out.parent.mkdir(parents=True, exist_ok=True)
    with args.rows_out.open("w", encoding="utf-8") as f:
        f.write(f"# FAA app link audit export — {summary['export_date']} — n={len(rows)}\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    args.summary_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
