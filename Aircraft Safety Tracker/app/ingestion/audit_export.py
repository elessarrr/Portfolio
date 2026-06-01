"""FR-10.6: Validate JSONL export bucket counts match audit summary."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, TextIO

WORKING_LINK_BUCKET = "viable_with_working_link"

EXPORT_BUCKET_FIELDS = {
    "skipped_deduped_asn_covered": "skipped_deduped_asn_covered",
    "viable_with_working_link": "viable_with_working_link",
    "viable_with_broken_link": "viable_with_broken_link",
}

EXPORT_LEGEND_LINES = [
    "# NTSB enrichment audit export — bucket legend (PRD 0006.2)",
    "# Records are split into two sections below (see section headers for counts).",
    "# Pipeline: parse (Boeing/Airbus) → dedupe vs ASN → viable unique → URL check → bucket",
    "#",
    "# - skipped_deduped_asn_covered: Matched an existing ASN incident (dedupe ≥2 strong signals on date/operator/location/fatalities). Removed from import — would duplicate ASN baseline.",
    "# - viable_with_working_link: Not ASN-covered. Resolved NTSB URL passed HTTP check (CAROL or released docket). Candidate for import (Task 6).",
    "# - viable_with_broken_link: Not ASN-covered (same dedupe gate as working) but URL failed viability — usually docket_not_released (\"The docket for this investigation has not been released\"). Excluded from import; Details would be a dead end.",
    "# - viable_unique: Not ASN-covered; link check not run (--check-links off). Pending URL validation.",
    "# - viable_link_check_skipped: Not ASN-covered; link check skipped (--max-link-checks cap reached).",
    "#",
    "# Fields: unknown_aircraft=true when NTSB make/model has no v3 aircraft match (ASN dedupe skipped).",
    "#         link_reason=null when viable; e.g. docket_not_released, http_404 when broken.",
    "#",
]

TO_ADD_SECTION_TITLE = (
    "# TO ADD TO DATABASE ('viable_with_working_link' bucket). COUNT = {count}"
)
OTHER_LINKS_SECTION_TITLE = "# OTHER LINKS. COUNT = {count}"


def write_export_legend(export_file: TextIO) -> None:
    """Write human-readable legend comment block before JSONL data rows."""
    export_file.write("\n".join(EXPORT_LEGEND_LINES) + "\n")
    export_file.flush()


def export_row(bucket: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """Build one JSONL object with bucket first (FR-10.3)."""
    return {"bucket": bucket, **row}


class ExportCollector:
    """Buffer classified rows; flush as two sections (to-add vs other)."""

    def __init__(self) -> None:
        self.to_add: List[Dict[str, Any]] = []
        self.other: List[Dict[str, Any]] = []

    def add(self, bucket: str, row: Dict[str, Any]) -> None:
        line = export_row(bucket, row)
        if bucket == WORKING_LINK_BUCKET:
            self.to_add.append(line)
        else:
            self.other.append(line)

    def write_to_path(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            write_export_legend(f)
            f.write(TO_ADD_SECTION_TITLE.format(count=len(self.to_add)) + "\n")
            for row in self.to_add:
                f.write(json.dumps(row, sort_keys=True) + "\n")
            f.write("\n" + OTHER_LINKS_SECTION_TITLE.format(count=len(self.other)) + "\n")
            for row in self.other:
                f.write(json.dumps(row, sort_keys=True) + "\n")


def write_export_row(export_file: TextIO, bucket: str, row: Dict[str, Any]) -> None:
    """Legacy streaming write (single section); prefer ExportCollector for new exports."""
    export_file.write(json.dumps(export_row(bucket, row), sort_keys=True) + "\n")
    export_file.flush()


def count_export_buckets(export_path: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    with open(export_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            obj = json.loads(line)
            if obj.get("record_type") == "legend":
                continue
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
        "to_add_count": file_counts.get(WORKING_LINK_BUCKET, 0),
        "other_count": sum(
            v for k, v in file_counts.items() if k != WORKING_LINK_BUCKET
        ),
        "matched": not mismatches,
        "mismatches": mismatches,
    }
    if mismatches:
        raise ValueError(
            "Export bucket counts do not match summary report: "
            + json.dumps(mismatches)
        )
    return result
