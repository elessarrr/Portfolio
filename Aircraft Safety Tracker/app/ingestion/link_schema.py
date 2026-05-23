"""Common schema for outbound links stored on IncidentSource.source_data."""

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

_PLACEHOLDER_HOSTS = frozenset({"example.com", "example.org", "example.net"})

LINK_ROLES = frozenset(
    {"primary", "investigation", "docket", "report", "brief", "press", "search", "catalog"}
)


def is_placeholder_url(url: Optional[str]) -> bool:
    if not url:
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return True
    return host in _PLACEHOLDER_HOSTS


def sanitize_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    cleaned = url.strip()
    if not cleaned or is_placeholder_url(cleaned):
        return None
    return cleaned


def normalize_link_entry(
    *,
    url: str,
    role: str = "primary",
    label: Optional[str] = None,
) -> Dict[str, str]:
    role_key = (role or "primary").strip().lower()
    if role_key not in LINK_ROLES:
        role_key = "primary"
    entry = {"role": role_key, "url": (url or "").strip()}
    if label:
        entry["label"] = label.strip()
    return entry


def get_links_from_source_data(source_data: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    if not source_data or not isinstance(source_data, dict):
        return []
    links = source_data.get("links")
    if not isinstance(links, list):
        return []
    out = []
    for item in links:
        if isinstance(item, dict) and item.get("url"):
            out.append(
                {
                    "role": str(item.get("role") or "primary"),
                    "url": str(item["url"]).strip(),
                    **({"label": str(item["label"])} if item.get("label") else {}),
                }
            )
    return out


def merge_links_into_source_data(
    source_data: Optional[Dict[str, Any]],
    new_links: List[Dict[str, str]],
) -> Dict[str, Any]:
    data = dict(source_data or {})
    existing = get_links_from_source_data(data)
    seen = {entry["url"] for entry in existing}
    for link in new_links:
        url = (link.get("url") or "").strip()
        if not url or url in seen:
            continue
        existing.append(link)
        seen.add(url)
    data["links"] = existing
    return data
