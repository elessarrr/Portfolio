from app.ingestion.normalization.jasc import normalize_jasc


def test_normalize_jasc_accepts_formatted():
    assert normalize_jasc('29-51-00') == '29-51-00'


def test_normalize_jasc_accepts_compact():
    assert normalize_jasc('295100') == '29-51-00'


def test_normalize_jasc_rejects_invalid():
    assert normalize_jasc('29-5100') is None
    assert normalize_jasc('ABC') is None

