from __future__ import annotations

from url_audit.classify import (
    BUCKET_BRIEF,
    BUCKET_NOT_WORKING,
    BUCKET_SEARCH,
    classify_audit_result,
    is_retryable,
)
from url_audit.config import SourceConfig


def _source(**kwargs: object) -> SourceConfig:
    defaults = dict(
        name="test",
        liveness_url="https://example.com/",
        url_modes=["brief", "search"],
        brief_markers=["factual narrative"],
        search_markers=["clear search"],
        not_working_markers=["errors.edgesuite.net"],
        retryable_status_codes=[503, 504],
        retryable_body_markers=["errors.edgesuite.net"],
    )
    defaults.update(kwargs)
    return SourceConfig(**defaults)  # type: ignore[arg-type]


def test_classify_brief_page_brief_mode() -> None:
    source = _source()
    result = classify_audit_result(
        source,
        url="https://host/brief",
        url_mode="brief",
        http_status=200,
        body="<html>Factual Narrative here</html>",
    )
    assert result.bucket == BUCKET_BRIEF
    assert result.link_viable is True
    assert result.product_viable is True
    assert result.reason is None


def test_classify_search_intermediate_brief_mode() -> None:
    source = _source()
    result = classify_audit_result(
        source,
        url="https://host/search",
        url_mode="brief",
        http_status=200,
        body="<form>Clear Search</form>",
    )
    assert result.bucket == BUCKET_SEARCH
    assert result.link_viable is True
    assert result.product_viable is False


def test_classify_not_working_404() -> None:
    source = _source()
    result = classify_audit_result(
        source,
        url="https://host/missing",
        url_mode="brief",
        http_status=404,
        body="not found",
    )
    assert result.bucket == BUCKET_NOT_WORKING
    assert result.link_viable is False
    assert result.reason == "http_404"


def test_classify_cdn_marker() -> None:
    source = _source()
    result = classify_audit_result(
        source,
        url="https://host/x",
        url_mode="search",
        http_status=200,
        body="errors.edgesuite.net outage",
    )
    assert result.bucket == BUCKET_NOT_WORKING
    assert result.reason == "body_marker"


def test_is_retryable_status_and_body() -> None:
    source = _source()
    assert is_retryable(source, http_status=503, body="")
    assert is_retryable(source, http_status=200, body="errors.edgesuite.net")
    assert not is_retryable(source, http_status=404, body="")
