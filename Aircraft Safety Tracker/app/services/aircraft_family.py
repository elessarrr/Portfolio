"""Boeing/Airbus family rollup — query-time incident aggregation."""

from __future__ import annotations

from typing import List, Optional, Set

from app import db
from app.models import Aircraft, AircraftFamilyMember, Incident

_BOEING_AIRBUS = frozenset({"BOEING", "AIRBUS"})


def clear_family_member_cache() -> None:
    """No-op retained for callers after seed; caching removed."""


def is_rollup_eligible(aircraft: Aircraft) -> bool:
    manufacturer = (aircraft.manufacturer or "").strip().upper()
    return manufacturer in _BOEING_AIRBUS


def is_canonical_family(aircraft_id: int) -> bool:
    """True when this aircraft_id is designated as a family head."""
    return (
        db.session.query(AircraftFamilyMember.id)
        .filter(AircraftFamilyMember.family_aircraft_id == aircraft_id)
        .first()
        is not None
    )


def resolve_canonical_family(aircraft_id: int) -> Optional[int]:
    """Return canonical family id for search/navigation, or None if unmapped leaf."""
    row = AircraftFamilyMember.query.filter_by(member_aircraft_id=aircraft_id).first()
    if row:
        return row.family_aircraft_id
    if is_canonical_family(aircraft_id):
        return aircraft_id
    return None


def get_family_for_member(aircraft_id: int) -> Optional[AircraftFamilyMember]:
    return AircraftFamilyMember.query.filter_by(member_aircraft_id=aircraft_id).first()


def get_family_member_ids(aircraft_id: int) -> List[int]:
    """
    Family head: self + all mapped members.
    Member or unmapped leaf: self only (FR-6.1 — no reverse rollup).
    """
    if not is_canonical_family(aircraft_id):
        return [aircraft_id]
    rows = AircraftFamilyMember.query.filter_by(family_aircraft_id=aircraft_id).all()
    ids = {aircraft_id}
    ids.update(row.member_aircraft_id for row in rows)
    return sorted(ids)


def uses_family_rollup(aircraft_id: int) -> bool:
    aircraft = db.session.get(Aircraft, aircraft_id)
    if not aircraft or not is_rollup_eligible(aircraft):
        return False
    return is_canonical_family(aircraft_id)


def incident_query_for_aircraft(aircraft_id: int):
    """Incident query scoped to family rollup when eligible."""
    aircraft = db.session.get(Aircraft, aircraft_id)
    if not aircraft:
        return Incident.query.filter(Incident.id == -1)
    if not is_rollup_eligible(aircraft) or not is_canonical_family(aircraft_id):
        return Incident.query.filter_by(aircraft_id=aircraft_id)
    member_ids = get_family_member_ids(aircraft_id)
    return Incident.query.filter(Incident.aircraft_id.in_(member_ids))


def count_incidents_for_aircraft(aircraft_id: int) -> int:
    return incident_query_for_aircraft(aircraft_id).count()


def rolled_up_aircraft_ids_for_filters(aircraft_id: int) -> Set[int]:
    """Aircraft ids to use when building filter option queries on family pages."""
    if uses_family_rollup(aircraft_id):
        return set(get_family_member_ids(aircraft_id))
    return {aircraft_id}
