"""FAA AIDS ASIAS URL viability checks (PRD 0007.1 FR-1, FR-2)."""

from __future__ import annotations

import random
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Literal, Optional, Tuple

import httpx

FetchResult = Tuple[int, str]
Fetcher = Callable[[str], FetchResult]
UrlMode = Literal["search", "brief"]

DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_BODY_BYTES = 65536
DEFAULT_USER_AGENT = "AircraftSafetyTracker/1.0 (FAA AIDS audit)"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

ASIAS_LIVENESS_URL = "https://www.asias.faa.gov/"

BUCKET_NOT_WORKING = "not_working"
BUCKET_BRIEF_REPORT = "working_brief_report"
BUCKET_SEARCH_PREFILL = "working_search_prefill"

RETRYABLE_REASONS = frozenset(
    {
        "asias_cdn_error",
        "asias_backend_timeout",
        "http_503",
        "http_504",
        "fetch_error",
    }
)

ASIAS_CONTENT_MARKERS = (
    "p12_aids_rprt_nbr",
    "aircraft make/model",
    "event date",
    "aids report",
    "air traffic",
    "phase of flight",
    "occurrence",
)

BRIEF_REPORT_MARKERS = (
    "ap_brief",
    "brief report",
    "factual narrative",
)

SEARCH_FORM_MARKERS = (
    "search aids",
    "aids search form",
    "clear search",
    "p12_aids_rprt_nbr",
)

APEX_EMPTY_PATTERNS = (
    "no data found",
    "no rows yet",
    "0 row(s) returned",
    "wwv_flow_t_varchar2()",
    "no records found",
    "session has expired",
    "your session is no longer valid",
    "your session has expired",
    "application express",
)

CDN_ERROR_MARKER = "errors.edgesuite.net"


@dataclass(frozen=True)
class FaaAidsViabilityResult:
    """HTTP check + three-tier product bucket."""

    viable: bool
    http_status: Optional[int]
    reason: Optional[str]
    bucket: str
    product_viable: bool


class HttpxUrlFetcher:
    """Thread-local httpx client with connection pooling and capped body reads."""

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        self._timeout = timeout
        self._max_body_bytes = max_body_bytes
        self._user_agent = user_agent
        self._local = threading.local()

    def _client(self) -> httpx.Client:
        client = getattr(self._local, "client", None)
        if client is None:
            client = httpx.Client(
                timeout=httpx.Timeout(self._timeout),
                follow_redirects=True,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                limits=httpx.Limits(
                    max_connections=64,
                    max_keepalive_connections=32,
                ),
            )
            self._local.client = client
        return client

    def close(self) -> None:
        client = getattr(self._local, "client", None)
        if client is not None:
            client.close()
            self._local.client = None

    def __call__(self, url: str) -> FetchResult:
        with self._client().stream("GET", url) as response:
            status = response.status_code
            chunks = []
            total = 0
            for chunk in response.iter_bytes():
                if not chunk:
                    continue
                chunks.append(chunk)
                total += len(chunk)
                if total >= self._max_body_bytes:
                    break
            body = b"".join(chunks).decode("utf-8", errors="replace")
            return status, body


def _page_heuristics(lower_body: str) -> Tuple[bool, bool]:
    looks_brief = any(marker in lower_body for marker in BRIEF_REPORT_MARKERS)
    looks_search = any(marker in lower_body for marker in SEARCH_FORM_MARKERS)
    return looks_brief, looks_search


def _url_shape(url: str) -> Tuple[bool, bool]:
    lower = (url or "").lower()
    is_brief = "ap_brief_rpt_var" in lower or ":18:" in lower
    is_search = "p12_aids_rprt_nbr" in lower or ":12:" in lower
    return is_brief, is_search


def classify_faa_aids_bucket(
    *,
    http_ok: bool,
    body: str,
    url: str,
    url_mode: UrlMode,
) -> str:
    """Map HTTP success + body/URL shape to a three-tier audit bucket."""
    if not http_ok:
        return BUCKET_NOT_WORKING

    lower = (body or "").lower()
    looks_brief, looks_search = _page_heuristics(lower)
    is_brief_url, is_search_url = _url_shape(url)

    if url_mode == "brief":
        if looks_brief and not looks_search:
            return BUCKET_BRIEF_REPORT
        if looks_brief and looks_search:
            return BUCKET_BRIEF_REPORT
        if looks_search and not looks_brief:
            return BUCKET_SEARCH_PREFILL
        if is_brief_url:
            return BUCKET_BRIEF_REPORT if looks_brief else BUCKET_SEARCH_PREFILL
        return BUCKET_SEARCH_PREFILL

    # search mode — strict: page-12 HTTP OK with only search-form signals → prefill, not brief
    if looks_brief and not looks_search:
        return BUCKET_BRIEF_REPORT
    if looks_search or is_search_url:
        return BUCKET_SEARCH_PREFILL
    if is_brief_url:
        return BUCKET_BRIEF_REPORT
    return BUCKET_SEARCH_PREFILL


