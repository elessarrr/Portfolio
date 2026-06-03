"""FAA AIDS make_model → aircraft page mapping (PRD 0007 FR-5)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app import db
from app.models import Aircraft

logger = logging.getLogger(__name__)

VALID_ACTIONS = frozenset({"map_to_existing", "create_approved", "skip"})


@dataclass(frozen=True)
class FaaAidsMappingEntry:
    faa_make_model: str
    canonical_model_name: str
    action: str
    canonical_aircraft_id: Optional[int] = None
    manufacturer: Optional[str] = None
    notes: Optional[str] = None


class FaaAidsMakeModelMapping:
    """Pre-import gate: FAA AIDS make_model string → catalog Aircraft row."""

    def __init__(self, entries: Dict[str, FaaAidsMappingEntry]):
        self._entries = entries

    @classmethod
    def load(cls, path: Path | str) -> "FaaAidsMakeModelMapping":
        path = Path(path)
        entries: Dict[str, FaaAidsMappingEntry] = {}
        with path.open(encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
                entry = _parse_entry(raw, path, line_no)
                if entry.faa_make_model in entries:
                    raise ValueError(
                        f"{path}:{line_no}: duplicate faa_make_model {entry.faa_make_model!r}"
                    )
                entries[entry.faa_make_model] = entry
        if not entries:
            raise ValueError(f"{path}: no mapping entries")
        return cls(entries)

    def get(self, faa_make_model: str) -> Optional[FaaAidsMappingEntry]:
        return self._entries.get(faa_make_model)

    def __len__(self) -> int:
        return len(self._entries)

    def resolve_aircraft_id(self, faa_make_model: str) -> Optional[int]:
        entry = self.get(faa_make_model)
        if entry is None:
            return None
        if entry.action == "skip":
            return None
        if entry.action == "map_to_existing":
            return _lookup_by_model_name(entry.canonical_model_name) or _lookup_by_id(
                entry.canonical_aircraft_id
            )
        if entry.action == "create_approved":
            return _get_or_create_approved(entry)
        logger.warning("unknown mapping action %r for %r", entry.action, faa_make_model)
        return None

    def lookup_aircraft_id_only(self, faa_make_model: str) -> Optional[int]:
        """Lookup-only for dedupe/bootstrap planning — never creates Aircraft rows."""
        entry = self.get(faa_make_model)
        if entry is None or entry.action == "skip":
            return None
        if entry.action == "map_to_existing":
            return _lookup_by_model_name(entry.canonical_model_name) or _lookup_by_id(
                entry.canonical_aircraft_id
            )
        if entry.action == "create_approved":
            return _lookup_by_model_name(entry.canonical_model_name)
        return None


def load_faa_aids_make_model_mapping(path: Path | str) -> FaaAidsMakeModelMapping:
    return FaaAidsMakeModelMapping.load(path)


def iter_create_approved_targets(
    mapping: FaaAidsMakeModelMapping,
) -> Dict[str, FaaAidsMappingEntry]:
    targets: Dict[str, FaaAidsMappingEntry] = {}
    for entry in mapping._entries.values():
        if entry.action != "create_approved":
            continue
        if entry.canonical_model_name not in targets:
            targets[entry.canonical_model_name] = entry
    return targets


def bootstrap_create_approved_pages(
    mapping: FaaAidsMakeModelMapping,
    *,
    dry_run: bool = False,
) -> Dict[str, object]:
    targets = iter_create_approved_targets(mapping)
    created: List[Dict[str, object]] = []
    already_existed: List[Dict[str, object]] = []

    for model_name in sorted(targets):
        entry = targets[model_name]
        _validate_boeing_airbus_page_name(model_name)

        existing_id = _lookup_by_model_name(model_name)
        if existing_id is not None:
            already_existed.append(
                {
                    "aircraft_id": existing_id,
                    "canonical_model_name": model_name,
                    "manufacturer": entry.manufacturer,
                }
            )
            continue

        if dry_run:
            created.append(
                {
                    "aircraft_id": None,
                    "canonical_model_name": model_name,
                    "manufacturer": entry.manufacturer,
                }
            )
            continue

        aircraft_id = _get_or_create_approved(entry)
        created.append(
            {
                "aircraft_id": aircraft_id,
                "canonical_model_name": model_name,
                "manufacturer": entry.manufacturer,
            }
        )

    if not dry_run and created:
        db.session.commit()

    return {
        "dry_run": dry_run,
        "target_count": len(targets),
        "created_count": len(created),
        "already_existed_count": len(already_existed),
        "created": created,
        "already_existed": already_existed,
    }


def _validate_boeing_airbus_page_name(model_name: str) -> None:
    if "Boeing" not in model_name and "Airbus" not in model_name:
        raise ValueError(
            f"canonical_model_name must contain Boeing or Airbus (FR-23): {model_name!r}"
        )


def _parse_entry(raw: dict, path: Path, line_no: int) -> FaaAidsMappingEntry:
    required = ("faa_make_model", "canonical_model_name", "action")
    for key in required:
        if key not in raw:
            raise ValueError(f"{path}:{line_no}: missing {key}")
    action = raw["action"]
    if action not in VALID_ACTIONS:
        raise ValueError(f"{path}:{line_no}: invalid action {action!r}")
    canonical_id = raw.get("canonical_aircraft_id")
    if canonical_id is not None and not isinstance(canonical_id, int):
        raise ValueError(f"{path}:{line_no}: canonical_aircraft_id must be int or null")
    manufacturer = raw.get("manufacturer")
    if action == "create_approved" and not manufacturer:
        raise ValueError(
            f"{path}:{line_no}: create_approved requires manufacturer for {raw['faa_make_model']!r}"
        )
    return FaaAidsMappingEntry(
        faa_make_model=raw["faa_make_model"],
        canonical_model_name=raw["canonical_model_name"],
        action=action,
        canonical_aircraft_id=canonical_id,
        manufacturer=manufacturer,
        notes=raw.get("notes"),
    )


def _lookup_by_model_name(model_name: str) -> Optional[int]:
    aircraft = Aircraft.query.filter_by(model_name=model_name).first()
    return aircraft.id if aircraft else None


def _lookup_by_id(aircraft_id: Optional[int]) -> Optional[int]:
    if aircraft_id is None:
        return None
    aircraft = db.session.get(Aircraft, aircraft_id)
    return aircraft.id if aircraft else None


def _get_or_create_approved(entry: FaaAidsMappingEntry) -> Optional[int]:
    existing_id = _lookup_by_model_name(entry.canonical_model_name)
    if existing_id is not None:
        return existing_id
    manufacturer = entry.manufacturer or "Boeing"
    aircraft = Aircraft(manufacturer=manufacturer, model_name=entry.canonical_model_name)
    db.session.add(aircraft)
    db.session.flush()
    return aircraft.id
