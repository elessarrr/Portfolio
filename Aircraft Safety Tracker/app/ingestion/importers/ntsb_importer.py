"""NTSB → IncidentSource importer (Boeing/Airbus only, single source_url)."""

from __future__ import annotations

import datetime
from typing import Any, Dict, Iterable, List, Optional

from app import db
from app.ingestion.importers.base import is_boeing_or_airbus_make_model, resolve_boeing_airbus_aircraft_id
from app.ingestion.link_schema import assert_source_data_metadata_only, assert_valid_source_url
from app.ingestion.url_builders.ntsb import resolve_ntsb_source_url
from app.models import Incident, IncidentSource


class NTSBImporter:
    source_name = "NTSB"

    def __init__(self, records: Optional[Iterable[Dict[str, Any]]] = None):
        self._records = list(records or [])

    def run(self) -> int:
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

        source_url = parsed.get("source_url")
        if source_url:
            assert_valid_source_url(source_url)

        if existing:
            existing.source_url = source_url
            existing.source_data = source_data
            existing.is_active = True
            incident = existing.incident
        else:
            aircraft_id = resolve_boeing_airbus_aircraft_id(parsed.get("make_model"))
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

    def parse(self, raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(raw_record, dict):
            return None

        vehicles = raw_record.get("cm_vehicles") or []
        vehicle = vehicles[0] if vehicles else {}
        make = vehicle.get("make") or ""
        model = vehicle.get("model") or ""
        make_model = f"{make} {model}".strip() if make or model else raw_record.get("make_model")
        if not is_boeing_or_airbus_make_model(make_model):
            return None

        parsed_date = self._parse_date(
            raw_record.get("cm_eventDate") or raw_record.get("event_date") or raw_record.get("date")
        )
        if not parsed_date:
            return None

        ntsb_num = (raw_record.get("cm_ntsbNum") or raw_record.get("ntsb_id") or "").strip()
        if not ntsb_num:
            return None

        source_data = {k: v for k, v in raw_record.items() if k != "links"}
        source_url = resolve_ntsb_source_url(ntsb_num, source_data)

        location = f"{raw_record.get('cm_city', '')}, {raw_record.get('cm_state', '')}".strip(", ")
        if not location:
            location = raw_record.get("location")

        description = (
            raw_record.get("analysisNarrative")
            or raw_record.get("factualNarrative")
            or raw_record.get("prelimNarrative")
            or raw_record.get("description")
        )
        if description == "-":
            description = None

        return {
            "source_record_id": ntsb_num,
            "date": parsed_date,
            "location": location or None,
            "operator": (vehicle.get("operatorName") or raw_record.get("operator") or "").strip() or None,
            "fatalities": self._parse_int(raw_record.get("cm_fatalInjuryCount") or raw_record.get("fatalities")),
            "description": (description or "").strip() or None,
            "make_model": make_model,
            "source_url": source_url,
            "source_data": source_data,
        }

    def _parse_date(self, value) -> Optional[datetime.date]:
        if isinstance(value, datetime.date):
            return value
        if not value:
            return None
        text = str(value).strip()
        if "T" in text:
            text = text.split("T")[0]
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_int(self, value) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
