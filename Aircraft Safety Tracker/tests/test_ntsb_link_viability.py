"""FR-5.2 / FR-9.1: NTSB link viability detection tests."""

from app.ingestion.url_builders.ntsb_viability import validate_ntsb_url

DOCKET_URL = "https://data.ntsb.gov/Docket/?NTSBNumber=ENG02RA003"
CAROL_URL = "https://carol.ntsb.gov/investigations/detail/abc123"


def test_unreleased_docket_body_not_viable():
    def fetcher(_url):
        return 200, "<html>The docket for this investigation has not been released.</html>"

    viable, status, reason = validate_ntsb_url(DOCKET_URL, fetcher=fetcher)
    assert viable is False
    assert status == 200
    assert reason == "docket_not_released"


def test_released_docket_body_is_viable():
    def fetcher(_url):
        return 200, "<html><h1>Investigation Docket</h1><table>...</table></html>"

    viable, status, reason = validate_ntsb_url(DOCKET_URL, fetcher=fetcher)
    assert viable is True
    assert status == 200
    assert reason is None


def test_http_404_not_viable():
    def fetcher(_url):
        return 404, "Not Found"

    viable, status, reason = validate_ntsb_url(DOCKET_URL, fetcher=fetcher)
    assert viable is False
    assert status == 404
    assert reason == "http_404"


def test_empty_url_not_viable():
    viable, status, reason = validate_ntsb_url(None)
    assert viable is False
    assert status is None
    assert reason == "no_url"


def test_carol_200_is_viable():
    def fetcher(_url):
        return 200, "<html><title>Investigation Detail</title></html>"

    viable, status, reason = validate_ntsb_url(CAROL_URL, fetcher=fetcher)
    assert viable is True
    assert status == 200
    assert reason is None
