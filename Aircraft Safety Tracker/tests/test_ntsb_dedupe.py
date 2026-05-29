"""FR-4.4: Deterministic NTSB vs ASN dedupe scoring edge cases."""

from datetime import date

from app.ingestion.dedupe.ntsb_asn import score_ntsb_vs_asn


def test_same_date_operator_location_close_is_asn_covered():
    decision = score_ntsb_vs_asn(
        ntsb_date=date(2020, 6, 15),
        asn_date=date(2020, 6, 15),
        ntsb_operator="United Airlines",
        asn_operator="United Airlines",
        ntsb_location="Denver, CO",
        asn_location="Denver, CO",
        ntsb_fatalities=0,
        asn_fatalities=0,
    )
    assert decision.asn_covered is True
    assert decision.signals.strong_count() >= 2


def test_date_plus_one_day_one_strong_signal_only_not_covered():
    decision = score_ntsb_vs_asn(
        ntsb_date=date(2020, 6, 16),
        asn_date=date(2020, 6, 15),
        ntsb_operator="United Airlines",
        asn_operator="Delta Air Lines",
        ntsb_location="Denver, CO",
        asn_location="Miami, FL",
        ntsb_fatalities=None,
        asn_fatalities=None,
    )
    assert decision.signals.date_close is True
    assert decision.signals.strong_count() == 1
    assert decision.asn_covered is False


def test_clearly_different_incident_not_covered():
    decision = score_ntsb_vs_asn(
        ntsb_date=date(2019, 1, 1),
        asn_date=date(2020, 6, 15),
        ntsb_operator="Southwest Airlines",
        asn_operator="United Airlines",
        ntsb_location="Phoenix, AZ",
        asn_location="Denver, CO",
        ntsb_fatalities=2,
        asn_fatalities=0,
    )
    assert decision.asn_covered is False
    assert decision.signals.strong_count() < 2


def test_same_inputs_produce_identical_decision():
    kwargs = dict(
        ntsb_date=date(2018, 3, 10),
        asn_date=date(2018, 3, 11),
        ntsb_operator="American Airlines",
        asn_operator="American Airlines Inc",
        ntsb_location="Dallas, TX",
        asn_location="Dallas Texas",
        ntsb_fatalities=1,
        asn_fatalities=1,
    )
    first = score_ntsb_vs_asn(**kwargs)
    second = score_ntsb_vs_asn(**kwargs)
    assert first == second
