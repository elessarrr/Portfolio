"""Pick a single primary Details URL for an incident (main-style, no JSON link stack)."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from app.ingestion.link_schema import is_catalog_url, is_placeholder_url
from app.models import Incident, IncidentSource

SOURCE_PRIORITY = ("NTSB", "FAA_AIDS", "FAA_SDR", "ASN")


def _valid_url(url: Optional[str]) -> bool:
    if not url or not str(url).strip():
        return False
    if is_placeholder_url(url) or is_catalog_url(url):
        return False
    return True


def _active_sources(sources: Iterable[IncidentSource]) -> List[IncidentSource]:
    return [s for s in sources if s.is_active is not False]


def pick_primary_href(
    incident: Incident,
    sources: Optional[Iterable[IncidentSource]] = None,
) -> Optional[str]:
    """
    Priority: Incident.asn_url → first valid IncidentSource (NTSB, then FAA_AIDS).
    Returns None when no honest outbound link exists.
    """
    if incident.asn_url and _valid_url(incident.asn_url):
        return incident.asn_url.strip()

    by_name: Dict[str, List[IncidentSource]] = {}
    for source in _active_sources(sources or []):
        name = (source.source_name or "").upper()
        by_name.setdefault(name, []).append(source)

    for name in SOURCE_PRIORITY:
        for source in by_name.get(name, []):
            if _valid_url(source.source_url):
                return source.source_url.strip()

    return None


def display_make_model(
    sources: Optional[Iterable[IncidentSource]] = None,
) -> Optional[str]:
    """Exact NTSB make/model string from source metadata (FR-21.4); ASN rows return None."""
    for source in _active_sources(sources or []):
        if (source.source_name or "").upper() != "NTSB":
            continue
        data = source.source_data or {}
        raw = data.get("ntsb_make_model") or data.get("make_model")
        if raw and str(raw).strip():
            return str(raw).strip()
    return None