def _classify_response(
    status: int, body: str
) -> Tuple[bool, Optional[int], Optional[str]]:
    lower_body = body.lower() if body else ""

    if CDN_ERROR_MARKER in lower_body:
        return False, status, "asias_cdn_error"

    if status == 503:
        return False, status, "asias_cdn_error"

    if status == 504:
        return False, status, "asias_backend_timeout"

    if status == 404:
        return False, status, "asias_record_not_found"

    if status >= 400:
        return False, status, f"http_{status}"

    if any(marker in lower_body for marker in ASIAS_CONTENT_MARKERS):
        return True, status, None

    if any(pattern in lower_body for pattern in APEX_EMPTY_PATTERNS):
        return False, status, "asias_empty_report"

    if status == 200 and len(lower_body) < 3000:
        return False, status, "asias_empty_report"

    return True, status, None


def _fetch_and_classify(
    url: str, fetch: Fetcher
) -> Tuple[bool, Optional[int], Optional[str], str]:
    try:
        status, body = fetch(url)
    except urllib.error.HTTPError as exc:
        reason = "asias_record_not_found" if exc.code == 404 else f"http_{exc.code}"
        return False, exc.code, reason, ""
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        reason = "asias_record_not_found" if code == 404 else f"http_{code}"
        return False, code, reason, ""
    except (urllib.error.URLError, httpx.TimeoutException, httpx.RequestError):
        return False, None, "asias_backend_timeout", ""
    except Exception:
        return False, None, "fetch_error", ""

    http_ok, status, reason = _classify_response(status, body)
    return http_ok, status, reason, body


def probe_asias_liveness(
    fetcher: Optional[Fetcher] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> bool:
    """Return True when ASIAS portal homepage returns HTTP 2xx."""
    if fetcher is not None:
        try:
            status, _ = fetcher(ASIAS_LIVENESS_URL)
            return 200 <= status < 300
        except urllib.error.HTTPError as exc:
            return 200 <= exc.code < 300
        except httpx.HTTPStatusError as exc:
            return 200 <= exc.response.status_code < 300
        except Exception:
            return False

    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            headers={
                "User-Agent": BROWSER_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        ) as client:
            resp = client.get(ASIAS_LIVENESS_URL)
            return 200 <= resp.status_code < 300
    except httpx.HTTPStatusError as exc:
        return 200 <= exc.response.status_code < 300
    except Exception:
        return False


def validate_faa_aids_url_extended(
    url: Optional[str],
    *,
    url_mode: UrlMode = "search",
    user_agent: str = DEFAULT_USER_AGENT,
    fetcher: Optional[Fetcher] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retry_once: bool = True,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
) -> FaaAidsViabilityResult:
    """Fetch URL, classify HTTP failure, then assign three-tier bucket."""
    if not url or not str(url).strip():
        return FaaAidsViabilityResult(
            viable=False,
            http_status=None,
            reason="no_url",
            bucket=BUCKET_NOT_WORKING,
            product_viable=False,
        )

    if fetcher is None:
        pooled = HttpxUrlFetcher(
            timeout=timeout, max_body_bytes=max_body_bytes, user_agent=user_agent
        )
        fetch = pooled
    else:
        fetch = fetcher

    http_ok, status, reason, body = _fetch_and_classify(url, fetch)

    if retry_once and not http_ok and reason in RETRYABLE_REASONS:
        time.sleep(random.uniform(0.05, 0.15))
        http_ok, status, reason, body = _fetch_and_classify(url, fetch)

    bucket = classify_faa_aids_bucket(
        http_ok=http_ok,
        body=body,
        url=url,
        url_mode=url_mode,
    )
    product_viable = bucket == BUCKET_BRIEF_REPORT
    viable = bucket != BUCKET_NOT_WORKING

    return FaaAidsViabilityResult(
        viable=viable,
        http_status=status,
        reason=reason,
        bucket=bucket,
        product_viable=product_viable,
    )


def validate_faa_aids_url(
    url: Optional[str],
    *,
    url_mode: UrlMode = "search",
    user_agent: str = DEFAULT_USER_AGENT,
    fetcher: Optional[Fetcher] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retry_once: bool = True,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
) -> Tuple[bool, Optional[int], Optional[str]]:
    """Return (viable, http_status, reason). Retries once on transient failures when enabled."""
    result = validate_faa_aids_url_extended(
        url,
        url_mode=url_mode,
        user_agent=user_agent,
        fetcher=fetcher,
        timeout=timeout,
        retry_once=retry_once,
        max_body_bytes=max_body_bytes,
    )
    return result.viable, result.http_status, result.reason


def db_should_remain_active(bucket: str, url_mode: UrlMode) -> bool:
    """Whether IncidentSource.is_active should stay True after an audit."""
    if bucket == BUCKET_NOT_WORKING:
        return False
    if url_mode == "brief":
        return bucket == BUCKET_BRIEF_REPORT
    return True
