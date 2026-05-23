"""FAA SDR (Service Difficulty Reports) URL builders."""

from typing import Dict, List, Optional
from urllib.parse import quote

from app.ingestion.link_schema import normalize_link_entry

DRS_BASE = "https://drs.faa.gov"


def build_faa_sdr_source_url(*, source_record_id: Optional[str]) -> Optional[str]:
    links = build_faa_sdr_links(source_record_id=source_record_id)
    return links[0]["url"] if links else None


def build_faa_sdr_links(*, source_record_id: Optional[str]) -> List[Dict[str, str]]:
    record = (source_record_id or "").strip()
    if not record:
        return []
    query = quote(record)
    search_url = f"{DRS_BASE}/browse/excelExternalWindow/?search={query}"
    return [
        normalize_link_entry(url=search_url, role="search", label="FAA DRS"),
    ]
