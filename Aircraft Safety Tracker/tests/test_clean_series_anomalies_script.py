import importlib.util
from datetime import date
from pathlib import Path

from app import db
from app.models import Aircraft, Incident


def _load_cleanup_script_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "Planning"
        / "scripts"
        / "clean_series_anomalies.py"
    )
    spec = importlib.util.spec_from_file_location("clean_series_anomalies_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_clean_series_anomalies_dry_run_reports_without_persisting(app):
    module = _load_cleanup_script_module()

    with app.app_context():
        invalid_orphan = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 75N1",
            total_incidents=0,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add(invalid_orphan)
        db.session.commit()

        summary = module.clean_series_anomalies(dry_run=True, batch_size=10)
        assert summary["invalid_rows"] >= 1
        assert summary["deleted_orphan_invalid_rows"] >= 1

        db.session.expire_all()
        still_exists = db.session.get(Aircraft, invalid_orphan.id)
        assert still_exists is not None


def test_clean_series_anomalies_apply_deletes_only_orphan_invalid_rows(app):
    module = _load_cleanup_script_module()

    with app.app_context():
        invalid_orphan = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 75N1",
            total_incidents=0,
            fatal_incidents=0,
            total_fatalities=0,
        )
        invalid_linked = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 75N2",
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add_all([invalid_orphan, invalid_linked])
        db.session.commit()

        db.session.add(
            Incident(
                aircraft_id=invalid_linked.id,
                date=date(2020, 1, 1),
                operator="Linked Operator",
                location="Linked Location",
                fatalities=0,
                description="Linked invalid model test",
                incident_type="Accident",
            )
        )
        db.session.commit()

        summary = module.clean_series_anomalies(dry_run=False, batch_size=10)
        assert summary["deleted_orphan_invalid_rows"] >= 1
        assert summary["kept_linked_invalid_rows"] >= 1

        db.session.expire_all()
        assert db.session.get(Aircraft, invalid_orphan.id) is None
        assert db.session.get(Aircraft, invalid_linked.id) is not None
