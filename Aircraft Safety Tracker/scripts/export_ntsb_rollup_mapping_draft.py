#!/usr/bin/env python3
"""Draft NTSB make_model → aircraft page mapping for product review (PRD 0006.3)."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = ROOT / "data/logs/ntsb_enrichment_audit_rows.jsonl"
DEFAULT_DB = ROOT / "data/aircraft_safety_v3.db"
DEFAULT_STRINGS_OUT = ROOT / "data/logs/ntsb_rollup_string_mapping_draft.jsonl"
DEFAULT_INCIDENTS_OUT = ROOT / "data/logs/ntsb_rollup_incident_assignments_draft.jsonl"

# Family pages to create when no catalog row exists (product-approved pattern).
CREATE_FAMILY_PAGES = {
    "Boeing 737",
    "Boeing 787",
}

STEARMAN_PAGE = "Boeing-Stearman Kaydet"
STEARMAN_ID = 68


def _load_catalog(db_path: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT id, manufacturer, model_name FROM aircraft ORDER BY model_name"
    ).fetchall()
    conn.close()
    return [{"id": r[0], "manufacturer": r[1], "model_name": r[2]} for r in rows]


def _normalize_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _is_stearman(make_model: str) -> bool:
    u = (make_model or "").upper()
    patterns = (
        "A75N1",
        "B75N1",
        "A75N",
        "B75N",
        " STEARMAN",
        "STEARMAN ",
        "KAYDET",
        "PT17",
        "PT-17",
        "PT 17",
        "PT13",
        "PT-13",
        "PT 13",
        "N2S",
        "BOEING E75",
        " E75",
    )
    if any(p in u for p in patterns):
        return True
    if re.search(r"\bB75\b", u) or re.search(r"\bA75\b", u):
        return True
    if u.startswith("BOEING B75") or u.startswith("BOEING A75"):
        return True
    return False


def _is_helicopter(make_model: str) -> bool:
    u = _normalize_for_match(make_model)
    tokens = (
        "HELICOP",
        "AS350",
        "AS 350",
        "EC135",
        "EC-130",
        "EC130",
        "EC 130",
        "H500",
        "H 500",
        "BK 117",
        "BK117",
        "MBB-BK",
        "MD600",
        "MD 600",
        "CH-47",
        "CH47",
        "CHINOOK",
        "VERTOL",
        "H125",
    )
    return any(t in u for t in tokens)


def _helicopter_page(make_model: str, catalog_by_name: dict[str, dict]) -> tuple[str, Optional[int], str]:
    u = _normalize_for_match(make_model)
    if "H125" in u:
        name = "Airbus Helicopters H125"
        row = catalog_by_name.get(name)
        return name, row["id"] if row else None, "map_to_existing" if row else "create_approved"
    if "AS350" in u or "AS 350" in u or "AS-350" in u:
        return "Airbus Helicopters AS350", None, "create_approved"
    if "BK" in u and "117" in u:
        return "Airbus Helicopters BK117", None, "create_approved"
    if "EC135" in u or "EC-130" in u or "EC130" in u or "EC 130" in u:
        return "Airbus Helicopters EC135", None, "create_approved"
    if "H500" in u:
        return "Boeing Helicopters H500", None, "create_approved"
    if "MD600" in u or "MD 600" in u:
        return "Boeing Helicopters MD600", None, "create_approved"
    if "CH-47" in u or "CH47" in u or "CHINOOK" in u:
        row = catalog_by_name.get("Boeing CH-47 Chinook")
        if row:
            return row["model_name"], row["id"], "map_to_existing"
        return "Boeing CH-47 Chinook", None, "create_approved"
    if "VERTOL" in u or "CH-46" in u:
        row = catalog_by_name.get("Boeing Vertol CH-46 Sea Knight")
        if row:
            return row["model_name"], row["id"], "map_to_existing"
        return "Boeing Vertol CH-46 Sea Knight", None, "create_approved"
    return "Airbus Helicopters (review)", None, "create_approved"


def _normalize_for_match(make_model: str) -> str:
    u = (make_model or "").upper()
    u = u.replace("AIRBUS INDUSTRIE", "AIRBUS").replace("AIRBUS CANADA", "AIRBUS")
    u = u.replace("A-3", "A3").replace("A-2", "A2")  # A-320 → A320
    u = u.replace("AS-350", "AS350").replace("AS 350", "AS350")
    u = re.sub(r"\s+", " ", u).strip()
    return u


def _best_catalog_match(
    make_model: str, catalog: list[dict[str, Any]]
) -> Optional[dict[str, Any]]:
    """Pick best catalog row by family + variant hints in the NTSB string."""
    u = _normalize_for_match(make_model)

    def find(name: str) -> Optional[dict]:
        for row in catalog:
            if row["model_name"] == name:
                return row
        return None

    # Product-confirmed overrides (PRD 0006.3 review 2026-05-31)
    if re.fullmatch(r"AIRBUS F4-622R", u) or "F4-622R" in u:
        row = find("Airbus A300-600")
        if row:
            return row
    if u == "BOEING MD":
        return {"id": None, "model_name": "Boeing MD-82", "manufacturer": "Boeing"}
    if u == "BOEING CV2":
        return {"id": None, "model_name": "Boeing CV2", "manufacturer": "Boeing"}

    # Specific variant patterns before generic family
    variant_rules: list[tuple[str, str]] = [
        (r"787-10|787 10", "Boeing 787-10 Dreamliner"),
        (r"787-9|787 9", "Boeing 787-9 Dreamliner"),
        (r"787-8|787 8", "Boeing 787-8 Dreamliner"),
        (r"A321NEO|A321-271N|A321 NEO", "Airbus A321neo"),
        (r"A320NEO|A320-271N", "Airbus A320neo"),
        (r"A350-1000|A350 1000", "Airbus A350-1000"),
        (r"A350-900|A350 900", "Airbus A350-900"),
        (r"A330-800", "Airbus A330-800"),
        (r"A330-900", "Airbus A330-900"),
        (r"A330-300", "Airbus A330-300"),
        (r"A330-200", "Airbus A330-200"),
        (r"A340-600", "Airbus A340-600"),
        (r"A340-500", "Airbus A340-500"),
        (r"A340-300", "Airbus A340-300"),
        (r"A340-200", "Airbus A340-200"),
        (r"747-422|747 422|747-412|747 412", "Boeing 747-400"),
        (r"747-8|747 8", "Boeing 747-8"),
        (r"747SP", "Boeing 747SP"),
        (r"747SR", "Boeing 747SR"),
        (r"747-400|747 400", "Boeing 747-400"),
        (r"747-300|747 300", "Boeing 747-300"),
        (r"747-200|747 200", "Boeing 747-200"),
        (r"747-100|747 100", "Boeing 747-100"),
        (r"747", "Boeing 747-400"),
        (r"707-321B|707 321B|707-338C|707 338C|707", "Boeing 707-300"),
        (r"757-300", "Boeing 757-300"),
        (r"757", "Boeing 757-200"),
        (r"767-400", "Boeing 767-400"),
        (r"767-300", "Boeing 767-300"),
        (r"767-200", "Boeing 767-200"),
        (r"767", "Boeing 767-300"),
        (r"777-300ER|777 300ER", "Boeing 777-300ER"),
        (r"777-300|777 300", "Boeing 777-300"),
        (r"777-200LR|777 200LR", "Boeing 777-200LR"),
        (r"777-200|777 200", "Boeing 777-200"),
        (r"777", "Boeing 777-200"),
        (r"727-100", "Boeing 727-100"),
        (r"727", "Boeing 727-200"),
        (r"717", "Boeing 717"),
        (r"A380", "Airbus A380"),
        (r"A350", "Airbus A350"),
        (r"A340", "Airbus A340-300"),
        (r"A330|\b330\b", "Airbus A330-300"),
        (r"A321", "Airbus A321"),
        (r"A320|AIRBUS 320|\b320\b", "Airbus A320"),
        (r"A319|\b319\b", "Airbus A319"),
        (r"A318", "Airbus A318"),
        (r"A310", "Airbus A310"),
        (r"A300-600", "Airbus A300-600"),
        (r"A300", "Airbus A300"),
        (r"A220|BD500|CSERIES|CS300|CS100", "Airbus A220"),
        (r"MD-11|MD11", "Boeing MD-11"),
        (r"MD-10|MD10", "Boeing MD-10"),
        (r"MD-90|MD90", "Boeing MD-90"),
        (r"MD-88|MD88", "Boeing MD-88"),
        (r"MD-83|MD83", "Boeing MD-83"),
        (r"MD-82|MD82", "Boeing MD-82"),
        (r"MD-80|MD80", "Boeing MD-80"),
        (r"B-17|B17", "Boeing B-17 Flying Fortress"),
        (r"S-307|S\.307|S 307", "Boeing S.307 Stratoliner"),
        (r"CH-46|CH46", "Boeing Vertol CH-46 Sea Knight"),
        (r"DC-10|DC10", "Boeing DC-10"),
        (r"DHC-8|DHC 8", "Boeing DHC-8 Dash 8"),
        (r"737 MAX 9|737-9 MAX|737 MAX9", "Boeing 737 MAX 9"),
        (r"737 MAX 8|737-8 MAX|737 MAX8", "Boeing 737 MAX 8"),
        (r"737-900|737 900", "Boeing 737-900"),
        (r"737-800|737 800", "Boeing 737-800"),
        (r"737-700|737 700", "Boeing 737-700"),
        (r"737-600|737 600", "Boeing 737-600"),
        (r"737-500|737 500", "Boeing 737-500"),
        (r"737-400|737 400", "Boeing 737-400"),
        (r"737-300|737 300", "Boeing 737-300"),
        (r"737-200|737 200", "Boeing 737-200"),
        (r"737-100|737 100", "Boeing 737-100"),
        (r"737", "Boeing 737"),
        (r"787", "Boeing 787"),
    ]

    for pattern, catalog_name in variant_rules:
        if re.search(pattern, u):
            row = find(catalog_name)
            if row:
                return row
            if catalog_name in CREATE_FAMILY_PAGES:
                return {"id": None, "model_name": catalog_name, "manufacturer": "Boeing"}
            # Approved create for MD/helicopter naming with Boeing/Airbus prefix
            if catalog_name.startswith(("Boeing ", "Airbus ")):
                return {"id": None, "model_name": catalog_name, "manufacturer": catalog_name.split()[0]}
    return None


def propose_page(
    make_model: str, catalog: list[dict[str, Any]], catalog_by_name: dict[str, dict]
) -> tuple[str, Optional[int], str, str]:
    if _is_stearman(make_model):
        return STEARMAN_PAGE, STEARMAN_ID, "map_to_existing", "stearman"
    if _is_helicopter(make_model):
        page, aid, action = _helicopter_page(make_model, catalog_by_name)
        cat = "helicopter"
        return page, aid, action, cat

    match = _best_catalog_match(make_model, catalog)
    if match:
        aid = match.get("id")
        action = "map_to_existing" if aid else "create_approved"
        return match["model_name"], aid, action, "fixed_wing"

    return "TBD", None, "TBD", "fixed_wing"


def load_working_rows(audit_path: Path) -> list[dict]:
    rows = []
    with audit_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            row = json.loads(line)
            if row.get("bucket") == "viable_with_working_link":
                rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--strings-out", type=Path, default=DEFAULT_STRINGS_OUT)
    parser.add_argument("--incidents-out", type=Path, default=DEFAULT_INCIDENTS_OUT)
    args = parser.parse_args()

    catalog = _load_catalog(args.db)
    catalog_by_name = {r["model_name"]: r for r in catalog}
    working = load_working_rows(args.input)

    by_model: dict[str, list[dict]] = defaultdict(list)
    for row in working:
        by_model[row["make_model"]].append(row)

    string_rows = []
    for make_model, incidents in sorted(by_model.items(), key=lambda x: (-len(x[1]), x[0])):
        page, aid, action, category = propose_page(make_model, catalog, catalog_by_name)
        string_rows.append(
            {
                "ntsb_make_model": make_model,
                "incident_count": len(incidents),
                "category": category,
                "proposed_aircraft_page": page,
                "proposed_aircraft_id": aid,
                "proposed_action": action,
                "product_decision": "",
                "override_aircraft_page": "",
            }
        )

    mapping = {r["ntsb_make_model"]: r for r in string_rows}
    incident_rows = []
    for row in sorted(working, key=lambda x: (x.get("date") or ""), reverse=True):
        sm = mapping[row["make_model"]]
        incident_rows.append(
            {
                "source_record_id": row["source_record_id"],
                "date": row.get("date"),
                "ntsb_make_model": row["make_model"],
                "proposed_aircraft_page": sm["proposed_aircraft_page"],
                "operator": row.get("operator"),
                "location": row.get("location"),
            }
        )

    args.strings_out.parent.mkdir(parents=True, exist_ok=True)
    with args.strings_out.open("w") as f:
        f.write("# DRAFT — not approved. One row per distinct NTSB make_model string.\n")
        for row in string_rows:
            f.write(json.dumps(row) + "\n")

    with args.incidents_out.open("w") as f:
        f.write("# DRAFT — auto-derived from string mapping. Reference only.\n")
        for row in incident_rows:
            f.write(json.dumps(row) + "\n")

    tbd = [r for r in string_rows if r["proposed_aircraft_page"] == "TBD"]
    pages = defaultdict(int)
    for r in string_rows:
        pages[r["proposed_aircraft_page"]] += r["incident_count"]

    print(f"strings: {len(string_rows)} -> {args.strings_out}")
    print(f"incidents: {len(incident_rows)} -> {args.incidents_out}")
    print(f"TBD strings: {len(tbd)} ({sum(r['incident_count'] for r in tbd)} incidents)")
    if tbd:
        print("remaining TBD:")
        for r in sorted(tbd, key=lambda x: -x["incident_count"])[:15]:
            print(f"  {r['incident_count']:3d}  {r['ntsb_make_model']!r}")


if __name__ == "__main__":
    main()
