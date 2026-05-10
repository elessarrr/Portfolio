"""
WebSearchService for the WA Incident Press Enrichment job (Task 1.0).

Encapsulates all web-search logic used by the `flask enrich-wa-incidents`
CLI command. Supports tiered searching:
  Tier 1 – Aviation Herald (aviation-herald.com) — direct URL
  Tier 2 – Major news wires (Reuters, AP, BBG) via search
  Tier 3 – General web search

Search backend priority:
  1. GOOGLE_CSE_API_KEY + GOOGLE_CSE_CX env vars → Google Custom Search
  2. SERPAPI_API_KEY env var → SerpAPI (Cloudflare-bypassing, paid but cheap)
  3. Fallbacks → Bing Lite / DuckDuckGo HTML scraping

URL validation uses the same pattern as the ingestion base validators.
Rate-limiting is per-domain (0.3 s default) to avoid IP bans.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_SEARCH_ENGINE_DOMAINS = {
    "bing.com",
    "www.bing.com",
    "r.bing.com",
    "lite.bing.com",
    "duckduckgo.com",
    "www.duckduckgo.com",
    "google.com",
    "www.google.com",
    "search.yahoo.com",
}

_TIER1_ALLOWED_DOMAINS = ("avherald.com", "aviation-herald.com")
_TIER2_ALLOWED_DOMAINS = ("reuters.com", "apnews.com", "bloomberg.com")
_LOW_SIGNAL_PORTAL_DOMAINS = {
    "msn.com",
    "www.msn.com",
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A single article candidate returned by one search tier."""
    url: str
    title: Optional[str] = None
    tier: int = 0          # 1, 2, or 3
    domain: str = ""


@dataclass
class EnrichmentResult:
    """Per-incident result from the full enrichment pipeline."""
    incident_id: int
    ntsb_event_id: Optional[str]
    articles: List[SearchResult] = field(default_factory=list)
    skipped: bool = False
    skip_reason: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Domain-level rate limiter
# ---------------------------------------------------------------------------

_DOMAIN_DELAY = 0.3          # seconds between requests to the same domain
_domain_last_seen: dict = {}


def _rate_limit(url: str) -> None:
    """Throttle requests to avoid hammering the same domain."""
    if not url:
        return
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return
    now = time.monotonic()
    prev = _domain_last_seen.get(domain)
    if prev is not None:
        elapsed = now - prev
        if elapsed < _DOMAIN_DELAY:
            time.sleep(_DOMAIN_DELAY - elapsed)
    _domain_last_seen[domain] = time.monotonic()


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def _retry(fn, max_attempts=3, base_delay=1.0, exceptions=(Exception,)):
    """
    Retry a callable with exponential backoff for specific exception types.

    Args:
        fn:               Callable to execute.
        max_attempts:     Maximum number of attempts (default 3).
        base_delay:       Initial delay in seconds, doubled each retry (default 1.0).
        exceptions:       Tuple of exception classes to catch and retry (default all).

    Raises the last exception if all attempts fail.
    """
    last_err = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except exceptions as exc:
            last_err = exc
            if attempt < max_attempts - 1:
                time.sleep(base_delay * (2 ** attempt))
    raise last_err


# ---------------------------------------------------------------------------
# URL Validation
# ---------------------------------------------------------------------------

def validate_url(url: str, timeout: float = 10.0) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate that a URL returns HTTP 200 with a non-empty body.

    Retries on transient HTTP errors (timeout, transport error) up to 3 times
    with exponential backoff (1.0 s base). Non-transient errors (4xx/5xx
    response, empty body) are returned immediately without retry.

    Returns (is_valid, http_status, error_detail).
    """
    if not url:
        return False, None, "url_is_none"

    def _get():
        client = httpx.Client(timeout=timeout, follow_redirects=True)
        try:
            _rate_limit(url)
            return client.get(url)
        finally:
            client.close()

    try:
        response = _retry(_get, max_attempts=3, base_delay=1.0,
                          exceptions=(httpx.TimeoutException, httpx.TransportError))
    except (httpx.TimeoutException, httpx.TransportError):
        return False, None, "timeout_or_transport_error_after_retry"

    if response.status_code >= 400:
        return False, response.status_code, f"http_{response.status_code}"
    text = response.text
    if not text or len(text.strip()) < 100:
        return False, response.status_code, "body_too_small"
    return True, response.status_code, None


def _domain_matches(domain: str, allowed_roots: Tuple[str, ...]) -> bool:
    host = (domain or "").lower()
    return any(host == root or host.endswith(f".{root}") for root in allowed_roots)


def _is_candidate_allowed(url: str, tier: int) -> bool:
    """
    Basic quality gate before expensive validation/network calls:
    - reject search engine pages
    - reject obvious homepage/root URLs
    - enforce domain constraints for tier 1 and tier 2
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    domain = (parsed.netloc or "").lower()
    path = parsed.path or ""

    if not domain or any(_domain_matches(domain, (root,)) for root in _SEARCH_ENGINE_DOMAINS):
        return False
    if domain in _LOW_SIGNAL_PORTAL_DOMAINS:
        return False
    if path in ("", "/"):
        return False
    if path in ("/play", "/search"):
        return False
    if _domain_matches(domain, ("microsoft.com",)) and (
        path.startswith("/bing") or path.startswith("/fwlink")
    ):
        return False
    if tier == 1 and not _domain_matches(domain, _TIER1_ALLOWED_DOMAINS):
        return False
    if tier == 2 and not _domain_matches(domain, _TIER2_ALLOWED_DOMAINS):
        return False
    return True


