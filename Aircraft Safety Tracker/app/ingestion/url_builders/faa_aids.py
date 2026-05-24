"""FAA AIDS URL builders — ASIAS direct per-record URLs (PRD 0002 / spike 0001)."""

from typing import Dict, List, Optional
from urllib.parse import quote

from app.ingestion.link_schema import is_placeholder_url, normalize_link_entry, sanitize_url

FAA_AIDS_CATALOG_URL = "https://www.faa.gov/data_research/accident_incident"
ASIAS_AIDS_QUERY_BASE = "https://www.asias.faa.gov/apex/f?p=100:12:::NO::"


def build_faa_aids_primary_url(source_record_id: str) -> str:
    """Direct ASIAS AIDS report URL keyed by control number (bulk field c5)."""
    rid = quote(str(source_record_id).strip(), safe="")
    return f"{ASIAS_AIDS_QUERY_BASE}P12_AIDS_RPRT_NBR:{rid}"


def build_faa_aids_source_url(
    *,
    source_record_id: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Optional[str]:
    links = build_faa_aids_links(source_record_id=source_record_id, source_url=source_url)
    for link in links:
        if link.get("role") == "primary":
            return link["url"]
    return links[0]["url"] if links else None


def build_faa_aids_links(
    *,
    source_record_id: Optional[str] = None,
    source_url: Optional[str] = None,
) -> List[Dict[str, str]]:
    links: List[Dict[str, str]] = []
    record_id = (source_record_id or "").strip()
    explicit = sanitize_url(source_url)

    if record_id:
        asias = build_faa_aids_primary_url(record_id)
        if (
            not explicit
            or explicit == asias
            or is_placeholder_url(explicit)
            or explicit == FAA_AIDS_CATALOG_URL
        ):
            links.append(normalize_link_entry(url=asias, role="primary", label="FAA ASIAS"))
            if not any(link["url"] == FAA_AIDS_CATALOG_URL for link in links):
                links.append(
                    normalize_link_entry(
                        url=FAA_AIDS_CATALOG_URL,
                        role="catalog",
                        label="FAA accident/incident data (catalog)",
                    )
                )
            return links
        links.append(normalize_link_entry(url=explicit, role="primary", label="FAA AIDS"))
        if explicit != asias:
            links.append(normalize_link_entry(url=asias, role="search", label="FAA ASIAS"))
        return links

    if explicit:
        links.append(normalize_link_entry(url=explicit, role="primary", label="FAA AIDS"))
    return links
