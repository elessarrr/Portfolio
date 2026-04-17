import csv
import io
import os
import random
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, cast

import httpx


class FAAAIDSError(RuntimeError):
    pass


def build_faa_aids_zip_url(year: int, month: Optional[int] = None) -> str:
    template = (os.environ.get("FAA_AIDS_ZIP_URL_TEMPLATE") or "").strip()
    if not template:
        raise FAAAIDSError("FAA_AIDS_ZIP_URL_TEMPLATE is not configured")

    if month is None:
        return template.format(year=year)
    if month < 1 or month > 12:
        raise FAAAIDSError("month must be 1-12")
    return template.format(year=year, month=f"{month:02d}")


def download_aids_zip_bytes(
    url: str,
    *,
    timeout_seconds: float = 60.0,
    max_retries: int = 5,
    backoff_base_seconds: float = 0.8,
    backoff_max_seconds: float = 30.0,
    sleep=time.sleep,
    transport: Optional[httpx.BaseTransport] = None,
) -> bytes:
    last_error: Optional[Exception] = None

    with httpx.Client(
        follow_redirects=True,
        timeout=timeout_seconds,
        headers={
            "User-Agent": "AircraftSafetyTracker/1.0",
            "Accept": "*/*",
        },
        transport=transport,
    ) as client:
        for attempt in range(1, max_retries + 1):
            try:
                resp = client.get(url)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("retry-after")
                    delay = _compute_delay(
                        attempt, retry_after, backoff_base_seconds, backoff_max_seconds
                    )
                    sleep(delay)
                    continue
                resp.raise_for_status()
                return resp.content
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                delay = _compute_delay(attempt, None, backoff_base_seconds, backoff_max_seconds)
                sleep(delay)

    raise FAAAIDSError(f"Failed to download FAA AIDS zip: {url}") from last_error


def extract_aids_zip_bytes(zip_bytes: bytes, dest_dir: Path) -> List[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted: List[Path] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for member in zf.infolist():
            member_name = member.filename
            if not member_name or member_name.endswith("/"):
                continue
            if _is_unsafe_zip_path(member_name):
                raise FAAAIDSError("Zip contains unsafe paths")
            target_path = dest_dir / member_name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, "r") as src, open(target_path, "wb") as dst:
                dst.write(src.read())
            extracted.append(target_path)
    return extracted


def iter_aids_records(
    extracted_paths: Sequence[Path],
    *,
    include_globs: Sequence[str] = ("*.txt", "*.tsv", "*.csv"),
    max_bytes_per_file: int = 50_000_000,
) -> Iterator[Dict[str, Any]]:
    candidates = _filter_paths(extracted_paths, include_globs)
    for path in candidates:
        if not path.is_file():
            continue
        if path.stat().st_size > max_bytes_per_file:
            raise FAAAIDSError("Input file too large")

        with open(path, "rb") as raw:
            sample = raw.read(8192)
            raw.seek(0)
            if b"\x00" in sample:
                continue
            text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
            dialect = _detect_dialect(sample)
            reader = csv.DictReader(text, dialect=dialect)
            for row in reader:
                if not row:
                    continue
                yield dict(row)


def _filter_paths(paths: Sequence[Path], include_globs: Sequence[str]) -> List[Path]:
    include_patterns = tuple(include_globs)
    results: List[Path] = []
    for path in paths:
        for pattern in include_patterns:
            if path.match(pattern):
                results.append(path)
                break
    return results


def _detect_dialect(sample_bytes: bytes) -> csv.Dialect:
    sample_text = sample_bytes.decode("utf-8", errors="replace")
    try:
        sniffed = csv.Sniffer().sniff(sample_text, delimiters="\t,;|")
        if getattr(sniffed, "delimiter", None) in {"\t", ",", ";", "|"}:
            return cast(csv.Dialect, sniffed)
    except Exception:
        pass
    return cast(csv.Dialect, csv.excel_tab())


def _is_unsafe_zip_path(name: str) -> bool:
    normalized = name.replace("\\", "/")
    if normalized.startswith("/"):
        return True
    parts = [p for p in normalized.split("/") if p]
    if any(p == ".." for p in parts):
        return True
    return False


def _compute_delay(
    attempt: int, retry_after: Optional[str], base: float, max_seconds: float
) -> float:
    if retry_after:
        try:
            return max(0.0, min(float(retry_after), max_seconds))
        except Exception:
            pass
    exp = min(base * (2 ** max(0, attempt - 1)), max_seconds)
    jitter = random.uniform(0.0, min(0.25 * exp, 2.0))
    return min(max_seconds, exp + jitter)