# ---------------------------------------------------------------------------
# Search tier query builders
# ---------------------------------------------------------------------------

def _build_aviation_herald_query(event_id: str, registration: str, date: str) -> str:
    """Tier 1 – Aviation Herald site-specific query."""
    parts = [f'"{event_id}"']
    if registration:
        parts.append(f'"{registration}"')
    if date:
        parts.append(date[:4])   # year
    return " ".join(parts)


def _build_news_wire_query(event_id: str, registration: str, operator: str, date: str) -> str:
    """Tier 2 – Major news wires (Reuters, AP, BBG) via DuckDuckGo."""
    parts = [f'"{event_id}"']
    if registration:
        parts.append(f'"{registration}"')
    if operator:
        parts.append(operator)
    if date:
        parts.append(date[:4])
    return " ".join(parts)


def _build_general_query(event_id: str, registration: str, operator: str, location: str, date: str) -> str:
    """Tier 3 – General web via DuckDuckGo."""
    parts = ["aviation incident", f'"{event_id}"']
    if registration:
        parts.append(f'"{registration}"')
    if operator:
        parts.append(operator)
    if location:
        parts.append(location)
    if date:
        parts.append(date[:4])
    return " ".join(parts)


# ---------------------------------------------------------------------------
# HTML parsing helpers (no external dependencies beyond stdlib / httpx)
# ---------------------------------------------------------------------------

def _extract_links_from_html(html: str, base_url: str) -> List[str]:
    """
    Extract all anchor hrefs from an HTML string.
    Used when we scrape a search results page instead of using an API.
    """
    import re
    hrefs = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
    seen = set()
    results = []
    for href in hrefs:
        domain = urlparse(href).netloc.lower()
        if domain not in seen:
            seen.add(domain)
            results.append(href)
    return results


# ---------------------------------------------------------------------------
# Search backends
# ---------------------------------------------------------------------------

_GOOGLE_CSE_API_KEY = None  # lazy-loaded from env
_GOOGLE_CSE_CX = None       # lazy-loaded from env
_SERPAPI_KEY = None         # lazy-loaded from env


def _get_google_cse_config() -> Tuple[Optional[str], Optional[str]]:
    global _GOOGLE_CSE_API_KEY, _GOOGLE_CSE_CX
    if _GOOGLE_CSE_API_KEY is None or _GOOGLE_CSE_CX is None:
        import os
        _GOOGLE_CSE_API_KEY = os.environ.get("GOOGLE_CSE_API_KEY", "") or None
        _GOOGLE_CSE_CX = os.environ.get("GOOGLE_CSE_CX", "") or None
    return _GOOGLE_CSE_API_KEY, _GOOGLE_CSE_CX


