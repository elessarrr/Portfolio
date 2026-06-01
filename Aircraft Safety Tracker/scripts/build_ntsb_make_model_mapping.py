#!/usr/bin/env python3
"""Build approved NTSB make_model → aircraft mapping from rollup draft (FR-16)."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAFT = ROOT / "data/logs/ntsb_rollup_string_mapping_draft.jsonl"
DEFAULT_OUT = ROOT / "data/config/ntsb_make_model_to_aircraft.jsonl"
DEFAULT_AUDIT = ROOT / "data/logs/ntsb_enrichment_audit_rows.jsonl"


def _manufacturer_from_page(page: str) -> str:
    if page.lower().startswith("airbus"):
        return "Airbus"
    return "Boeing"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def _draft_to_approved(row: dict[str, Any]) -> dict[str, Any]:
    page = row.get("override_aircraft_page") or row["proposed_aircraft_page"]
    action = row["proposed_action"]
    if page == "TBD" or action == "TBD":
        raise ValueError(f"unapproved mapping for {row['ntsb_make_model']!r}")

    out: dict[str, Any] = {
        "ntsb_make_model": row["ntsb_make_model"],
        "canonical_aircraft_id": row.get("proposed_aircraft_id"),
        "canonical_model_name": page,
        "action": action,
    }
    if action == "create_approved":
        out["manufacturer"] = _manufacturer_from_page(page)
    incident_count = row.get("incident_count")
    if incident_count is not None:
        out["notes"] = f"{incident_count} working-link incident(s); source=rollup_draft_v1"
    return out


def _working_make_models(audit_path: Path) -> set[str]:
    models: set[str] = set()
    with audit_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            row = json.loads(line)
            if row.get("bucket") == "viable_with_working_link":
                models.add(row["make_model"])
    return models


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--approved-date", default=date.today().isoformat())
    args = parser.parse_args()

    draft_rows = _load_jsonl(args.draft)
    approved = [_draft_to_approved(r) for r in draft_rows]

    working = _working_make_models(args.audit)
    mapped = {r["ntsb_make_model"] for r in approved}
    missing = working - mapped
    extra = mapped - working
    if missing:
        raise SystemExit(f"mapping missing {len(missing)} working-bucket strings: {sorted(missing)[:5]}")
    if extra:
        raise SystemExit(f"mapping has {len(extra)} strings not in working bucket")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        f.write(f"# ntsb_make_model_to_aircraft v1 approved {args.approved_date}\n")
        f.write(f"# source: {args.draft.relative_to(ROOT)}\n")
        f.write(f"# rows: {len(approved)} distinct strings / {len(working)} checked against working bucket\n")
        for row in approved:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    actions = {}
    pages = set()
    for r in approved:
        actions[r["action"]] = actions.get(r["action"], 0) + 1
        pages.add(r["canonical_model_name"])

    print(f"wrote {len(approved)} rows -> {args.out}")
    print(f"actions: {actions}")
    print(f"distinct canonical pages: {len(pages)}")


if __name__ == "__main__":
    main()
