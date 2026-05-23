"""FAA AIDS URL builders.

FAA bulk AIDS exports do not include stable per-record public URLs in most releases.
We expose a catalog/search landing page when no record-specific URL is known.
"""

from typing import Any, Dict, List, Optional

from app.ingestion.link_schema import normalize_link_entry

FAA_AIDS_CATALOG_URL = "https://www.faa.gov/data_research/accident_incident"


def build_faa_aids_source_url(
    *,
    source_record_id: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Optional[str]:
    if source_url:
        return source_url.strip()
    links = build_faa_aids_links(source_record_id=source_record_id, source_url=source_url)
    return links[0]["url"] if links else None


def build_faa_aids_links(
    *,
    source_record_id: Optional[str] = None,
    source_url: Optional[str] = None,
) -> List[Dict[str, str]]:
    if source_url:
        return [normalize_link_entry(url=source_url, role="primary", label="FAA AIDS")]
    # No stable per-control-number public URL documented; catalog only for discovery.
    if source_record_id:
        return [
            normalize_link_entry(
                url=FAA_AIDS_CATALOG_URL,
                role="catalog",
                label="FAA accident/incident data",
            )
        ]
    return []