def _google_cse_search(query: str, tier: int, max_results: int = 5) -> List[SearchResult]:
    """
    Execute a search via Google Custom Search JSON API.
    Activated when both GOOGLE_CSE_API_KEY and GOOGLE_CSE_CX are set.
    """
    api_key, cx = _get_google_cse_config()
    if not api_key or not cx:
        logger.debug("Google CSE not configured, skipping")
        return []

    try:
        client = httpx.Client(timeout=20.0)
        try:
            _rate_limit("https://www.googleapis.com")
            params = {
                "key": api_key,
                "cx": cx,
                "q": query,
                "num": max(1, min(max_results, 10)),
            }
            resp = client.get("https://www.googleapis.com/customsearch/v1", params=params)
            if resp.status_code != 200:
                logger.warning("Google CSE returned %s: %s", resp.status_code, query)
                return []
            data = resp.json()
            items = data.get("items", [])
            results = []
            for item in items[:max_results]:
                link = item.get("link", "")
                if link:
                    results.append(SearchResult(
                        url=link,
                        title=item.get("title"),
                        tier=tier,
                        domain=urlparse(link).netloc,
                    ))
            return results
        finally:
            client.close()
    except Exception as exc:
        logger.warning("Google CSE search failed for '%s': %s", query, exc)
        return []


def _get_serpapi_key() -> Optional[str]:
    global _SERPAPI_KEY
    if _SERPAPI_KEY is None:
        import os
        _SERPAPI_KEY = os.environ.get("SERPAPI_API_KEY", "") or None
    return _SERPAPI_KEY


def _serpapi_search(query: str, tier: int, max_results: int = 5) -> List[SearchResult]:
    """
    Execute a search via SerpAPI (bypasses Cloudflare DDG blocks).
    Set SERPAPI_API_KEY in the environment to activate.
    """
    api_key = _get_serpapi_key()
    if not api_key:
        return []

    try:
        client = httpx.Client(timeout=20.0)
        try:
            _rate_limit("https://serpapi.com")
            params = {
                "q": query,
                "api_key": api_key,
                "engine": "duckduckgo",
                # switch to engine=google for higher-quality results if needed
                "num": max_results,
            }
            resp = client.get("https://serpapi.com/search", params=params)
            if resp.status_code != 200:
                if resp.status_code == 401:
                    logger.warning("SerpAPI auth failure (401) — check SERPAPI_API_KEY env var")
                elif resp.status_code == 429:
                    logger.warning("SerpAPI quota exhausted (429) — daily limit reached, search skipped")
                else:
                    logger.warning("SerpAPI returned %s: %s", resp.status_code, query)
                return []
            data = resp.json()
            organic = data.get("organic_results", [])
            results = []
            for r in organic[:max_results]:
                link = r.get("link", "")
                if link:
                    results.append(SearchResult(
                        url=link,
                        title=r.get("title"),
                        tier=tier,
                        domain=urlparse(link).netloc,
                    ))
            return results
        finally:
            client.close()
    except Exception as exc:
        logger.warning("SerpAPI search failed for '%s': %s", query, exc)
        return []


def _bing_lite_search(query: str, tier: int, max_results: int = 5) -> List[SearchResult]:
    """
    Execute a web search via Bing Lite (lite.bing.com) HTML interface.
    Used as fallback when DuckDuckGo is Cloudflare-blocked.
    """
    try:
        client = httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        try:
            _rate_limit("https://lite.bing.com")
            encoded_q = query.replace(" ", "+")
            url = f"https://lite.bing.com/search?q={encoded_q}&PC=U523&FORM=CHROMN"
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning("Bing Lite returned %s for query: %s", resp.status_code, query)
                return []
            links = _extract_links_from_html(resp.text, url)
            results = []
            for link in links[:max_results]:
                results.append(SearchResult(
                    url=link,
                    tier=tier,
                    domain=urlparse(link).netloc,
                ))
            return results
        finally:
            client.close()
    except Exception as exc:
        logger.warning("Bing Lite search failed for '%s': %s", query, exc)
        return []


def _duckduckgo_search(query: str, tier: int, max_results: int = 5) -> List[SearchResult]:
    """
    Execute a web search via DuckDuckGo HTML interface and extract result URLs.

    Falls back gracefully when blocked (returns empty list — caller logs warning).
    """
    try:
        client = httpx.Client(timeout=15.0, follow_redirects=True,
                              headers={"User-Agent": "Mozilla/5.0 (compatible; AircraftSafetyBot/1.0)"})
        try:
            _rate_limit("https://duckduckgo.com")
            encoded_q = query.replace(" ", "+")
            url = f"https://duckduckgo.com/html/?q={encoded_q}&kl=us-en"
            resp = client.get(url)
            if resp.status_code != 200:
                logger.warning("DuckDuckGo returned %s for query: %s", resp.status_code, query)
                return []
            links = _extract_links_from_html(resp.text, url)
            results = []
            for link in links[:max_results]:
                results.append(SearchResult(url=link, tier=tier, domain=urlparse(link).netloc))
            return results
        finally:
            client.close()
    except Exception as exc:
        logger.warning("DuckDuckGo search failed for '%s': %s", query, exc)
        return []


