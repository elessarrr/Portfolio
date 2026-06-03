"""Unit tests for FAA AIDS ASIAS URL viability (PRD 0007.1 FR-8)."""

from app.ingestion.url_builders.faa_aids import (
    build_faa_aids_brief_report_url,
    build_faa_aids_search_url,
)
from app.ingestion.url_builders.faa_aids_viability import (
    BUCKET_BRIEF_REPORT,
    BUCKET_NOT_WORKING,
    BUCKET_SEARCH_PREFILL,
    classify_faa_aids_bucket,
    probe_asias_liveness,
    validate_faa_aids_url,
    validate_faa_aids_url_extended,
)

FAA_SEARCH_URL = build_faa_aids_search_url("19850102002229I")
FAA_BRIEF_URL = build_faa_aids_brief_report_url("19850102002229I")

CONTENT_BODY = """
<html><body>
<span id="P12_AIDS_RPRT_NBR">19850102002229I</span>
Aircraft Make/Model: BOEING 727222
Event Date: 1985-01-02
Phase of Flight: CRUISE
</body></html>
"""

SEARCH_FORM_BODY = """
<html><body>
<h1>AIDS Search Form</h1>
<span id="P12_AIDS_RPRT_NBR">19850102002229I</span>
Search AIDS
Clear Search
</body></html>
"""

BRIEF_REPORT_BODY = """
<html><body>
<div class="ap_brief">Brief Report</div>
Factual narrative: aircraft landed safely.
Event Date: 1985-01-02
Aircraft Make/Model: BOEING 727
</body></html>
"""

CDN_ERROR_BODY = """
<html><body>
<h1>An error occurred while processing your request.</h1>
Reference #102.d0e9c717.1780310489.9ae7f7d1<br/>
https://errors.edgesuite.net/102...
</body></html>
"""

EMPTY_APEX_BODY = """
<html><body>
<div id="uBodyContainer">
No data found
</div>
</body></html>
"""

SESSION_EXPIRED_BODY = """
<html><body>
Your session has expired. Please log in again.
</body></html>
"""


def test_http_503_returns_cdn_error():
    viable, status, reason = validate_faa_aids_url(
        FAA_SEARCH_URL, fetcher=lambda u: (503, "Service Unavailable")
    )
    assert not viable
    assert status == 503
    assert reason == "asias_cdn_error"


def test_http_200_cdn_error_body():
    viable, status, reason = validate_faa_aids_url(
        FAA_SEARCH_URL, fetcher=lambda u: (200, CDN_ERROR_BODY)
    )
    assert not viable
    assert status == 200
    assert reason == "asias_cdn_error"


def test_http_404_returns_record_not_found():
    import urllib.error

    def fetcher_404(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    viable, status, reason = validate_faa_aids_url(FAA_SEARCH_URL, fetcher=fetcher_404)
    assert not viable
    assert status == 404
    assert reason == "asias_record_not_found"


def test_http_200_empty_apex_body():
    viable, status, reason = validate_faa_aids_url(
        FAA_SEARCH_URL, fetcher=lambda u: (200, EMPTY_APEX_BODY)
    )
    assert not viable
    assert status == 200
    assert reason == "asias_empty_report"


def test_session_expired_redirect_landing():
    viable, status, reason = validate_faa_aids_url(
        FAA_SEARCH_URL, fetcher=lambda u: (200, SESSION_EXPIRED_BODY)
    )
    assert not viable
    assert reason == "asias_empty_report"


def test_http_200_with_content_markers_search_mode_is_search_prefill():
    result = validate_faa_aids_url_extended(
        FAA_SEARCH_URL,
        url_mode="search",
        fetcher=lambda u: (200, CONTENT_BODY),
        retry_once=False,
    )
    assert result.viable
    assert result.bucket == BUCKET_SEARCH_PREFILL
    assert not result.product_viable


def test_search_form_body_search_mode_is_search_prefill():
    result = validate_faa_aids_url_extended(
        FAA_SEARCH_URL,
        url_mode="search",
        fetcher=lambda u: (200, SEARCH_FORM_BODY),
        retry_once=False,
    )
    assert result.bucket == BUCKET_SEARCH_PREFILL


def test_brief_url_brief_mode_is_product_viable():
    result = validate_faa_aids_url_extended(
        FAA_BRIEF_URL,
        url_mode="brief",
        fetcher=lambda u: (200, BRIEF_REPORT_BODY),
        retry_once=False,
    )
    assert result.product_viable
    assert result.bucket == BUCKET_BRIEF_REPORT


def test_brief_url_landing_on_search_form_is_search_prefill():
    result = validate_faa_aids_url_extended(
        FAA_BRIEF_URL,
        url_mode="brief",
        fetcher=lambda u: (200, SEARCH_FORM_BODY),
        retry_once=False,
    )
    assert result.viable
    assert result.bucket == BUCKET_SEARCH_PREFILL
    assert not result.product_viable


def test_classify_search_url_strict_without_search_markers():
    bucket = classify_faa_aids_bucket(
        http_ok=True,
        body=CONTENT_BODY,
        url=FAA_SEARCH_URL,
        url_mode="search",
    )
    assert bucket == BUCKET_SEARCH_PREFILL


def test_liveness_probe_false_on_connection_error():
    import urllib.error

    def bad_fetcher(url):
        raise urllib.error.URLError("connection refused")

    assert probe_asias_liveness(fetcher=bad_fetcher) is False


def test_liveness_probe_true_on_200():
    assert probe_asias_liveness(fetcher=lambda u: (200, "<html>ok</html>")) is True


def test_liveness_probe_false_on_503():
    assert probe_asias_liveness(fetcher=lambda u: (503, "Service Unavailable")) is False


def test_no_url_returns_no_url_reason():
    result = validate_faa_aids_url_extended(None, retry_once=False)
    assert not result.viable
    assert result.reason == "no_url"
    assert result.bucket == BUCKET_NOT_WORKING


def test_retry_once_recovers_from_transient_503():
    calls = {"n": 0}

    def fetcher(url):
        calls["n"] += 1
        if calls["n"] == 1:
            return 503, "Service Unavailable"
        return 200, BRIEF_REPORT_BODY

    result = validate_faa_aids_url_extended(
        FAA_BRIEF_URL,
        url_mode="brief",
        fetcher=fetcher,
        retry_once=True,
    )
    assert calls["n"] == 2
    assert result.product_viable
    assert result.bucket == BUCKET_BRIEF_REPORT


def test_db_should_remain_active_brief_mode():
    from app.ingestion.url_builders.faa_aids_viability import db_should_remain_active

    assert db_should_remain_active(BUCKET_BRIEF_REPORT, "brief") is True
    assert db_should_remain_active(BUCKET_SEARCH_PREFILL, "brief") is False
    assert db_should_remain_active(BUCKET_NOT_WORKING, "brief") is False
    assert db_should_remain_active(BUCKET_SEARCH_PREFILL, "search") is True
