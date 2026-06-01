"""Tests for NTSB bulk import (FR-21)."""

from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

from app import db
from app.ingestion.importers.ntsb_importer import NTSBImporter
from app.models import Aircraft, Incident, IncidentSource

ROOT = Path(__file__).resolve().parents[1]
BULK_SCRIPT = ROOT / "scripts/ntsb_bulk_import.py"


def _load_bulk_module():
    spec = importlib.util.spec_from_file_location("ntsb_bulk_import", BULK_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_import_candidates_filters_status():
    bulk = _load_bulk_module()
    rows = [
        {"source_record_id": "A", "dedupe_repasse_status": "import"},
        {"source_record_id": "B", "dedupe_repasse_status": "skip_asn_covered"},
    ]
    assert len(bulk.import_candidates(rows)) == 1


def test_bulk_import_idempotent_with_mapping(app, tmp_path):
    bulk = _load_bulk_module()
    mapping_path = tmp_path / "mapping.jsonl"
    mapping_path.write_text(
        "# test\n"
        + json.dumps(
            {
                "ntsb_make_model": "Boeing 737-800",
                "canonical_aircraft_id": None,
                "canonical_model_name": "Boeing 737-800",
                "action": "map_to_existing",
                "manufacturer": "Boeing",
            }
        )
        + "\n"
    )

    with app.app_context():
        aircraft = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737-800",
            total_incidents=0,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add(aircraft)
        db.session.commit()

        raw = {
            "cm_ntsbNum": "ENG20FA010",
            "cm_eventDate": "2020-06-15",
            "cm_vehicles": [{"make": "Boeing", "model": "737-800"}],
        }
        audit_row = {
            "source_record_id": "ENG20FA010",
            "ntsb_url": "https://data.ntsb.gov/Docket/?NTSBNumber=ENG20FA010",
            "mapped_aircraft_id": aircraft.id,
            "make_model": "Boeing 737-800",
        }

        # Patch mapping loader target by writing real mapping with aircraft id
        mapping_path.write_text(
            "# test\n"
            + json.dumps(
                {
                    "ntsb_make_model": "Boeing 737-800",
                    "canonical_aircraft_id": aircraft.id,
                    "canonical_model_name": "Boeing 737-800",
                    "action": "map_to_existing",
                    "manufacturer": "Boeing",
                }
            )
            + "\n"
        )

        candidates = [audit_row]
        full_index = {"ENG20FA010": raw}

        first = bulk.run_bulk_import(candidates, full_index, mapping_path)
        second = bulk.run_bulk_import(candidates, full_index, mapping_path)

        assert first["written"] == 1
        assert first["ntsb_sources_created"] == 1
        assert second["written"] == 1
        assert second["ntsb_sources_created"] == 0
        assert second["incidents_created"] == 0
        assert IncidentSource.query.filter_by(source_name="NTSB").count() == 1
        assert Incident.query.count() == 1

        source = IncidentSource.query.filter_by(
            source_name="NTSB", source_record_id="ENG20FA010"
        ).one()
        assert source.source_data.get("ntsb_make_model") == "Boeing 737-800"

        db.session.refresh(aircraft)
        assert aircraft.total_incidents == 1