def _try_all_backends(query: str, tier: int, max_results: int = 5) -> List[SearchResult]:
    """
    Try all available search backends in priority order:
      1. SerpAPI   (if SERPAPI_API_KEY is set — bypasses Cloudflare DDG blocks)
      2. Google CSE (if GOOGLE_CSE_API_KEY + GOOGLE_CSE_CX are set)
      3. Bing Lite (accessible from most server IPs)
      4. DuckDuckGo (often Cloudflare-blocked from server IPs)

    Returns results from the first backend that returns non-empty results.
    """
    backends = [
        lambda: _serpapi_search(query, tier, max_results),
        lambda: _google_cse_search(query, tier, max_results),
        lambda: _bing_lite_search(query, tier, max_results),
        lambda: _duckduckgo_search(query, tier, max_results),
    ]
    for backend_fn in backends:
        results = backend_fn()
        if results:
            return results
    return []


def _search_aviation_herald(event_id: str, registration: str, date: str) -> List[SearchResult]:
    """
    Tier 1 – Aviation Herald (aviation-herald.com).
    Queries via all backends with a site:aviation-herald.com modifier.
    """
    query = _build_aviation_herald_query(event_id, registration, date)
    return _try_all_backends(
        f"(site:avherald.com OR site:aviation-herald.com) {query}",
        tier=1,
        max_results=3,
    )


def _search_news_wires(event_id: str, registration: str, operator: str, date: str) -> List[SearchResult]:
    """
    Tier 2 – Major news wires (Reuters, Associated Press, Bloomberg).
    """
    query = _build_news_wire_query(event_id, registration, operator, date)
    sites = " OR ".join([f"site:{s}" for s in ("reuters.com", "apnews.com", "bloomberg.com")])
    return _try_all_backends(f"({sites}) {query}", tier=2, max_results=5)


def _search_general(event_id: str, registration: str, operator: str, location: str, date: str) -> List[SearchResult]:
    """
    Tier 3 – General web search.
    """
    query = _build_general_query(event_id, registration, operator, location, date)
    return _try_all_backends(query, tier=3, max_results=5)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class WebSearchService:
    """
    Tiered web search for WA incident press enrichment.

    Usage:
        svc = WebSearchService()
        results = svc.search_tiered(event_id="WPR24LA999", registration="N12345",
                                    operator="Some Airline", location="Tokyo", date="2024-03-15")
    """

    def __init__(self, validate: bool = True):
        """
        Args:
            validate: If True, validate each candidate URL (HTTP GET) before returning.
                      Set False in unit tests to avoid network calls.
        """
        self.validate = validate

    def search_tiered(
        self,
        event_id: str,
        registration: Optional[str] = None,
        operator: Optional[str] = None,
        location: Optional[str] = None,
        date: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Run all three search tiers in order, halting at the first tier that
        returns at least one validated result.

        Args:
            event_id:       NTSB event ID (e.g. "WPR24LA999").
            registration:  Aircraft tail number.
            operator:      Airline / operator name.
            location:      Incident location string.
            date:          ISO date string (YYYY-MM-DD).

        Returns:
            List of validated SearchResult objects from the first successful tier.
            Returns up to 5 validated results.
        """
        tiers = [
            lambda: _search_aviation_herald(event_id, registration, date),
            lambda: _search_news_wires(event_id, registration, operator, date),
            lambda: _search_general(event_id, registration, operator, location, date),
        ]

        for tier_fn in tiers:
            raw_results = tier_fn()
            if not raw_results:
                continue

            if not self.validate:
                # Return raw (unvalidated) results for test environments
                return raw_results[:5]

            validated = []
            for result in raw_results:
                if not _is_candidate_allowed(result.url, result.tier):
                    continue
                is_valid, status, err = validate_url(result.url)
                if is_valid:
                    validated.append(result)
                    if len(validated) >= 5:
                        break

            if validated:
                logger.info(
                    "Tier %d returned %d valid article(s) for event_id=%s",
                    validated[0].tier, len(validated), event_id
                )
                return validated

            # Tier ran but nothing validated — log and continue to next tier
            logger.info(
                "Tier %d found %d candidate(s) but none validated for event_id=%s",
                raw_results[0].tier, len(raw_results), event_id
            )

        logger.info("All tiers exhausted, no valid articles found for event_id=%s", event_id)
        return []
