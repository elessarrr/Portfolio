import os
import random
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin

import httpx


class NTSBApiError(RuntimeError):
    pass


class NTSBApiClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 5,
        backoff_base_seconds: float = 0.8,
        backoff_max_seconds: float = 20.0,
        sleep: Callable[[float], None] = time.sleep,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.base_url = (base_url or os.environ.get('NTSB_API_BASE_URL') or '').strip()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_max_seconds = backoff_max_seconds
        self.sleep = sleep
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=timeout_seconds,
            headers={
                'User-Agent': 'AircraftSafetyTracker/1.0',
                'Accept': 'application/json',
            },
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def request_json(self, method: str, path_or_url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = self._build_url(path_or_url)
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.request(method, url, params=params)
                if response.status_code == 429:
                    retry_after = response.headers.get('retry-after')
                    delay = self._compute_delay(attempt, retry_after)
                    self.sleep(delay)
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                    status = exc.response.status_code
                    if status in {400, 401, 403, 404}:
                        break
                    if status == 429:
                        delay = self._compute_delay(attempt, exc.response.headers.get('retry-after'))
                        self.sleep(delay)
                        continue

                delay = self._compute_delay(attempt, None)
                self.sleep(delay)

        raise NTSBApiError(f'NTSB API request failed: {url}') from last_error

    def iter_batches(
        self,
        path_or_url: str,
        base_params: Optional[Dict[str, Any]] = None,
        batch_size: int = 500,
        offset_param: str = 'offset',
        limit_param: str = 'limit',
        max_batches: Optional[int] = None,
    ) -> Iterable[List[Dict[str, Any]]]:
        params = dict(base_params or {})
        offset = int(params.get(offset_param) or 0)
        params[limit_param] = int(params.get(limit_param) or batch_size)
        params[offset_param] = offset

        batches = 0
        while True:
            payload = self.request_json('GET', path_or_url, params=params)
            items, has_more = self._extract_items(payload, params[limit_param])
            if not items:
                return

            yield items
            batches += 1
            if max_batches is not None and batches >= max_batches:
                return
            if not has_more:
                return
            params[offset_param] = int(params[offset_param]) + int(params[limit_param])

    def _build_url(self, path_or_url: str) -> str:
        if path_or_url.startswith('http://') or path_or_url.startswith('https://'):
            return path_or_url
        if not self.base_url:
            raise NTSBApiError('NTSB_API_BASE_URL is not configured')
        return urljoin(self.base_url.rstrip('/') + '/', path_or_url.lstrip('/'))

    def _compute_delay(self, attempt: int, retry_after: Optional[str]) -> float:
        if retry_after:
            try:
                return max(0.0, min(float(retry_after), self.backoff_max_seconds))
            except Exception:
                pass
        base = min(self.backoff_base_seconds * (2 ** max(0, attempt - 1)), self.backoff_max_seconds)
        jitter = random.uniform(0.0, min(0.25 * base, 1.5))
        return min(self.backoff_max_seconds, base + jitter)

    def _extract_items(self, payload: Any, batch_size: int) -> Tuple[List[Dict[str, Any]], bool]:
        if isinstance(payload, list):
            items = [item for item in payload if isinstance(item, dict)]
            return items, len(items) >= batch_size

        if isinstance(payload, dict):
            for key in ('results', 'data', 'items', 'records'):
                value = payload.get(key)
                if isinstance(value, list):
                    items = [item for item in value if isinstance(item, dict)]
                    has_more = payload.get('next') is not None or len(items) >= batch_size
                    return items, bool(has_more)

        return [], False

