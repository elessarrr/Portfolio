"""Resolve external URLs for incident sources (shared by templates and routes)."""

from typing import Dict, List, Optional, Tuple

from app.ingestion.link_schema import get_links_from_source_data, is_placeholder_url, sanitize_url
from app.ingestion.url_builders import (
    build_asn_links,
    build_asn_source_url,
    build_faa_aids_links,
    build_faa_aids_source_url,
    build_faa_sdr_links,
    build_faa_sdr_source_url,
    build_ntsb_links,
    build_ntsb_source_url,
)
from app.models import Incident, IncidentSource

def build_links_for_source(source: IncidentSource) -> List[Dict[str, str]]:
    """Build normalized link list for a source row."""
    name = source.source_name or ""
    if name == "NTSB":
        return build_ntsb_links(
            source_record_id=source.source_record_id,
            source_url=source.source_url,
            report_url=source.report_url,
            source_data=source.source_data if isinstance(source.source_data, dict) else None,
        )
    if name == "ASN":
        return build_asn_links(
            source_record_id=source.source_record_id,
            source_url=source.source_url,
        )
    if name == "FAA_AIDS":
        return build_faa_aids_links(
            source_record_id=source.source_record_id,
            source_url=source.source_url,
        )
    if name == "FAA_SDR":
        return build_faa_sdr_links(source_record_id=source.source_record_id)
    if name == "MEDIA":
        url = sanitize_url(source.source_url)
        return [{"role": "press", "url": url, "label": "Press"}] if url else []

    links = get_links_from_source_data(source.source_data)
    if links:
        return [link for link in links if not is_placeholder_url(link.get("url"))]
    url = sanitize_url(source.report_url or source.source_url)
    return [{"role": "primary", "url": url}] if url else []


def resolve_source_hrefs(source: IncidentSource) -> List[Tuple[str, str, str]]:
    """Return (url, role, label) tuples for all clickable links on a source."""
    if not source or not source.is_active:
        return []
    out: List[Tuple[str, str, str]] = []
    seen = set()
    for link in build_links_for_source(source):
        url = sanitize_url(link.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        role = link.get("role") or "primary"
        label = link.get("label") or (source.source_name or "Source")
        out.append((url, role, label))
    return out


def resolve_ntsb_href(source: IncidentSource) -> Optional[str]:
    """Prefer CAROL investigation page; fall back to NTSB docket lookup."""
    if not source:
        return None
    return build_ntsb_source_url(
        source_record_id=source.source_record_id,
        source_url=source.source_url,
        source_data=source.source_data if isinstance(source.source_data, dict) else None,
    )


def resolve_source_href(source: IncidentSource) -> Optional[str]:
    """Primary public URL for a single active source, or None if not linkable."""
    hrefs = resolve_source_hrefs(source)
    if not hrefs:
        return None
    if source.source_name == "NTSB":
        for url, role, _label in hrefs:
            if role in ("investigation", "brief", "primary"):
                return url
        for url, role, _label in hrefs:
            if role == "docket":
                return url
    if source.source_name == "FAA_AIDS":
        for url, role, _label in hrefs:
            if role == "primary":
                return url
        return None
    return hrefs[0][0]


def pick_primary_source(active_sources: List[IncidentSource]) -> Optional[IncidentSource]:
    sorted_sources = sorted(active_sources, key=lambda s: s.source_name or "")
    by_name: Dict[str, List[IncidentSource]] = {}
    for source in sorted_sources:
        by_name.setdefault(source.source_name, []).append(source)
    for name in ("NTSB", "FAA_AIDS", "FAA_SDR", "ASN", "MEDIA"):
        if by_name.get(name):
            return by_name[name][0]
    return sorted_sources[0] if sorted_sources else None


def resolve_primary_href(incident: Incident) -> Optional[str]:
    sources = list(incident.sources.all())
    active = [s for s in sources if s.is_active]
    primary = pick_primary_source(active)
    if not primary:
        return None
    return resolve_source_href(primary)


def incident_has_active_link(incident: Incident) -> bool:
    for source in incident.sources.all():
        if source.is_active and resolve_source_href(source):
            return True
    return False


def is_foreign_led_ntsb(source: IncidentSource) -> bool:
    """NTSB participated as accredited rep; host state leads (no public CAROL/docket)."""
    if (source.source_name or "").upper() != "NTSB":
        return False
    data = source.source_data if isinstance(source.source_data, dict) else {}
    return (data.get("cm_agency") or "").strip().upper() == "OTHER"


def incident_has_foreign_led_ntsb(incident: Incident) -> bool:
    for source in incident.sources.all():
        if is_foreign_led_ntsb(source):
            return True
    return False
