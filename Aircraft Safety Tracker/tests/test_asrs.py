import json
from pathlib import Path

import pytest

from app.ingestion.asrs_aircraft_match import (
    build_aircraft_index,
    match_asrs_make_model,
)
from app.ingestion.asrs_import import import_asrs_rows, iter_csv_rows
from app.models import Aircraft, AsrsReport
from app.services.asrs import get_asrs_profile, normalize_factor_bucket

FIXTURE_CSV = Path(__file__).parent / "fixtures" / "asrs_sample.csv"


@pytest.fixture
def boeing_737_800(app):
    ac = Aircraft(
        manufacturer="Boeing",
        model_name="Boeing 737-800",
        years_in_service=25,
        total_incidents=5,
    )
    from app import db

    db.session.add(ac)
    db.session.commit()
    return ac


def test_normalize_factor_bucket():
    assert normalize_factor_bucket("Human Factors") == "Human Factors"
    assert normalize_factor_bucket("Aircraft Equipment Problem Critical") == "Aircraft Equipment"
    assert normalize_factor_bucket("Weather / Turbulence") == "Weather/Environment"


def test_match_asrs_make_model(boeing_737_800):
    index = build_aircraft_index([boeing_737_800])
    assert match_asrs_make_model("B737-800", index) == boeing_737_800.id
    assert match_asrs_make_model("BOEING 737-824", index) == boeing_737_800.id


def test_get_asrs_profile_aggregates(boeing_737_800):
    from app import db

    for i, (problem, factors) in enumerate(
        [
            ("Human Factors", ["Human Factors", "Procedure"]),
            ("Aircraft Equipment Problem", ["Aircraft Equipment"]),
            ("Human Factors", ["Human Factors"]),
        ]
    ):
        db.session.add(
            AsrsReport(
                acn=f"100000{i}",
                aircraft_make_model_raw="B737-800",
                primary_problem=problem,
                contributing_factors=json.dumps(factors),
                aircraft_id=boeing_737_800.id,
                source="test",
            )
        )
    db.session.commit()

    profile = get_asrs_profile(boeing_737_800.id)
    assert profile is not None
    assert profile["n"] == 3
    assert profile["contributing_factors"]["Human Factors"] == pytest.approx(66.7, abs=0.2)
    assert profile["limited_data"] is True
    assert len(profile["top_event_types"]) >= 1


def test_get_asrs_profile_none_when_empty(boeing_737_800):
    assert get_asrs_profile(boeing_737_800.id) is None


def test_aircraft_page_shows_asrs_card(client, boeing_737_800):
    from app import db

    db.session.add(
        AsrsReport(
            acn="9999991",
            aircraft_make_model_raw="B737-800",
            primary_problem="Human Factors",
            contributing_factors=json.dumps(["Human Factors"]),
            aircraft_id=boeing_737_800.id,
            source="test",
        )
    )
    db.session.commit()

    response = client.get(f"/aircraft/{boeing_737_800.id}")
    assert response.status_code == 200
    assert b"Crew Safety Reports" in response.data
    assert b"n = 1 reports" in response.data
    assert b"% of reports mentioning" in response.data


def test_import_csv_dry_run(boeing_737_800):
    rows = list(iter_csv_rows(FIXTURE_CSV))
    stats = import_asrs_rows(rows, apply=False)
    assert stats.seen == 2
    assert stats.imported == 2
    assert stats.duplicate == 0
    assert AsrsReport.query.count() == 0


def test_import_csv_apply_and_idempotent(boeing_737_800):
    rows = list(iter_csv_rows(FIXTURE_CSV))
    first = import_asrs_rows(rows, apply=True)
    assert first.imported == 2
    assert AsrsReport.query.count() == 2
    assert all(r.aircraft_id == boeing_737_800.id for r in AsrsReport.query.all())

    second = import_asrs_rows(rows, apply=True)
    assert second.duplicate == 2
    assert second.imported == 0
    assert AsrsReport.query.count() == 2


def test_remap_fixes_boeing_40_false_positive(app):
    from app import db
    from app.ingestion.asrs_remap import remap_asrs_aircraft_ids

    bo40 = Aircraft(
        manufacturer="Boeing",
        model_name="Boeing 40",
        years_in_service=50,
        total_incidents=0,
    )
    b737_400 = Aircraft(
        manufacturer="Boeing",
        model_name="Boeing 737-400",
        years_in_service=25,
        total_incidents=0,
    )
    db.session.add_all([bo40, b737_400])
    db.session.commit()

    report = AsrsReport(
        acn="7777001",
        aircraft_make_model_raw="B737-400",
        primary_problem="Human Factors",
        contributing_factors=json.dumps(["Human Factors"]),
        aircraft_id=bo40.id,
        source="test",
    )
    db.session.add(report)
    db.session.commit()

    stats = remap_asrs_aircraft_ids(
        apply=True,
        overrides_path=Path("/nonexistent/overrides.jsonl"),
    )
    assert stats.changed == 1
    db.session.refresh(report)
    assert report.aircraft_id == b737_400.id


def test_import_asrs_requires_migrated_table(app):
    from sqlalchemy import text

    from app import db

    db.session.execute(text("DROP TABLE IF EXISTS asrs_report"))
    db.session.commit()

    from app.ingestion.asrs_import import require_asrs_table

    with pytest.raises(SystemExit, match="flask db upgrade"):
        require_asrs_table()


def test_export_asrs_coverage_summary(boeing_737_800, tmp_path):
    from app import db

    db.session.add(
        AsrsReport(
            acn="8888881",
            aircraft_make_model_raw="B737-800",
            primary_problem="Human Factors",
            contributing_factors=json.dumps(["Human Factors"]),
            aircraft_id=boeing_737_800.id,
            source="test",
        )
    )
    db.session.commit()

    from app.ingestion.asrs_coverage import build_coverage_summary, write_coverage_summary

    summary = build_coverage_summary()
    assert summary["aircraft_with_data"] == 1
    assert summary["matched_rows"] == 1
    assert summary["ship_gate_pass"] is False  # unit DB has 1 aircraft; gate is 10

    out = tmp_path / "coverage.json"
    write_coverage_summary(out)
    assert out.is_file()
    assert "Boeing 737-800" in out.read_text()
