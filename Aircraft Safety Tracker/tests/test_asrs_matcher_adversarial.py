"""Adversarial tests for ASRS make/model → aircraft matcher."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.ingestion.asrs_aircraft_match import build_aircraft_index, match_asrs_make_model


@dataclass
class _FakeAircraft:
    id: int
    manufacturer: str
    model_name: str


@pytest.fixture
def boeing_matcher_catalog():
    """Multi-aircraft catalog including false-positive-prone Boeing 40 / 80 rows."""
    rows = [
        _FakeAircraft(1, "Boeing", "Boeing 40"),
        _FakeAircraft(2, "Boeing", "Boeing 80"),
        _FakeAircraft(3, "Boeing", "Boeing 737"),
        _FakeAircraft(4, "Boeing", "Boeing 737-400"),
        _FakeAircraft(5, "Boeing", "Boeing 737-800"),
    ]
    return build_aircraft_index(rows)


def test_a380_does_not_match_boeing_80(boeing_matcher_catalog):
    """Regression: '80' substring in A380 must not map to Boeing 80."""
    index = boeing_matcher_catalog
    assert match_asrs_make_model("A380", index) is None


def test_b737_400_does_not_match_boeing_40_or_80(boeing_matcher_catalog):
    index = boeing_matcher_catalog
    by_id = {e.aircraft_id: e.model_name for e in index}

    for raw in ("B737-400", "737-400", "BOEING 737-400"):
        matched_id = match_asrs_make_model(raw, index)
        assert matched_id is not None
        assert by_id[matched_id] == "Boeing 737-400"
        assert matched_id not in (1, 2)


def test_b737_800_matches_variant_not_legacy_types(boeing_matcher_catalog):
    index = boeing_matcher_catalog
    by_id = {e.aircraft_id: e.model_name for e in index}

    matched_id = match_asrs_make_model("B737-800", index)
    assert matched_id is not None
    assert by_id[matched_id] == "Boeing 737-800"


def test_generic_b737_prefers_737_rollup(boeing_matcher_catalog):
    index = boeing_matcher_catalog
    by_id = {e.aircraft_id: e.model_name for e in index}

    matched_id = match_asrs_make_model("B737", index)
    assert matched_id is not None
    assert by_id[matched_id] == "Boeing 737"


def test_ambiguous_equal_score_tie_returns_none():
    """Two substring candidates with identical top score must not pick arbitrarily."""
    rows = [
        _FakeAircraft(10, "Acme", "Acme XXXX"),
        _FakeAircraft(11, "Acme", "Acme YYYY"),
    ]
    index = build_aircraft_index(rows)
    # Both series keys length 4 substring-match asrs_compact with score 14 → tie → None.
    assert match_asrs_make_model("XXXXYYYY", index) is None
