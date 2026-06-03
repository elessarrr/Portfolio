"""FAA AIDS per-record ASIAS URL builder (PRD 0007 FR-3)."""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote

# Page 12 — search form with report number pre-filled (extra "Search AIDS" click required).
ASIAS_AIDS_SEARCH_TEMPLATE = (
    "https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:{report_id}"
)
# Page 18 — brief report view (direct record; discovered 2026-06-01 product QA).
ASIAS_AIDS_BRIEF_REPORT_TEMPLATE = (
    "https://www.asias.faa.gov/apex/f?p=100:18:::NO::AP_BRIEF_RPT_VAR:{report_id}"
)

# Legacy alias used by importers today.
ASIAS_AIDS_TEMPLATE = ASIAS_AIDS_SEARCH_TEMPLATE


def _encode_report_id(source_record_id: Optional[str]) -> Optional[str]:
    if source_record_id is None:
        return None
    rid = str(source_record_id).strip()
    if not rid:
        return None
    return quote(rid, safe="")


def build_faa_aids_search_url(source_record_id: Optional[str]) -> Optional[str]:
    """ASIAS AIDS search form with ``P12_AIDS_RPRT_NBR`` pre-filled."""
    encoded = _encode_report_id(source_record_id)
    if encoded is None:
        return None
    return ASIAS_AIDS_SEARCH_TEMPLATE.format(report_id=encoded)


def build_faa_aids_brief_report_url(source_record_id: Optional[str]) -> Optional[str]:
    """ASIAS AIDS brief report page ``AP_BRIEF_RPT_VAR`` (page 18)."""
    encoded = _encode_report_id(source_record_id)
    if encoded is None:
        return None
    return ASIAS_AIDS_BRIEF_REPORT_TEMPLATE.format(report_id=encoded)


def build_faa_aids_url(source_record_id: Optional[str]) -> Optional[str]:
    """Return ASIAS AIDS brief report URL for control number ``c5`` (page 18; PRD 0007.2 / 0009)."""
    return build_faa_aids_brief_report_url(source_record_id)
