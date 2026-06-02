"""Marker-based URL audit classification (PRD 0008 three-tier buckets)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from url_audit.config import SourceConfig

BUCKET_BRIEF = "working_brief_report"
BUCKET_SEARCH = "working_search_prefill"
BUCKET_NOT_WORKING = "not_working"


@dataclass(frozen=True)
class Classification:
    bucket: str
    reason: Optional[str]
    link_viable: bool
    product_viable: bool
    http_status: Optional[int]


def _body_has_markers(body: str, markers: list[str]) -> bool:
    lower = (body or "").lower()
    return any(m.lower() in lower for m in markers if m)


def is_retryable(
    source: SourceConfig,
    *,
    http_status: Optional[int],
    body: str,
) -> bool:
    if http_status is not None and http_status in source.retryable_status_codes:
        return True
    return _body_has_markers(body, source.retryable_body_markers)


def classify_audit_result(
    source: SourceConfig,
    *,
    url: str,
    url_mode: str,
    http_status: Optional[int],
    body: str,
) -> Classification:
    """Classify one URL check into buckets + viability flags."""
    if http_status is None:
        return Classification(
            bucket=BUCKET_NOT_WORKING,
            reason="fetch_error",
            link_viable=False,
            product_viable=False,
            http_status=None,
        )

    lower = (body or "").lower()
    if _body_has_markers(body, source.not_working_markers):
        return _not_working(http_status, "body_marker")

    if http_status == 404:
        return _not_working(http_status, "http_404")

    if http_status >= 400:
        return _not_working(http_status, f"http_{http_status}")

    http_ok = 200 <= http_status < 300
    if not http_ok:
        return _not_working(http_status, f"http_{http_status}")

    looks_brief = _body_has_markers(body, source.brief_markers)
    looks_search = _body_has_markers(body, source.search_markers)

    if url_mode == "brief":
        bucket = _bucket_for_brief_mode(looks_brief, looks_search, lower, url)
    else:
        bucket = _bucket_for_search_mode(looks_brief, looks_search, lower, url)

    if bucket == BUCKET_NOT_WORKING:
        reason = "empty_or_unclassified"
        if len(lower) < 50 and not looks_brief and not looks_search:
            reason = "empty_body"
        return _not_working(http_status, reason)

    return Classification(
        bucket=bucket,
        reason=None,
        link_viable=True,
        product_viable=bucket == BUCKET_BRIEF,
        http_status=http_status,
    )


def _not_working(http_status: Optional[int], reason: str) -> Classification:
    return Classification(
        bucket=BUCKET_NOT_WORKING,
        reason=reason,
        link_viable=False,
        product_viable=False,
        http_status=http_status,
    )


def _bucket_for_brief_mode(
    looks_brief: bool, looks_search: bool, lower: str, url: str
) -> str:
    if looks_brief:
        return BUCKET_BRIEF
    if looks_search and not looks_brief:
        return BUCKET_SEARCH
    if looks_brief and looks_search:
        return BUCKET_BRIEF
    url_lower = (url or "").lower()
    if "brief" in url_lower or ":18:" in url_lower:
        return BUCKET_BRIEF if looks_brief else BUCKET_SEARCH
    if looks_search:
        return BUCKET_SEARCH
    if not looks_brief and not looks_search and len(lower) < 50:
        return BUCKET_NOT_WORKING
    return BUCKET_SEARCH


def _bucket_for_search_mode(
    looks_brief: bool, looks_search: bool, lower: str, url: str
) -> str:
    if looks_brief and not looks_search:
        return BUCKET_BRIEF
    if looks_search:
        return BUCKET_SEARCH
    url_lower = (url or "").lower()
    if "search" in url_lower or ":12:" in url_lower or "p12_aids" in url_lower:
        return BUCKET_SEARCH
    if "brief" in url_lower or ":18:" in url_lower:
        return BUCKET_BRIEF
    if not looks_brief and not looks_search and len(lower) < 50:
        return BUCKET_NOT_WORKING
    return BUCKET_SEARCH
