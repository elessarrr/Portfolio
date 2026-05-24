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
        source_data={"factualNarrative": "Published NTSB factual narrative for this investigation."},
    )
    assert resolve_ntsb_href(source) == "https://carol.ntsb.gov/investigations/detail/75062"


def test_resolve_ntsb_falls_back_to_docket():
    source = IncidentSource(
        source_name="NTSB",
        source_record_id="DCA10RA010",
        source_url=None,
    )
    assert resolve_ntsb_href(source) == "https://data.ntsb.gov/Docket/?NTSBNumber=DCA10RA010"


def test_resolve_ntsb_skips_empty_carol_detail():
    source = IncidentSource(
        source_name="NTSB",
        source_record_id="DCA26WA017",
        source_url="https://carol.ntsb.gov/investigations/detail/201888",
        source_data={"cm_mkey": 201888, "cm_launch": "Partial"},
    )
    assert resolve_ntsb_href(source) is None


def test_resolve_ntsb_skips_foreign_led_even_with_narrative():
    source = IncidentSource(
        source_name="NTSB",
        source_record_id="DCA17RA058",
        source_url="https://carol.ntsb.gov/investigations/detail/94608",
        source_data={
            "cm_mkey": 94608,
            "cm_agency": "Other",
            "factualNarrative": "The Government of Kyrgyzstan has notified the NTSB of an accident.",
        },
    )
    assert resolve_ntsb_href(source) is None


def test_resolve_ntsb_keeps_carol_when_narrative_exists():
    source = IncidentSource(
        source_name="NTSB",
        source_record_id="DCA10RA010",
        source_url="https://carol.ntsb.gov/investigations/detail/75062",
        source_data={
            "cm_agency": "NTSB",
            "factualNarrative": "Published NTSB factual narrative for this investigation.",
        },
    )
    assert resolve_ntsb_href(source) == "https://carol.ntsb.gov/investigations/detail/75062"


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
        source_data={"factualNarrative": "Published NTSB factual narrative for this investigation."},
        is_active=True,
    )
    hrefs = resolve_source_hrefs(source)
    urls = [u for u, _r, _l in hrefs]
    assert "https://carol.ntsb.gov/investigations/detail/75062" in urls
    assert any("data.ntsb.gov/Docket" in u for u in urls)
