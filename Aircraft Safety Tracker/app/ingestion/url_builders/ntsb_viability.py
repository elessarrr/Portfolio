"""NTSB URL viability checks for enrichment audit and import gate (FR-5).

Known dead-end patterns (from product review 2026-05-28 / QA 2026-05-31):
- Docket URLs (`data.ntsb.gov/Docket/`) returning HTTP 200 with body text
  *"The docket for this investigation has not been released"* — common for
  foreign-led accredited-rep cases (`cm_agency=Other`, `*WA*`, `*RA*` numbers)
  where CAROL is blocked and the docket fallback is empty.
- CAROL detail URLs (`carol.ntsb.gov/investigations/detail/{mkey}`) returning
  HTTP 200 with an empty React SPA shell (`<main id="root"></main>`) — no
  investigation content without a rendered browser; manual click-through also
  shows blank pages (QA 2026-05-31).
- DirectorBrief records often resolve to docket URLs that are similarly unreleased
  (`cm_reportType=DirectorBrief` → no CAROL → docket not released).
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Callable, Optional, Tuple

FetchResult = Tuple[int, str]
Fetcher = Callable[[str], FetchResult]

UNRELEASED_DOCKET_PHRASE = "has not been released"
CAROL_CONTENT_MARKERS = (
    "ntsb number",
    "event date",
    "probable cause",
    "investigation status",
    "highest injury",
    "factual narrative",
)
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_USER_AGENT = "AircraftSafetyTracker/1.0 (NTSB enrichment audit)"


def _default_fetch(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> FetchResult:
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        return response.status, body


def is_carol_empty_spa_shell(body: str) -> bool:
    """
    True when CAROL detail HTML is the empty React bootstrap (no investigation data).

    Static HTTP fetch cannot execute JS; real CAROL detail pages served this way
    are never viable Details links — prefer docket fallback when available.
    """
    if not body or not str(body).strip():
        return True
    lower = body.lower()
    if any(marker in lower for marker in CAROL_CONTENT_MARKERS):
        return False
    if 'id="root"' in lower or "id='root'" in lower:
        return True
    if "you need to enable javascript" in lower and len(body) < 8000:
        return True
    return False


def validate_ntsb_url(
    url: Optional[str],
    *,
    fetcher: Optional[Fetcher] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Return (viable, status_code, reason).

    viable=True when the URL appears to lead to real public content.
    """
    if not url or not str(url).strip():
        return False, None, "no_url"

    fetch = fetcher
    if fetch is None:
        fetch = lambda u: _default_fetch(u, timeout=timeout)

    try:
        status, body = fetch(url)
    except urllib.error.HTTPError as exc:
        return False, exc.code, f"http_{exc.code}"
    except urllib.error.URLError:
        return False, None, "url_error"
    except Exception:
        return False, None, "fetch_error"

    lower_url = url.lower()
    lower_body = body.lower()

    if "data.ntsb.gov/docket" in lower_url:
        if UNRELEASED_DOCKET_PHRASE in lower_body:
            return False, status, "docket_not_released"

    if "carol.ntsb.gov/investigations/detail" in lower_url:
        if is_carol_empty_spa_shell(body):
            return False, status, "carol_empty_spa"

    if status >= 400:
        return False, status, f"http_{status}"

    return True, status, None
