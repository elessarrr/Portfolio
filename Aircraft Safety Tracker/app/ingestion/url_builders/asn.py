"""ASN (Aviation Safety Network) URL builders."""

import re
from typing import Any, Dict, List, Optional

from app.ingestion.link_schema import normalize_link_entry
from app.ingestion.link_schema import is_placeholder_url

_WIKIBASE_ID_RE = re.compile(r"^(\d+)$")
_WIKIBASE_PATH_RE = re.compile(r"wikibase/(\d+)", re.I)


def build_asn_source_url(
    *,
    source_record_id: Optional[str],
    source_url: Optional[str] = None,
) -> Optional[str]:
    links = build_asn_links(source_record_id=source_record_id, source_url=source_url)
    return links[0]["url"] if links else None


def build_asn_links(
    *,
    source_record_id: Optional[str],
    source_url: Optional[str] = None,
) -> List[Dict[str, str]]:
    links: List[Dict[str, str]] = []

    if source_url and not is_placeholder_url(source_url):
        links.append(normalize_link_entry(url=source_url, role="primary", label="ASN"))
        return links

    record = (source_record_id or "").strip()
    if not record:
        return links

    if record.startswith("http"):
        if not is_placeholder_url(record):
            links.append(normalize_link_entry(url=record, role="primary", label="ASN"))
        return links

    match = _WIKIBASE_PATH_RE.search(record)
    if match:
        wikibase_id = match.group(1)
    elif _WIKIBASE_ID_RE.match(record):
        wikibase_id = record
    else:
        return links

    url = f"https://aviation-safety.net/wikibase/{wikibase_id}"
    links.append(normalize_link_entry(url=url, role="primary", label="ASN"))
    return links
