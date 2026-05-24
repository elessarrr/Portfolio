"""Seed and validate aircraft_family_member rules from CSV."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from app import db
from app.models import Aircraft, AircraftFamilyMember, Incident, IncidentSource
from app.services.aircraft_family import clear_family_member_cache, get_family_member_ids

DEFAULT_CSV = Path("data/aircraft_family_members.csv")

# Phase 1 family heads: explicit id + model-name matching rules for CSV generation.
# Each member aircraft maps to at most one family (FR-3.3).
FAMILY_DEFINITIONS: List[Dict] = [
    {"family_id": 88, "label": "BOEING 737-300", "include": [r"737-3", r"7373"], "exclude": [r"737-37", r"73737"]},
    {"family_id": 206, "label": "Boeing 737-400", "include": [r"737-4", r"7374"], "exclude": [r"737-47", r"73747"]},
    {"family_id": 185, "label": "Boeing 737-500", "include": [r"737-5", r"7375"], "exclude": []},
    {
        "family_id": 172,
        "label": "Boeing 737-700",
        "include": [r"737-7"],
        "exclude": [r"737-79", r"737-7bd", r"737-7ct", r"737-7max", r"737-8", r"737-9", r"7378", r"7379", r"max"],
    },
    {
        "family_id": 49,
        "label": "Boeing 737-800",
        "include": [r"737-8", r"7378"],
        "exclude": [r"737-89", r"737-8max", r"737-8 max", r"737 max", r"737-9", r"7379", r"737-7"],
    },
    {
        "family_id": 48,
        "label": "Boeing 737 MAX family",
        "include": [r"737 max", r"737-7 max", r"737-8 max", r"737-8max", r"737-9 max", r"737-9max", r"737-7m", r"737-8m", r"737-9m"],
        "exclude": [],
    },
    {"family_id": 97, "label": "BOEING 727", "include": [r"727"], "exclude": [r"72777"]},
    {"family_id": 77, "label": "BOEING 757", "include": [r"757"], "exclude": []},
    {"family_id": 70, "label": "BOEING 747", "include": [r"747"], "exclude": []},
    {"family_id": 212, "label": "Boeing 767", "include": [r"767"], "exclude": []},
    {"family_id": 194, "label": "Boeing 777", "include": [r"777"], "exclude": [r"72777"]},
    {"family_id": 18, "label": "Airbus A320", "include": [r"a320"], "exclude": [r"a3200"]},
    {"family_id": 25, "label": "Airbus A330-300", "include": [r"a330"], "exclude": [r"a3300"]},
    {"family_id": 33, "label": "Airbus A350", "include": [r"a350"], "exclude": []},
    {"family_id": 36, "label": "Airbus A380", "include": [r"a380"], "exclude": []},
]


def _normalize_model(model_name: str, manufacturer: str) -> str:
    text = (model_name or "").strip().lower()
    mfr = (manufacturer or "").strip().lower()
    if mfr and text.startswith(mfr):
        text = text[len(mfr) :].strip()
    text = re.sub(r"[^a-z0-9\- ]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _matches_rules(normalized: str, include: Iterable[str], exclude: Iterable[str]) -> bool:
    if not any(re.search(pat, normalized) for pat in include):
        return False
    if any(re.search(pat, normalized) for pat in exclude):
        return False
    return True


def propose_family_members() -> List[Tuple[int, int]]:
    """Build explicit (family_id, member_id) pairs from FAMILY_DEFINITIONS."""
    claimed_members: Set[int] = set()
    pairs: List[Tuple[int, int]] = []

    aircraft_rows = Aircraft.query.filter(
        db.func.upper(Aircraft.manufacturer).in_(["BOEING", "AIRBUS"])
    ).order_by(Aircraft.id).all()

    for family in FAMILY_DEFINITIONS:
        family_id = family["family_id"]
        head = db.session.get(Aircraft, family_id)
        if not head:
            continue
        family_members: Set[int] = {family_id}
        for ac in aircraft_rows:
            normalized = _normalize_model(ac.model_name, ac.manufacturer)
            if not _matches_rules(normalized, family["include"], family["exclude"]):
                continue
            if ac.id in claimed_members and ac.id not in family_members:
                continue
            family_members.add(ac.id)
        for member_id in sorted(family_members):
            if member_id != family_id and member_id in claimed_members:
                continue
            pairs.append((family_id, member_id))
            claimed_members.add(member_id)
    return pairs


def write_seed_csv(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    pairs = propose_family_members()
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["family_aircraft_id", "member_aircraft_id"])
        for family_id, member_id in pairs:
            writer.writerow([family_id, member_id])
    return len(pairs)


@dataclass
class SeedSummary:
    families: Dict[str, Dict] = field(default_factory=dict)
    row_count: int = 0
    errors: List[str] = field(default_factory=list)


def _faa_count_for_ids(aircraft_ids: Iterable[int]) -> int:
    ids = list(aircraft_ids)
    if not ids:
        return 0
    return (
        db.session.query(db.func.count(db.distinct(Incident.id)))
        .join(IncidentSource)
        .filter(
            Incident.aircraft_id.in_(ids),
            IncidentSource.source_name == "FAA_AIDS",
            IncidentSource.source_url.like("%asias%"),
        )
        .scalar()
        or 0
    )


def _incident_count_for_ids(aircraft_ids: Iterable[int]) -> int:
    ids = list(aircraft_ids)
    if not ids:
        return 0
    return Incident.query.filter(Incident.aircraft_id.in_(ids)).count()


def load_csv_rows(path: Path) -> List[Tuple[int, int]]:
    rows: List[Tuple[int, int]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for line in reader:
            family_id = int(line["family_aircraft_id"])
            member_id = int(line["member_aircraft_id"])
            rows.append((family_id, member_id))
    return rows


def validate_rows(rows: List[Tuple[int, int]]) -> SeedSummary:
    summary = SeedSummary(row_count=len(rows))
    seen_members: Set[int] = set()
    for family_id, member_id in rows:
        family = db.session.get(Aircraft, family_id)
        member = db.session.get(Aircraft, member_id)
        if not family or not member:
            summary.errors.append(f"missing aircraft family={family_id} member={member_id}")
            continue
        f_mfr = (family.manufacturer or "").upper()
        m_mfr = (member.manufacturer or "").upper()
        if f_mfr not in ("BOEING", "AIRBUS") or m_mfr not in ("BOEING", "AIRBUS"):
            summary.errors.append(f"non Boeing/Airbus family={family_id} member={member_id}")
        if f_mfr != m_mfr:
            summary.errors.append(f"manufacturer mismatch family={family_id} member={member_id}")
        if member_id in seen_members and member_id != family_id:
            summary.errors.append(f"duplicate member mapping member={member_id}")
        seen_members.add(member_id)

        key = str(family_id)
        if key not in summary.families:
            direct_ids = [member_id] if member_id == family_id else []
            summary.families[key] = {
                "family_model": family.model_name,
                "member_ids": [],
                "before_direct_incidents": _incident_count_for_ids([family_id]),
                "before_direct_faa": _faa_count_for_ids([family_id]),
            }
        summary.families[key]["member_ids"].append(member_id)

    for family_id, data in summary.families.items():
        member_ids = sorted(set(int(x) for x in data["member_ids"]))
        data["member_ids"] = member_ids
        data["after_rollup_incidents"] = _incident_count_for_ids(member_ids)
        data["after_rollup_faa"] = _faa_count_for_ids(member_ids)
    return summary


def apply_rows(rows: List[Tuple[int, int]], *, replace: bool = True) -> None:
    if replace:
        AircraftFamilyMember.query.delete()
        db.session.commit()
        clear_family_member_cache()
    now = datetime.utcnow()
    for family_id, member_id in rows:
        db.session.add(
            AircraftFamilyMember(
                family_aircraft_id=family_id,
                member_aircraft_id=member_id,
                created_at=now,
            )
        )
    db.session.commit()
    clear_family_member_cache()


def run_seed(*, csv_path: Path, dry_run: bool, replace: bool = True) -> SeedSummary:
    if not csv_path.exists():
        write_seed_csv(csv_path)
    rows = load_csv_rows(csv_path)
    summary = validate_rows(rows)
    if summary.errors:
        return summary
    if not dry_run:
        apply_rows(rows, replace=replace)
        for family_id, data in summary.families.items():
            data["live_member_ids"] = get_family_member_ids(int(family_id))
    return summary


def summary_to_json(summary: SeedSummary) -> str:
    payload = asdict(summary)
    return json.dumps(payload, indent=2)
