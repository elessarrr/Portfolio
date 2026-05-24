from app.ingestion.link_schema import is_placeholder_url
from app.ingestion.url_builders.faa_aids import (
    build_faa_aids_links,
    build_faa_aids_primary_url,
    build_faa_aids_source_url,
)


def test_build_faa_aids_primary_url():
    url = build_faa_aids_primary_url("19850908053709I")
    assert url == (
        "https://www.asias.faa.gov/apex/f?p=100:12:::NO::"
        "P12_AIDS_RPRT_NBR:19850908053709I"
    )


def test_build_faa_aids_primary_url_encodes_special_chars():
    url = build_faa_aids_primary_url("ABC/123 test")
    assert "P12_AIDS_RPRT_NBR:ABC%2F123%20test" in url


def test_build_faa_aids_links_with_record_id():
    links = build_faa_aids_links(source_record_id="19850908053709I")
    roles = [link["role"] for link in links]
    assert roles[0] == "primary"
    assert "asias.faa.gov" in links[0]["url"]
    assert "P12_AIDS_RPRT_NBR:19850908053709I" in links[0]["url"]
    assert "catalog" in roles


def test_build_faa_aids_links_missing_record_id():
    links = build_faa_aids_links()
    assert links == []


def test_build_faa_aids_source_url_prefers_asias_over_catalog():
    url = build_faa_aids_source_url(
        source_record_id="19850908053709I",
        source_url="https://www.faa.gov/data_research/accident_incident",
    )
    assert "asias.faa.gov" in url
    assert "P12_AIDS_RPRT_NBR" in url


def test_build_faa_aids_blocks_placeholder():
    url = build_faa_aids_source_url(
        source_record_id="19850908053709I",
        source_url="https://example.com/faa/1",
    )
    assert is_placeholder_url("https://example.com/faa/1")
    assert "asias.faa.gov" in url
