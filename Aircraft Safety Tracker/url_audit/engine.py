"""Core audit loop: liveness, concurrency, jitter, retry (PRD 0008)."""

from __future__ import annotations

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Sequence

from url_audit.classify import Classification, classify_audit_result, is_retryable
from url_audit.config import SourceConfig
from url_audit.http import FetchResult, Fetcher, UrlFetcher
from url_audit.io import UrlRow, write_audit_jsonl

DEFAULT_CONCURRENCY = 16
JITTER_MS_MIN = 50
JITTER_MS_MAX = 200


class LivenessError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuditRunOptions:
    concurrency: int = DEFAULT_CONCURRENCY
    timeout_seconds: int = 15
    use_jitter: bool = True
    use_retry: bool = True
    skip_liveness: bool = False
    user_agent: Optional[str] = None


def probe_liveness(
    source: SourceConfig,
    fetcher: Fetcher,
    *,
    skip: bool = False,
) -> None:
    if skip:
        return
    status, _ = fetcher(source.liveness_url)
    if status is None or not (200 <= status < 300):
        raise LivenessError(
            f"Liveness probe failed for {source.name!r}: "
            f"{source.liveness_url} returned HTTP {status!r}"
        )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _jitter_sleep(use_jitter: bool) -> None:
    if not use_jitter:
        return
    delay_ms = random.randint(JITTER_MS_MIN, JITTER_MS_MAX)
    time.sleep(delay_ms / 1000.0)


def audit_one_url(
    source: SourceConfig,
    *,
    url: str,
    url_mode: str,
    metadata: Dict[str, object],
    fetcher: Fetcher,
    use_jitter: bool,
    use_retry: bool,
) -> Dict[str, object]:
    _jitter_sleep(use_jitter)
    status, body = _fetch_with_retry(source, url, fetcher, use_retry=use_retry)
    classification = classify_audit_result(
        source, url=url, url_mode=url_mode, http_status=status, body=body
    )
    return _row_from_classification(
        url=url,
        url_mode=url_mode,
        metadata=metadata,
        classification=classification,
    )


def _fetch_with_retry(
    source: SourceConfig,
    url: str,
    fetcher: Fetcher,
    *,
    use_retry: bool,
) -> FetchResult:
    status, body = fetcher(url)
    if not use_retry:
        return status, body
    if is_retryable(source, http_status=status, body=body):
        time.sleep(0.25)
        return fetcher(url)
    return status, body


def _row_from_classification(
    *,
    url: str,
    url_mode: str,
    metadata: Dict[str, object],
    classification: Classification,
) -> Dict[str, object]:
    row: Dict[str, object] = dict(metadata)
    row.update(
        {
            "url": url,
            "http_status": classification.http_status,
            "link_viable": classification.link_viable,
            "product_viable": classification.product_viable,
            "bucket": classification.bucket,
            "reason": classification.reason,
            "checked_at": _utc_now_iso(),
            "url_mode": url_mode,
        }
    )
    return row


def run_audit(
    source: SourceConfig,
    rows: Sequence[UrlRow],
    *,
    url_mode: str,
    options: AuditRunOptions,
    fetcher: Optional[Fetcher] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> List[Dict[str, object]]:
    """Run bulk audit; returns result rows (does not write files)."""
    if fetcher is None:
        from url_audit.http import DEFAULT_USER_AGENT, HttpOptions

        ua = options.user_agent or DEFAULT_USER_AGENT
        fetcher = UrlFetcher(
            HttpOptions(timeout_seconds=options.timeout_seconds, user_agent=ua)
        )

    probe_liveness(source, fetcher, skip=options.skip_liveness)

    total = len(rows)
    results: List[Dict[str, object]] = []
    workers = max(1, options.concurrency)

    def _work(row: UrlRow) -> Dict[str, object]:
        return audit_one_url(
            source,
            url=row.url,
            url_mode=url_mode,
            metadata=dict(row.metadata),
            fetcher=fetcher,
            use_jitter=options.use_jitter,
            use_retry=options.use_retry,
        )

    if workers == 1 or total <= 1:
        for i, row in enumerate(rows):
            results.append(_work(row))
            if on_progress:
                on_progress(i + 1, total)
        return results

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_work, row): row for row in rows}
        done = 0
        for fut in as_completed(futures):
            results.append(fut.result())
            done += 1
            if on_progress:
                on_progress(done, total)

    return results


def run_audit_to_file(
    source: SourceConfig,
    rows: Sequence[UrlRow],
    *,
    url_mode: str,
    output_path,
    options: AuditRunOptions,
    fetcher: Optional[Fetcher] = None,
) -> List[Dict[str, object]]:
    results = run_audit(
        source, rows, url_mode=url_mode, options=options, fetcher=fetcher
    )
    write_audit_jsonl(output_path, results)
    return results
