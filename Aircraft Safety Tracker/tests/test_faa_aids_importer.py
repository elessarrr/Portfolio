"""FAA AIDS importer tests (PRD 0007 FR-12.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import db
from app.ingestion.importers.faa_aids_importer import FAAAIDSImporter
from app.ingestion.link_schema import is_catalog_url
from app.models import Aircraft, Incident, IncidentSource


def _write_mapping(tmp_path: Path) -> Path:
    path = tmp_path / "mapping.jsonl"
    path.write_text(
        "# test\n"
        + json.dumps(
            {
                "faa_make_model": "BOEING 737-800",
                "canonical_model_name": "Boeing 737-800",
                "action": "map_to_existing",
            }
        )
        + "\n"
    )
    return path


def _valid_row(**overrides):
    row = {
        "c5": "20050316X00394",
        "c9": "03/16/2005",
        "c23": "BOEING",
        "c24": "737-800",
        "c26": "Test Air",
        "c28": "Seattle",
        "c29": "WA",
        "c34": "0",
        "c44": "Test narrative",
    }
    row.update(overrides)
    return row


def test_parse_valid_boeing_row():
    parsed = FAAAIDSImporter.parse(_valid_row())
    assert parsed is not None
    assert parsed["source_record_id"] == "20050316X00394"
    assert parsed["faa_make_model"] == "BOEING 737-800"
    assert parsed["fatalities"] == 0
    assert "P12_AIDS_RPRT_NBR" in parsed["source_url"]


def test_parse_non_boeing_returns_none():
    assert FAAAIDSImporter.parse(_valid_row(c23="CESSNA", c24="172")) is None


def test_parse_empty_c5_returns_none():
    assert FAAAIDSImporter.parse(_valid_row(c5="")) is None


def test_parse_invalid_date_returns_none():
    assert FAAAIDSImporter.parse(_valid_row(c9="not-a-date")) is None


def test_parse_null_fatalities_coerced_to_zero():
    parsed = FAAAIDSImporter.parse(_valid_row(c34=""))
    assert parsed["fatalities"] == 0


def test_upsert_mapped_inserts(app, tmp_path):
    with app.app_context():
        aircraft = Aircraft(manufacturer="Boeing", model_name="Boeing 737-800")
        db.session.add(aircraft)
        db.session.commit()
        mapping = _write_mapping(tmp_path)
        assert FAAAIDSImporter(records=[_valid_row()], mapping=mapping).run() == 1
        assert IncidentSource.query.filter_by(source_name="FAA_AIDS").count() == 1


def test_upsert_unmapped_skipped(app, tmp_path):
    with app.app_context():
        mapping = _write_mapping(tmp_path)
        importer = FAAAIDSImporter(
            records=[_valid_row(c24="757-200")],
            mapping=mapping,
        )
        assert importer.run() == 0
        assert importer.skipped_unmapped


def test_upsert_idempotent(app, tmp_path):
    with app.app_context():
        aircraft = Aircraft(manufacturer="Boeing", model_name="Boeing 737-800")
        db.session.add(aircraft)
        db.session.commit()
        mapping = _write_mapping(tmp_path)
        row = _valid_row()
        first = FAAAIDSImporter(records=[row], mapping=mapping).run()
        second = FAAAIDSImporter(records=[row], mapping=mapping).run()
        assert first == 1
        assert second == 1
        assert IncidentSource.query.filter_by(source_name="FAA_AIDS").count() == 1
        assert Incident.query.count() == 1


def test_source_data_has_faa_make_model_no_links(app, tmp_path):
    with app.app_context():
        aircraft = Aircraft(manufacturer="Boeing", model_name="Boeing 737-800")
        db.session.add(aircraft)
        db.session.commit()
        FAAAIDSImporter(records=[_valid_row()], mapping=_write_mapping(tmp_path)).run()
        source = IncidentSource.query.one()
        assert source.source_data.get("faa_aids_make_model") == "BOEING 737-800"
        assert "links" not in (source.source_data or {})


def test_source_url_not_catalog():
    parsed = FAAAIDSImporter.parse(_valid_row())
    assert not is_catalog_url(parsed["source_url"])
