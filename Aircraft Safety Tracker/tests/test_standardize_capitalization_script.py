import importlib.util
from pathlib import Path

from app import db
from app.models import Aircraft, AircraftVariant, Incident


def _load_standardize_script_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "Planning"
        / "scripts"
        / "standardize_capitalization.py"
    )
    spec = importlib.util.spec_from_file_location("standardize_capitalization_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_standardize_capitalization_dry_run_does_not_persist(app):
    module = _load_standardize_script_module()

    with app.app_context():
        aircraft = Aircraft(
            manufacturer="BOEING",
            model_name="BOEING 737-800",
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add(aircraft)
        db.session.commit()

        variant = AircraftVariant(aircraft_id=aircraft.id, variant_name="MAX 8")
        incident = Incident(
            aircraft_id=aircraft.id,
            raw_model_variant="BOEING 737-800",
        )
        db.session.add_all([variant, incident])
        db.session.commit()

        summary = module.standardize_capitalization(dry_run=True, batch_size=10)
        assert summary["aircraft_manufacturer_updated"] == 1
        assert summary["aircraft_model_updated"] == 1
        assert summary["variant_name_updated"] == 1
        assert summary["incident_raw_model_variant_updated"] == 1

        db.session.expire_all()
        persisted_aircraft = db.session.get(Aircraft, aircraft.id)
        persisted_variant = db.session.get(AircraftVariant, variant.id)
        persisted_incident = db.session.get(Incident, incident.id)

        assert persisted_aircraft.manufacturer == "BOEING"
        assert persisted_aircraft.model_name == "BOEING 737-800"
        assert persisted_variant.variant_name == "MAX 8"
        assert persisted_incident.raw_model_variant == "BOEING 737-800"


def test_standardize_capitalization_apply_persists_changes_and_tracks_conflicts(app):
    module = _load_standardize_script_module()

    with app.app_context():
        conflict_target = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737",
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        conflict_source = Aircraft(
            manufacturer="BOEING",
            model_name="BOEING 737",
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add_all([conflict_target, conflict_source])
        db.session.commit()

        summary = module.standardize_capitalization(dry_run=False, batch_size=10)
        assert summary["aircraft_manufacturer_updated"] >= 1
        assert summary["aircraft_model_conflicts"] == 1

        db.session.expire_all()
        updated_source = db.session.get(Aircraft, conflict_source.id)
        assert updated_source.manufacturer == "Boeing"
        # Model remains unchanged because title-casing would collide.
        assert updated_source.model_name == "BOEING 737"
