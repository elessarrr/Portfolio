"""Tests for NTSB variant → catalog page resolution."""

from app.ingestion.ntsb_variant_resolution import (
    is_ec130_make_model,
    is_generic_boeing_737,
    resolve_boeing_737_series_page,
    resolve_boeing_787_page,
    resolve_canonical_model_name,
)


def test_generic_737_stays_on_family():
    assert is_generic_boeing_737("BOEING 737")
    assert resolve_boeing_737_series_page("BOEING 737") == "Boeing 737"
    assert resolve_boeing_737_series_page("Boeing 737") == "Boeing 737"


def test_737_301_maps_to_300_series():
    assert resolve_boeing_737_series_page("BOEING 737-301") == "Boeing 737-300"
    assert resolve_boeing_737_series_page("BOEING 737-7H4") == "Boeing 737-700"


def test_787_variant_vs_family():
    assert resolve_boeing_787_page("BOEING 787") == "Boeing 787"
    assert resolve_boeing_787_page("BOEING 787-8") == "Boeing 787-8 Dreamliner"
    assert resolve_boeing_787_page("BOEING 787-9") == "Boeing 787-9 Dreamliner"
    assert resolve_boeing_787_page("BOEING 787-10") == "Boeing 787-10 Dreamliner"


def test_ec130_not_ec135():
    assert is_ec130_make_model("AIRBUS HELICOPTERS EC 130 T2")
    assert is_ec130_make_model("AIRBUS EC130")
    assert not is_ec130_make_model("AIRBUS EC135")
    assert resolve_canonical_model_name("AIRBUS EC130") == "Airbus Helicopters EC130"
