"""ASRS aggregate profile for aircraft detail pages."""

from __future__ import annotations

import json
import re
from collections import Counter

from app.models import AsrsReport

ASRS_DBOL_URL = "https://asrs.arc.nasa.gov/search/database.html"

_BUCKET_NEEDLES: list[tuple[str, tuple[str, ...]]] = [
    ("Human Factors", ("human factors", "human-machine", "human machine", "crm", "confusion", "situational awareness")),
    ("Aircraft Equipment", ("aircraft equipment", "equipment problem", "component", "maintenance", " aircraft ")),
    ("ATC Issue", ("atc", "air traffic control", "controller")),
    ("Weather/Environment", ("weather", "environment", "turbulence", "icing", "wind")),
]


def normalize_factor_bucket(token: str) -> str:
    lowered = f" {(token or '').strip().lower()} "
    for bucket, needles in _BUCKET_NEEDLES:
        if any(n in lowered for n in needles):
            return bucket
    if "human" in lowered or "person" in lowered:
        return "Human Factors"
    if "aircraft" in lowered or "equipment" in lowered:
        return "Aircraft Equipment"
    return "Other"


def parse_factor_list(raw_json: str | None) -> list[str]:
    if not raw_json:
        return []
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return [p.strip() for p in re.split(r"[;,]", raw_json) if p.strip()]
    if isinstance(data, list):
        return [str(x).strip() for x in data if str(x).strip()]
    return []


def get_asrs_profile(aircraft_id: int) -> dict | None:
    rows = AsrsReport.query.filter_by(aircraft_id=aircraft_id).all()
    if not rows:
        return None

    n = len(rows)
    bucket_counts: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()

    for row in rows:
        factors = parse_factor_list(row.contributing_factors)
        buckets = {normalize_factor_bucket(f) for f in factors}
        if not buckets and row.primary_problem:
            buckets = {normalize_factor_bucket(row.primary_problem)}
        for bucket in buckets:
            bucket_counts[bucket] += 1
        if row.primary_problem:
            event_counts[row.primary_problem.strip()] += 1

    contributing_factors = {
        label: round(100 * count / n, 1)
        for label, count in bucket_counts.most_common()
    }
    top_event_types = [label for label, _ in event_counts.most_common(3)]

    return {
        "n": n,
        "contributing_factors": contributing_factors,
        "top_event_types": top_event_types,
        "limited_data": n < 5,
        "asrs_query_url": ASRS_DBOL_URL,
    }
