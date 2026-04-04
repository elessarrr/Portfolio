import csv
import io
import os
import random
import time
from typing import Any, Dict, Iterator, Optional

import httpx


class FAASDRError(RuntimeError):
    pass


def build_faa_sdr_csv_url(year: int) -> str:
    template = (os.environ.get('FAA_SDR_CSV_URL_TEMPLATE') or '').strip()
    if not template:
        raise FAASDRError('FAA_SDR_CSV_URL_TEMPLATE is not configured')
    return template.format(year=year)


def download_sdr_csv_text(
    url: str,
    *,
    timeout_seconds: float = 60.0,
    max_retries: int = 5,
    backoff_base_seconds: float = 0.8,
    backoff_max_seconds: float = 30.0,
    sleep=time.sleep,
    transport: Optional[httpx.BaseTransport] = None,
) -> str:
    last_error: Optional[Exception] = None

    with httpx.Client(
        follow_redirects=True,
        timeout=timeout_seconds,
        headers={
            'User-Agent': 'AircraftSafetyTracker/1.0',
            'Accept': 'text/csv,*/*',
        },
        transport=transport,
    ) as client:
        for attempt in range(1, max_retries + 1):
            try:
                resp = client.get(url)
                if resp.status_code == 429:
                    retry_after = resp.headers.get('retry-after')
                    delay = _compute_delay(attempt, retry_after, backoff_base_seconds, backoff_max_seconds)
                    sleep(delay)
                    continue
                resp.raise_for_status()
                return resp.text
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                delay = _compute_delay(attempt, None, backoff_base_seconds, backoff_max_seconds)
                sleep(delay)

    raise FAASDRError(f'Failed to download FAA SDR CSV: {url}') from last_error


def iter_sdr_records(csv_text: str) -> Iterator[Dict[str, Any]]:
    if not csv_text:
        return
    stream = io.StringIO(csv_text)
    sample = csv_text[:4096]
    dialect = _detect_dialect(sample)
    reader = csv.DictReader(stream, dialect=dialect)
    for row in reader:
        if not row:
            continue
        yield dict(row)


def _detect_dialect(sample_text: str) -> csv.Dialect:
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=[',', '\t', ';', '|'])
    except Exception:
        dialect = csv.excel
    if getattr(dialect, 'delimiter', None) not in {',', '\t', ';', '|'}:
        dialect = csv.excel
    return dialect


def _compute_delay(attempt: int, retry_after: Optional[str], base: float, max_seconds: float) -> float:
    if retry_after:
        try:
            return max(0.0, min(float(retry_after), max_seconds))
        except Exception:
            pass
    exp = min(base * (2 ** max(0, attempt - 1)), max_seconds)
    jitter = random.uniform(0.0, min(0.25 * exp, 2.0))
    return min(max_seconds, exp + jitter)

