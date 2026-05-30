"""FR-10.6: Validate JSONL export bucket counts match audit summary."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, TextIO


EXPORT_BUCKET_FIELDS = {
    "skipped_deduped_asn_covered": "skipped_deduped_asn_covered",
    "viable_with_working_link": "viable_with_working_link",
    "viable_with_broken_link": "viable_with_broken_link",
}


def export_row(bucket: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """Build one JSONL object with bucket first (FR-10.3)."""
    return {"bucket": bucket, **row}


def write_export_row(export_file: TextIO, bucket: str, row: Dict[str, Any]) -> None:
    export_file.write(json.dumps(export_row(bucket, row), sort_keys=True) + "\n")
    export_file.flush()


def count_export_buckets(export_path: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    with open(export_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            bucket = obj.get("bucket") or "unknown"
            counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def validate_export_against_report(
    export_path: str,
    report: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare JSONL line counts per bucket to summary report counts.
    Returns validation dict with matched/mismatches; raises ValueError if mismatched.
    """
    file_counts = count_export_buckets(export_path)
    mismatches: List[Dict[str, Any]] = []

    for bucket, field in EXPORT_BUCKET_FIELDS.items():
        expected = report.get(field, 0)
        actual = file_counts.get(bucket, 0)
        if actual != expected:
            mismatches.append(
                {"bucket": bucket, "expected": expected, "actual": actual}
            )

    result = {
        "export_path": export_path,
        "file_counts": file_counts,
        "total_lines": sum(file_counts.values()),
        "matched": not mismatches,
        "mismatches": mismatches,
    }
    if mismatches:
        raise ValueError(
            "Export bucket counts do not match summary report: "
            + json.dumps(mismatches)
        )
    return result
