"""FAA AIDS URL builder tests (PRD 0007 FR-12.2)."""

from app.ingestion.link_schema import assert_valid_source_url, is_catalog_url
from app.ingestion.url_builders.faa_aids import (
    build_faa_aids_brief_report_url,
    build_faa_aids_search_url,
    build_faa_aids_url,
)


def test_build_url_contains_report_id():
    url = build_faa_aids_url("20050316X00394")
    assert url is not None
    assert "f?p=100:18" in url
    assert "AP_BRIEF_RPT_VAR:20050316X00394" in url


def test_build_url_none_for_empty():
    assert build_faa_aids_url(None) is None
    assert build_faa_aids_url("") is None


def test_url_passes_link_schema():
    url = build_faa_aids_url("20050316X00394")
    assert_valid_source_url(url)
    assert not is_catalog_url(url)


def test_brief_report_url_page_18():
    url = build_faa_aids_brief_report_url("19850309009149I")
    assert "f?p=100:18" in url
    assert "AP_BRIEF_RPT_VAR:19850309009149I" in url


def test_search_and_brief_urls_differ():
    sid = "19850309009149I"
    assert build_faa_aids_search_url(sid) != build_faa_aids_brief_report_url(sid)
