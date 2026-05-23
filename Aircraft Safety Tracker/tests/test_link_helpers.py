from app.link_helpers import is_placeholder_url, resolve_ntsb_href, resolve_source_href, resolve_source_hrefs
from app.models import IncidentSource


def test_is_placeholder_url():
    assert is_placeholder_url("https://example.com/asn/1") is True
    assert is_placeholder_url("https://aviation-safety.net/wikibase/1") is False


def test_resolve_ntsb_prefers_carol():
    source = IncidentSource(
        source_name="NTSB",
        source_record_id="DCA10RA010",
        source_url="https://carol.ntsb.gov/investigations/detail/75062",
    )
    assert resolve_ntsb_href(source) == "https://carol.ntsb.gov/investigations/detail/75062"


def test_resolve_ntsb_falls_back_to_docket():
    source = IncidentSource(
        source_name="NTSB",
        source_record_id="DCA10RA010",
        source_url=None,
    )
    assert resolve_ntsb_href(source) == "https://data.ntsb.gov/Docket/?NTSBNumber=DCA10RA010"


def test_resolve_source_href_blocks_placeholder():
    source = IncidentSource(
        source_name="ASN",
        source_url="https://example.com/asn/1",
        is_active=True,
    )
    assert resolve_source_href(source) is None


def test_resolve_source_hrefs_ntsb_multiple():
    source = IncidentSource(
        source_name="NTSB",
        source_record_id="DCA10RA010",
        source_url="https://carol.ntsb.gov/investigations/detail/75062",
        is_active=True,
    )
    hrefs = resolve_source_hrefs(source)
    urls = [u for u, _r, _l in hrefs]
    assert "https://carol.ntsb.gov/investigations/detail/75062" in urls
    assert any("data.ntsb.gov/Docket" in u for u in urls)
