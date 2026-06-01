#!/usr/bin/env python3
"""Re-run ASN dedupe on NTSB working-link rows using approved make_model mapping (FR-18)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.ingestion.ntsb_dedupe_repass import (
    load_working_link_rows,
    run_dedupe_repass,
    write_jsonl,
)
from app.ingestion.ntsb_mapping import load_ntsb_make_model_mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_ROWS = ROOT / "data/logs/ntsb_enrichment_audit_rows.jsonl"
DEFAULT_MAPPING = ROOT / "data/config/ntsb_make_model_to_aircraft.jsonl"
DEFAULT_REPASSE_OUT = ROOT / "data/logs/ntsb_dedupe_repasse.json"
DEFAULT_NORMALIZED_OUT = ROOT / "data/logs/ntsb_enrichment_audit_rows_normalized.jsonl"
DEFAULT_SUMMARY_OUT = ROOT / "data/logs/ntsb_pre_import_summary.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audit-rows",
        type=Path,
        default=DEFAULT_AUDIT_ROWS,
        help="Audit export JSONL (uses bucket=viable_with_working_link).",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=DEFAULT_MAPPING,
        help="Approved ntsb_make_model_to_aircraft.jsonl gate file.",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="ASN candidate search window (days). Default: 7",
    )
    parser.add_argument(
        "--repasse-out",
        type=Path,
        default=DEFAULT_REPASSE_OUT,
        help="Dedupe re-pass report JSON.",
    )
    parser.add_argument(
        "--normalized-out",
        type=Path,
        default=DEFAULT_NORMALIZED_OUT,
        help="Normalized working rows JSONL.",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=DEFAULT_SUMMARY_OUT,
        help="Pre-import summary JSON (FR-19.2).",
    )
    args = parser.parse_args()

    working_rows = load_working_link_rows(args.audit_rows)
    mapping = load_ntsb_make_model_mapping(args.mapping)

    database_url = os.environ.get("DATABASE_URL")
    app = create_app()
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    with app.app_context():
        report, normalized = run_dedupe_repass(
            working_rows,
            mapping,
            window_days=args.window_days,
        )

    summary = {
        "working_link_total": report["working_link_total"],
        "import_candidates_after_dedupe_repasse": report["import_candidates_after_dedupe_repasse"],
        "skipped_unmapped": report["skipped_unmapped"],
        "skipped_pending_create": report["skipped_pending_create"],
        "skipped_asn_covered_repasse": report["skipped_asn_covered_repasse"],
        "newly_deduped_count": report["newly_deduped_count"],
        "distinct_canonical_aircraft_ids": report["distinct_canonical_aircraft_ids"],
        "distinct_canonical_model_names": report["distinct_canonical_model_names"],
        "mapping_path": str(args.mapping),
        "audit_rows_path": str(args.audit_rows),
    }

    args.repasse_out.parent.mkdir(parents=True, exist_ok=True)
    repasse_payload = {
        **report,
        "mapping_path": str(args.mapping),
        "audit_rows_path": str(args.audit_rows),
    }
    with args.repasse_out.open("w") as f:
        json.dump(repasse_payload, f, indent=2, sort_keys=True)

    write_jsonl(
        args.normalized_out,
        normalized,
        [
            "# Normalized NTSB working-link rows with mapping + dedupe re-pass status",
            f"# source audit: {args.audit_rows}",
            f"# mapping: {args.mapping}",
        ],
    )

    with args.summary_out.open("w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
