"""FR-5.2 / FR-9.1 / FR-12: NTSB link viability detection tests."""

from app.ingestion.url_builders.ntsb_viability import (
    is_carol_empty_spa_shell,
    validate_ntsb_url,
)

DOCKET_URL = "https://data.ntsb.gov/Docket/?NTSBNumber=ENG02RA003"
CAROL_URL = "https://carol.ntsb.gov/investigations/detail/abc123"

CAROL_EMPTY_SPA = """<!DOCTYPE html><html><body>
<script>window.__ENV__ = {};</script>
<main id="root"></main>
</body></html>"""

CAROL_WITH_CONTENT = """<html><body>
<h1>Investigation Detail</h1>
<p>NTSB Number: DCA08MA076</p>
<p>Event Date: 2008-01-01</p>
</body></html>"""


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


def test_carol_empty_spa_shell_not_viable():
    assert is_carol_empty_spa_shell(CAROL_EMPTY_SPA) is True

    def fetcher(_url):
        return 200, CAROL_EMPTY_SPA

    viable, status, reason = validate_ntsb_url(CAROL_URL, fetcher=fetcher)
    assert viable is False
    assert status == 200
    assert reason == "carol_empty_spa"


def test_carol_with_content_is_viable():
    assert is_carol_empty_spa_shell(CAROL_WITH_CONTENT) is False

    def fetcher(_url):
        return 200, CAROL_WITH_CONTENT

    viable, status, reason = validate_ntsb_url(CAROL_URL, fetcher=fetcher)
    assert viable is True
    assert status == 200
    assert reason is None
