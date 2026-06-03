"""FAA AIDS → IncidentSource importer (Boeing/Airbus only, URL at import time)."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from app import db
from app.ingestion.dedupe.ntsb_asn import fatalities_like_import
from app.ingestion.faa_aids_mapping import FaaAidsMakeModelMapping, load_faa_aids_make_model_mapping
from app.ingestion.importers.base import (
    is_boeing_or_airbus_make_model,
    resolve_boeing_airbus_aircraft_id,
)
from app.ingestion.link_schema import assert_source_data_metadata_only, assert_valid_source_url
from app.ingestion.url_builders.faa_aids import build_faa_aids_url
from app.models import Incident, IncidentSource


class FAAAIDSImporter:
    source_name = "FAA_AIDS"

    def __init__(
        self,
        records: Optional[Iterable[Dict[str, Any]]] = None,
        *,
        mapping: Optional[Union[FaaAidsMakeModelMapping, str, Path]] = None,
    ):
        self._records = list(records or [])
        if isinstance(mapping, (str, Path)):
            mapping = load_faa_aids_make_model_mapping(mapping)
        self._mapping = mapping
        self.skipped_unmapped: List[str] = []
        self.skipped_unresolved: List[str] = []
        self.skipped_action_skip: List[str] = []

    def run(self) -> int:
        self.skipped_unmapped.clear()
        self.skipped_unresolved.clear()
        self.skipped_action_skip.clear()
        written = 0
        for raw in self._records:
            if self.upsert(raw):
                written += 1
        db.session.commit()
        return written

    def upsert(self, raw_record: Dict[str, Any]) -> bool:
        parsed = self.parse(raw_record)
        if not parsed:
            return False

        source_record_id = parsed["source_record_id"]
        existing = IncidentSource.query.filter_by(
            source_name=self.source_name,
            source_record_id=source_record_id,
        ).first()

        source_data = parsed["source_data"]
        assert_source_data_metadata_only(source_data)
        source_data["faa_aids_make_model"] = parsed.get("faa_make_model")

        source_url = parsed.get("source_url")
        assert_valid_source_url(source_url)

        if existing:
            existing.source_url = source_url
            existing.source_data = source_data
            existing.is_active = True
            incident = existing.incident
        else:
            aircraft_id = self._resolve_aircraft_id(parsed.get("faa_make_model"))
            if aircraft_id is None:
                return False
            incident = Incident(
                aircraft_id=aircraft_id,
                date=parsed["date"],
                operator=parsed.get("operator"),
                location=parsed.get("location"),
                fatalities=parsed.get("fatalities") or 0,
                description=parsed.get("description"),
                incident_type="Accident",
            )
            db.session.add(incident)
            db.session.flush()
            existing = IncidentSource(
                incident_id=incident.id,
                source_name=self.source_name,
                source_record_id=source_record_id,
                source_url=source_url,
                source_data=source_data,
                is_active=True,
            )
            db.session.add(existing)

        incident.operator = parsed.get("operator") or incident.operator
        incident.location = parsed.get("location") or incident.location
        if parsed.get("fatalities") is not None:
            incident.fatalities = parsed.get("fatalities")
        incident.description = parsed.get("description") or incident.description
        return True

    def _resolve_aircraft_id(self, faa_make_model: Optional[str]) -> Optional[int]:
        if self._mapping is not None:
            if not faa_make_model:
                self.skipped_unmapped.append("")
                return None
            entry = self._mapping.get(faa_make_model)
            if entry is None:
                self.skipped_unmapped.append(faa_make_model)
                return None
            if entry.action == "skip":
                self.skipped_action_skip.append(faa_make_model)
                return None
            aircraft_id = self._mapping.resolve_aircraft_id(faa_make_model)
            if aircraft_id is None:
                self.skipped_unresolved.append(faa_make_model)
            return aircraft_id
        return resolve_boeing_airbus_aircraft_id(faa_make_model)

    @staticmethod
    def parse(raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(raw_record, dict):
            return None

        c5 = str(raw_record.get("c5") or "").strip()
        if not c5:
            return None

        make = str(raw_record.get("c23") or "").strip()
        model = str(raw_record.get("c24") or "").strip()
        faa_make_model = f"{make} {model}".strip() if model else make
        if not is_boeing_or_airbus_make_model(faa_make_model):
            return None

        parsed_date = FAAAIDSImporter._parse_date(raw_record.get("c9"))
        if not parsed_date:
            return None

        source_url = build_faa_aids_url(c5)
        if not source_url:
            return None

        city = str(raw_record.get("c28") or "").strip()
        state = str(raw_record.get("c29") or "").strip()
        location = f"{city}, {state}".strip(", ") or None

        description = raw_record.get("c44") or raw_record.get("description")
        if description == "-":
            description = None

        source_data = {k: v for k, v in raw_record.items() if k != "links"}

        return {
            "source_record_id": c5,
            "date": parsed_date,
            "location": location,
            "operator": str(raw_record.get("c26") or "").strip() or None,
            "fatalities": fatalities_like_import(FAAAIDSImporter._parse_int(raw_record.get("c34"))),
            "description": (str(description).strip() if description else None) or None,
            "faa_make_model": faa_make_model,
            "source_url": source_url,
            "source_data": source_data,
        }

    @staticmethod
    def _parse_date(value) -> Optional[datetime.date]:
        if isinstance(value, datetime.date):
            return value
        if not value:
            return None
        text = str(value).strip()
        if "T" in text:
            text = text.split("T")[0]
        if len(text) == 8 and text.isdigit():
            try:
                return datetime.datetime.strptime(text, "%Y%m%d").date()
            except ValueError:
                pass
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
            try:
                return datetime.datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_int(value) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
