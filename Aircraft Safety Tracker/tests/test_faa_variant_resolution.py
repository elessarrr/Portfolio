"""Tests for FAA AIDS make_model → catalog page resolution."""

from app.ingestion.faa_variant_resolution import resolve_faa_canonical_model_name

CATALOG = frozenset(
    {
        "Boeing 727-100",
        "Boeing 727-200",
        "Boeing 737-800",
        "Boeing 747-400",
        "Airbus A320",
        "Airbus Helicopters AS350",
        "Airbus Helicopters EC130",
    }
)


def test_boeing_727_customer_code_maps_to_727_200():
    assert resolve_faa_canonical_model_name("BOEING 7272M7", CATALOG) == "Boeing 727-200"


def test_boeing_737_maps_to_series_page():
    assert resolve_faa_canonical_model_name("BOEING 7378K5", CATALOG) == "Boeing 737-800"


def test_skip_ag1():
    assert resolve_faa_canonical_model_name("BOEING AG-1", CATALOG) is None
