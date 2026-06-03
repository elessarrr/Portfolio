#!/usr/bin/env python3
"""Overlay FAA AIDS retry JSONL onto a base merged audit (by source_record_id).

Use after a deferred retry batch (e.g. retry4 when ASIAS was down):
  1. Audit retry input → retry{N}_browserua.jsonl
  2. Gap-fill any missing IDs (see --build-gap-input)
  3. Merge overlays onto *_merged.jsonl with backup + summary

Tolerant JSONL read skips corrupt lines (common when audit output is interrupted).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BUCKET_BRIEF = "working_brief_report"
BUCKET_SEARCH = "working_search_prefill"
BUCKET_NW = "not_working"


def load_audit_jsonl(path: Path, *, tolerant: bool = True) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.open(encoding="utf-8"), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            if tolerant:
                continue
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def load_by_source_id(paths: list[Path], *, tolerant: bool = True) -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for path in paths:
        for row in load_audit_jsonl(path, tolerant=tolerant):
            sid = row.get("source_record_id")
            if sid:
                by_id[str(sid)] = row
    return by_id


def build_gap_input(
    retry_input: Path,
    retry_outputs: list[Path],
    gap_out: Path,
) -> int:
    """Write rows from retry_input that are missing from retry output JSONL."""
    in_by = load_by_source_id([retry_input], tolerant=True)
    out_by = load_by_source_id(retry_outputs, tolerant=True)
    missing = sorted(set(in_by) - set(out_by))
    gap_out.parent.mkdir(parents=True, exist_ok=True)
    with gap_out.open("w", encoding="utf-8") as f:
        for sid in missing:
            f.write(json.dumps(in_by[sid], ensure_ascii=False) + "\n")
    print(f"gap input: {len(missing)} rows → {gap_out}")
    return len(missing)


def merge_overlay(
    base: Path,
    overlays: list[Path],
    out: Path,
    *,
    backup: bool,
    summary_out: Path | None,
    tolerant: bool,
) -> dict:
    updates = load_by_source_id(overlays, tolerant=tolerant)
    backup_path = base.with_name(f"{base.stem}_pre_overlay{base.suffix}")
    if backup and not backup_path.exists():
        shutil.copy2(base, backup_path)
        print(f"backup: {backup_path}")

    counts: Counter[str] = Counter()
    lines_out: list[str] = []
    src_base = backup_path if backup_path.exists() else base
    for row in load_audit_jsonl(src_base, tolerant=False):
        sid = row.get("source_record_id")
        if sid and str(sid) in updates:
            row = updates[str(sid)]
        bucket = row.get("bucket", BUCKET_NW)
        counts[str(bucket)] += 1
        lines_out.append(json.dumps(row, ensure_ascii=False))

    today = date.today().isoformat()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        f.write(
            f"# FAA AIDS URL audit (merged) — {today} — {len(lines_out)} rows"
            f" — {counts[BUCKET_BRIEF]} {BUCKET_BRIEF}"
            f" — {counts[BUCKET_SEARCH]} {BUCKET_SEARCH}"
            f" — {counts[BUCKET_NW]} {BUCKET_NW}\n"
        )
        f.write(f"# Overlay merge from {len(updates)} retry row(s)\n")
        for line in lines_out:
            f.write(line + "\n")

    pct = round(counts[BUCKET_BRIEF] / len(lines_out) * 100, 2) if lines_out else 0.0
    summary = {
        "audit_date": today,
        "merged_path": str(out),
        "total_rows": len(lines_out),
        "bucket_counts": dict(counts),
        "product_viable_count": counts[BUCKET_BRIEF],
        "gate_pct_brief": pct,
        "overlay_rows": len(updates),
        "overlay_sources": [str(p) for p in overlays],
        "backup": str(backup_path) if backup_path.exists() else None,
    }
    if summary_out:
        summary_out.parent.mkdir(parents=True, exist_ok=True)
        summary_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"summary: {summary_out}")
    print(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    gap_p = sub.add_parser("gap", help="Build gap-fill input for missing retry output IDs")
    gap_p.add_argument("--retry-input", type=Path, required=True)
    gap_p.add_argument(
        "--retry-output",
        type=Path,
        action="append",
        required=True,
        help="Retry audit JSONL (repeat for gap + gap2 chunks)",
    )
    gap_p.add_argument("--gap-out", type=Path, required=True)

    merge_p = sub.add_parser("merge", help="Overlay retry JSONL onto base merged audit")
    merge_p.add_argument("--base", type=Path, required=True, help="Pre-overlay merged JSONL")
    merge_p.add_argument(
        "--overlay",
        type=Path,
        action="append",
        required=True,
        help="Retry output JSONL(s); later files win on duplicate IDs",
    )
    merge_p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Merged output (default: overwrite --base)",
    )
    merge_p.add_argument("--no-backup", action="store_true")
    merge_p.add_argument("--summary-out", type=Path, default=None)
    merge_p.add_argument(
        "--strict",
        action="store_true",
        help="Fail on corrupt JSONL in overlay files (default: skip bad lines)",
    )

    args = parser.parse_args()
    if args.command == "gap":
        n = build_gap_input(args.retry_input, args.retry_output, args.gap_out)
        return 0 if n >= 0 else 1

    out = args.out or args.base
    merge_overlay(
        args.base,
        args.overlay,
        out,
        backup=not args.no_backup,
        summary_out=args.summary_out,
        tolerant=not args.strict,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
