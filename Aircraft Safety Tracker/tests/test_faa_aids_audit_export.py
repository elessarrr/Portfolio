"""FAA app-link export integrity (PRD 0009 FR-3.5)."""

import importlib.util
import json
import sys
from pathlib import Path

from app.ingestion.audit_export import count_export_buckets


def test_count_export_buckets_skips_comments(tmp_path: Path):
    p = tmp_path / "rows.jsonl"
    rows = [
        {"bucket": "working_brief_report"},
        {"bucket": "not_working"},
        {"bucket": "working_brief_report"},
    ]
    with p.open("w", encoding="utf-8") as f:
        f.write("# header\n")
        for row in rows:
            f.write(json.dumps(row) + "\n")
    counts = count_export_buckets(str(p))
    assert counts["working_brief_report"] == 2
    assert counts["not_working"] == 1


def test_export_app_link_rows_summary(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "export_faa_aids_app_link_audit",
        root / "scripts/export_faa_aids_app_link_audit.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["export_faa_aids_app_link_audit"] = mod
    spec.loader.exec_module(mod)

    merged = tmp_path / "merged.jsonl"
    merged.write_text(
        "\n".join(
            [
                "# merged",
                json.dumps({"source_record_id": "A1", "bucket": "working_brief_report", "faa_aids_url": "u1"}),
                json.dumps({"source_record_id": "A2", "bucket": "not_working", "faa_aids_url": "u2"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out_rows, summary = mod.export_app_link_rows(merged)
    assert len(out_rows) == 2
    assert summary["product_viable_count"] == 1
    assert summary["bucket_counts"]["not_working"] == 1
