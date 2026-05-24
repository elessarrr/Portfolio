from datetime import date

import pytest

from app import db
from app.models import Aircraft, AircraftFamilyMember, Incident, IncidentSource
from app.services.aircraft_family import (
    clear_family_member_cache,
    get_family_member_ids,
    incident_query_for_aircraft,
    resolve_canonical_family,
    uses_family_rollup,
)
from app.ingestion.family_rules_seed import load_csv_rows, validate_rows


def _seed_family(app, family_id, member_ids):
    with app.app_context():
        AircraftFamilyMember.query.delete()
        db.session.commit()
        clear_family_member_cache()
        for member_id in member_ids:
            db.session.add(
                AircraftFamilyMember(
                    family_aircraft_id=family_id,
                    member_aircraft_id=member_id,
                )
            )
        db.session.commit()
        clear_family_member_cache()


def test_get_family_member_ids_includes_self_and_members(app):
    family = Aircraft(manufacturer="Boeing", model_name="BOEING 737-300")
    member_a = Aircraft(manufacturer="Boeing", model_name="Boeing 7373H4")
    member_b = Aircraft(manufacturer="Boeing", model_name="Boeing 737322")
    db.session.add_all([family, member_a, member_b])
    db.session.commit()
    _seed_family(app, family.id, [family.id, member_a.id, member_b.id])

    ids = get_family_member_ids(family.id)
    assert set(ids) == {family.id, member_a.id, member_b.id}


def test_member_page_no_reverse_rollup(app):
    family = Aircraft(manufacturer="Boeing", model_name="BOEING 737-300")
    member = Aircraft(manufacturer="Boeing", model_name="Boeing 7373H4")
    db.session.add_all([family, member])
    db.session.commit()
    _seed_family(app, family.id, [family.id, member.id])

    assert get_family_member_ids(member.id) == [member.id]
    assert uses_family_rollup(member.id) is False


def test_ga_aircraft_no_rollup(app):
    ga = Aircraft(manufacturer="Cessna", model_name="Cessna 172")
    db.session.add(ga)
    db.session.commit()
    assert get_family_member_ids(ga.id) == [ga.id]
    assert uses_family_rollup(ga.id) is False


def test_incident_query_for_family_aggregates(app):
    family = Aircraft(manufacturer="Boeing", model_name="BOEING 737-300")
    member = Aircraft(manufacturer="Boeing", model_name="Boeing 7373H4")
    db.session.add_all([family, member])
    db.session.commit()
    _seed_family(app, family.id, [family.id, member.id])

    db.session.add_all([
        Incident(aircraft_id=family.id, date=date(2020, 1, 1), fatalities=0),
        Incident(aircraft_id=member.id, date=date(2019, 1, 1), fatalities=0),
    ])
    db.session.commit()

    assert incident_query_for_aircraft(family.id).count() == 2
    assert incident_query_for_aircraft(member.id).count() == 1


def test_resolve_canonical_family_from_member(app):
    family = Aircraft(manufacturer="Boeing", model_name="BOEING 737-300")
    member = Aircraft(manufacturer="Boeing", model_name="Boeing 7373H4")
    db.session.add_all([family, member])
    db.session.commit()
    _seed_family(app, family.id, [family.id, member.id])

    assert resolve_canonical_family(member.id) == family.id
    assert resolve_canonical_family(family.id) == family.id


def test_seed_family_rules_rejects_duplicate_member(app):
    family_a = Aircraft(manufacturer="Boeing", model_name="Family A")
    family_b = Aircraft(manufacturer="Boeing", model_name="Family B")
    member = Aircraft(manufacturer="Boeing", model_name="Shared Member")
    db.session.add_all([family_a, family_b, member])
    db.session.commit()

    rows = [
        (family_a.id, family_a.id),
        (family_a.id, member.id),
        (family_b.id, family_b.id),
        (family_b.id, member.id),
    ]
    summary = validate_rows(rows)
    assert any("duplicate member" in err for err in summary.errors)


def test_search_autocomplete_prefers_canonical_family(client, app):
    family = Aircraft(manufacturer="Boeing", model_name="BOEING 737-300")
    member = Aircraft(manufacturer="Boeing", model_name="Boeing 7373H4")
    db.session.add_all([family, member])
    db.session.commit()
    _seed_family(app, family.id, [family.id, member.id])

    response = client.get("/api/search/autocomplete?q=7373")
    assert response.status_code == 200
    payload = response.get_json()
    ids = [item["id"] for item in payload["results"]]
    assert family.id in ids
    assert member.id not in ids
