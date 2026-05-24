from datetime import date

from app import db
from app.ingestion.linking.faa_profile_attach import (
    attach_aircraft_ids,
    exact_match_key,
    exact_merge_faa_to_profile,
    is_boeing_airbus_faa,
)
from app.models import Aircraft, Incident, IncidentSource


def test_exact_match_key_normalizes_registration():
    key = exact_match_key(date(2020, 5, 1), "n12-345")
    assert key == ("2020-05-01", "N12345")


def test_exact_match_key_missing_registration():
    assert exact_match_key(date(2020, 5, 1), None) is None


def test_is_boeing_airbus_faa_filters_ga(app):
    with app.app_context():
        ga = IncidentSource(
            source_name="FAA_AIDS",
            source_url="https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:1",
            is_active=True,
            source_data={"c23": "CESSNA", "c24": "172"},
        )
        boeing = IncidentSource(
            source_name="FAA_AIDS",
            source_url="https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:2",
            is_active=True,
            source_data={"c23": "BOEING", "c24": "727232"},
        )
        assert is_boeing_airbus_faa(ga) is False
        assert is_boeing_airbus_faa(boeing) is True


def test_attach_dry_run_no_writes(app):
    with app.app_context():
        a = Aircraft(manufacturer="Boeing", model_name="Boeing 727232")
        db.session.add(a)
        db.session.commit()

        inc = Incident(date=date(1985, 1, 2), registration="N12345")
        db.session.add(inc)
        db.session.commit()

        src = IncidentSource(
            incident_id=inc.id,
            source_name="FAA_AIDS",
            source_record_id="TEST001",
            source_url="https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:TEST001",
            is_active=True,
            source_data={"c23": "BOEING", "c24": "727232", "c203": "N12345"},
        )
        db.session.add(src)
        db.session.commit()

        before = Incident.query.get(inc.id).aircraft_id
        summary = attach_aircraft_ids(dry_run=True, limit=10)
        after = Incident.query.get(inc.id).aircraft_id

        assert summary.attached == 1
        assert before is None
        assert after is None


def test_exact_merge_single_hit(app):
    with app.app_context():
        a = Aircraft(manufacturer="Boeing", model_name="Boeing 737")
        db.session.add(a)
        db.session.commit()

        target = Incident(
            aircraft_id=a.id,
            date=date(2010, 3, 15),
            registration="N999AA",
            operator="Test Air",
        )
        faa_inc = Incident(date=date(2010, 3, 15), registration="N999AA")
        db.session.add_all([target, faa_inc])
        db.session.commit()

        ntsb = IncidentSource(
            incident_id=target.id,
            source_name="NTSB",
            source_record_id="WPR10WA001",
            is_active=True,
            source_data={"cm_agency": "Other"},
        )
        faa_src = IncidentSource(
            incident_id=faa_inc.id,
            source_name="FAA_AIDS",
            source_record_id="FAA999",
            source_url="https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:FAA999",
            is_active=True,
            source_data={"c23": "BOEING", "c24": "737", "c203": "N999AA"},
        )
        db.session.add_all([ntsb, faa_src])
        db.session.commit()

        summary = exact_merge_faa_to_profile(dry_run=False, limit=100)
        assert summary.merge_linked == 1

        target_sources = IncidentSource.query.filter_by(incident_id=target.id).all()
        names = {s.source_name for s in target_sources}
        assert "FAA_AIDS" in names
        assert Incident.query.get(faa_inc.id) is None


def test_exact_merge_skips_ambiguous(app):
    with app.app_context():
        a = Aircraft(manufacturer="Boeing", model_name="Boeing 737")
        db.session.add(a)
        db.session.commit()

        target = Incident(
            aircraft_id=a.id,
            date=date(2011, 4, 20),
            registration="N888BB",
        )
        faa1 = Incident(date=date(2011, 4, 20), registration="N888BB")
        faa2 = Incident(date=date(2011, 4, 20), registration="N888BB")
        db.session.add_all([target, faa1, faa2])
        db.session.commit()

        for idx, inc in enumerate([faa1, faa2], start=1):
            db.session.add(
                IncidentSource(
                    incident_id=inc.id,
                    source_name="FAA_AIDS",
                    source_record_id=f"FAAX{idx}",
                    source_url=f"https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:FAAX{idx}",
                    is_active=True,
                    source_data={"c23": "BOEING", "c24": "737", "c203": "N888BB"},
                )
            )
        db.session.add(
            IncidentSource(
                incident_id=target.id,
                source_name="NTSB",
                source_record_id="WPR11WA002",
                is_active=True,
                source_data={"cm_agency": "Other"},
            )
        )
        db.session.commit()

        summary = exact_merge_faa_to_profile(dry_run=True, limit=100)
        assert summary.merge_ambiguous == 1
        assert summary.merge_linked == 0
