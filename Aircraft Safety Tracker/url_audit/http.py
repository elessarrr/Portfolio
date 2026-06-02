"""HTTP fetch helpers for the portable URL audit engine (stdlib urllib, PRD 0008)."""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_BODY_BYTES = 64 * 1024
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; url-audit/0.1; +https://github.com/portfolio/url-audit)"
)

FetchResult = Tuple[Optional[int], str]


@dataclass(frozen=True)
class HttpOptions:
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    user_agent: str = DEFAULT_USER_AGENT


def fetch_url(url: str, options: Optional[HttpOptions] = None) -> FetchResult:
    """GET *url* with redirect follow; return (status_code, body_text). status None on transport error."""
    opts = options or HttpOptions()
    request = urllib.request.Request(
        url,
        headers={"User-Agent": opts.user_agent},
        method="GET",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=opts.timeout_seconds,
            context=ssl.create_default_context(),
        ) as response:
            status = getattr(response, "status", None) or response.getcode()
            body = _read_body(response, opts.max_body_bytes)
            return int(status), body
    except urllib.error.HTTPError as exc:
        body = _read_body(exc, opts.max_body_bytes)
        return int(exc.code), body
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, ""
    except Exception:
        return None, ""


def _read_body(response: object, max_bytes: int) -> str:
    try:
        raw = response.read(max_bytes + 1)  # type: ignore[attr-defined]
    except Exception:
        return ""
    if isinstance(raw, str):
        return raw[:max_bytes]
    return raw[:max_bytes].decode("utf-8", errors="replace")


Fetcher = Callable[[str], FetchResult]


class UrlFetcher:
    """Thread-safe fetcher wrapper (each call uses urllib; no shared mutable state)."""

    def __init__(self, options: Optional[HttpOptions] = None) -> None:
        self._options = options or HttpOptions()

    def __call__(self, url: str) -> FetchResult:
        return fetch_url(url, self._options)
