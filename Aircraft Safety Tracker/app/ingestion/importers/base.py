"""Minimal Boeing/Airbus aircraft resolution for v3 importers."""

from __future__ import annotations

import re
from typing import Optional

from app import db
from app.models import Aircraft

BOEING_AIRBUS_PREFIXES = ("boeing", "airbus")


def normalize_make_model(make_model: str) -> str:
    text = re.sub(r"\s+", " ", (make_model or "").strip())
    return text


def is_boeing_or_airbus_make_model(make_model: Optional[str]) -> bool:
    value = (make_model or "").strip().lower()
    return value.startswith(BOEING_AIRBUS_PREFIXES)


def resolve_boeing_airbus_aircraft_id(make_model: Optional[str]) -> Optional[int]:
    if not is_boeing_or_airbus_make_model(make_model):
        return None
    model_name = normalize_make_model(make_model or "")
    aircraft = Aircraft.query.filter_by(model_name=model_name).first()
    if aircraft:
        return aircraft.id
    manufacturer = "Boeing" if model_name.lower().startswith("boeing") else "Airbus"
    aircraft = Aircraft(manufacturer=manufacturer, model_name=model_name)
    db.session.add(aircraft)
    db.session.flush()
    return aircraft.id
