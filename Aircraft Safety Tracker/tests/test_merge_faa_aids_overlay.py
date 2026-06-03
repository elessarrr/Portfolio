"""Tests for scripts/merge_faa_aids_audit_overlay.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "merge_faa_aids_audit_overlay",
    ROOT / "scripts/merge_faa_aids_audit_overlay.py",
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
build_gap_input = _mod.build_gap_input
merge_overlay = _mod.merge_overlay


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def test_gap_detects_missing_ids(tmp_path: Path) -> None:
    inp = tmp_path / "in.jsonl"
    out = tmp_path / "out.jsonl"
    gap = tmp_path / "gap.jsonl"
    _write_jsonl(
        inp,
        [
            {"source_record_id": "A", "faa_aids_url": "http://a"},
            {"source_record_id": "B", "faa_aids_url": "http://b"},
        ],
    )
    _write_jsonl(
        out,
        [
            {
                "source_record_id": "A",
                "bucket": "working_brief_report",
                "faa_aids_url": "http://a",
            },
        ],
    )
    n = build_gap_input(inp, [out], gap)
    assert n == 1
    gap_rows = gap.read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(gap_rows[0])["source_record_id"] == "B"


def test_merge_overlay_updates_bucket(tmp_path: Path) -> None:
    base = tmp_path / "merged.jsonl"
    overlay = tmp_path / "retry.jsonl"
    summary = tmp_path / "summary.json"
    _write_jsonl(
        base,
        [
            {
                "source_record_id": "X",
                "bucket": "not_working",
                "faa_aids_url": "http://x",
            },
        ],
    )
    _write_jsonl(
        overlay,
        [
            {
                "source_record_id": "X",
                "bucket": "working_brief_report",
                "faa_aids_url": "http://x",
            },
        ],
    )
    merge_overlay(base, [overlay], base, backup=False, summary_out=summary, tolerant=True)
    row = json.loads(base.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert row["bucket"] == "working_brief_report"
    summary_data = json.loads(summary.read_text(encoding="utf-8"))
    assert summary_data["product_viable_count"] == 1
