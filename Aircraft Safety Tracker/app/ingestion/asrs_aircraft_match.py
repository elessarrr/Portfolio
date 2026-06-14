"""Map ASRS make/model strings to catalog Aircraft rows."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_ALNUM = re.compile(r"[^A-Z0-9]")
_BOEING = re.compile(r"(?:BOEING|B)[\s-]*(\d{3})[\s-]*(\d)?", re.I)
_AIRBUS = re.compile(r"(?:AIRBUS|A)[\s-]*(A\d{3})", re.I)


@dataclass(frozen=True)
class AircraftIndexEntry:
    aircraft_id: int
    manufacturer: str
    model_name: str
    series_key: str
    family_key: str


def _compact(value: str) -> str:
    return _ALNUM.sub("", (value or "").upper())


def _series_and_family(manufacturer: str, model_name: str) -> tuple[str, str]:
    suffix = model_name
    if model_name.upper().startswith(manufacturer.upper()):
        suffix = model_name[len(manufacturer) :].strip()
    compact = _compact(suffix)
    family = compact[:4] if compact.startswith("A") else compact[:3]
    return compact, family


def build_aircraft_index(aircraft_rows) -> list[AircraftIndexEntry]:
    entries: list[AircraftIndexEntry] = []
    for ac in aircraft_rows:
        series, family = _series_and_family(ac.manufacturer or "", ac.model_name or "")
        entries.append(
            AircraftIndexEntry(
                aircraft_id=ac.id,
                manufacturer=(ac.manufacturer or "").upper(),
                model_name=ac.model_name or "",
                series_key=series,
                family_key=family,
            )
        )
    return entries


def load_asrs_overrides(path: Path) -> dict[str, int | None]:
    """JSONL: {"asrs_make_model": "B737-800", "canonical_model_name": "Boeing 737-800", "action": "map_to_existing"|"skip"}"""
    if not path.is_file():
        return {}
    from app.models import Aircraft

    by_name = {a.model_name: a.id for a in Aircraft.query.all()}
    overrides: dict[str, int | None] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = json.loads(line)
        key = _compact(row.get("asrs_make_model", ""))
        if row.get("action") == "skip":
            overrides[key] = None
            continue
        canonical = row.get("canonical_model_name")
        if canonical and canonical in by_name:
            overrides[key] = by_name[canonical]
    return overrides


def match_asrs_make_model(
    raw: str,
    index: list[AircraftIndexEntry],
    overrides: dict[str, int | None] | None = None,
) -> int | None:
    text = (raw or "").strip()
    if not text:
        return None

    key = _compact(text)
    if overrides and key in overrides:
        return overrides[key]

    asrs_compact = key
    candidates: list[tuple[int, int]] = []

    for entry in index:
        score = 0
        if asrs_compact == entry.series_key:
            score = 100
        elif entry.series_key and entry.series_key in asrs_compact:
            score = len(entry.series_key) + 10
        elif asrs_compact in entry.series_key:
            score = len(asrs_compact) + 5
        else:
            score = _fuzzy_family_score(text, entry)

        if score > 0:
            candidates.append((score, entry.aircraft_id))

    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    best_score = candidates[0][0]
    if best_score < 8:
        return None
    return candidates[0][1]


def _fuzzy_family_score(asrs_raw: str, entry: AircraftIndexEntry) -> int:
    upper = asrs_raw.upper()
    if entry.manufacturer.startswith("AIRBUS") or entry.series_key.startswith("A"):
        m = _AIRBUS.search(upper)
        if m and _compact(m.group(1)) == entry.family_key:
            return 12
    if entry.manufacturer.startswith("BOEING") or re.search(r"\bB?\d{3}", upper):
        m = _BOEING.search(upper)
        if not m:
            return 0
        series = m.group(1)
        variant_digit = m.group(2) or ""
        if series != entry.family_key:
            return 0
        if not variant_digit:
            return 8
        if entry.series_key and variant_digit == entry.series_key[3:4]:
            return 14
        return 10
    return 0
