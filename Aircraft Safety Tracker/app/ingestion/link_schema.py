"""Minimal URL validation for import-time source_url contracts."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

PLACEHOLDER_HOSTS = frozenset({"example.com", "www.example.com"})
FAA_CATALOG_PATH_MARKERS = frozenset({"f?p=100:11", "f?p=100:1:"})
ASIAS_RECORD_MARKER = "p12_aids_rprt_nbr"


def is_placeholder_url(url: Optional[str]) -> bool:
    if not url or not str(url).strip():
        return True
    try:
        host = (urlparse(url.strip()).hostname or "").lower()
    except ValueError:
        return True
    return host in PLACEHOLDER_HOSTS


def is_catalog_url(url: Optional[str]) -> bool:
    """Reject FAA ASIAS catalog/search pages without a per-record report id."""
    if not url:
        return False
    lower = url.strip().lower()
    if "asias.faa.gov" not in lower:
        return False
    if ASIAS_RECORD_MARKER in lower:
        return False
    return any(marker in lower for marker in FAA_CATALOG_PATH_MARKERS)


def assert_valid_source_url(url: Optional[str]) -> None:
    if is_placeholder_url(url):
        raise ValueError(f"placeholder or empty URL rejected: {url!r}")
    if is_catalog_url(url):
        raise ValueError(f"catalog URL rejected: {url!r}")


def assert_source_data_metadata_only(source_data: Optional[dict]) -> None:
    """source_data must not carry a links[] blob used for display (v3 rule)."""
    if not source_data or not isinstance(source_data, dict):
        return
    if "links" in source_data:
        raise ValueError("source_data must not contain a links[] blob on v3 branch")
