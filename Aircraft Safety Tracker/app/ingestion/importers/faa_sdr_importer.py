import datetime
from typing import Any, Dict, Iterable, List, Optional

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.ingestion.bulk.faa_sdr_bulk import iter_sdr_records
from app.ingestion.importers.base import DataSourceImporter


def _is_retryable_fetch_error(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if not isinstance(exc, httpx.HTTPStatusError):
        return False
    status_code = exc.response.status_code if exc.response is not None else 0
    return status_code == 429 or 500 <= status_code < 600


class FAASDRImporter(DataSourceImporter):
    source_name = "FAA_SDR"
    base_url = "https://drs.faa.gov"
    search_endpoint = "/browse/excelExternalWindow/"
    request_timeout_seconds = 30
    target_manufacturers = ("BOEING", "AIRBUS")
    request_user_agent = "AircraftSafetyTracker/1.0"
    retry_attempts = 5
    retry_wait_multiplier_seconds = 1
    retry_wait_min_seconds = 1
    retry_wait_max_seconds = 30

    def __init__(self, records: Optional[Iterable[Dict[str, Any]]] = None, **kwargs):
        super().__init__(**kwargs)
        self._records = list(records or [])

    def fetch(self) -> List[Dict[str, Any]]:
        if self._records:
            seed_records = self._filter_target_manufacturers(self._records)
            return self._apply_incremental_window(seed_records)

        records: List[Dict[str, Any]] = []
        seen: set = set()
        for manufacturer in self.target_manufacturers:
            remote_records = self._fetch_remote_records(manufacturer)
            for record in remote_records:
                key = self._record_identity(record)
                if key in seen:
                    continue
                seen.add(key)
                records.append(record)
        return self._apply_incremental_window(records)

    def _fetch_remote_records(self, manufacturer: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}{self.search_endpoint}"
        with httpx.Client(
            follow_redirects=True,
            timeout=self.request_timeout_seconds,
            headers={
                "User-Agent": self.request_user_agent,
                "Accept": "text/csv,*/*",
            },
        ) as client:
            payload = self._request_csv_payload(client, url, manufacturer)

        if not self._looks_like_csv(payload):
            return []

        parsed = list(iter_sdr_records(payload))
        for row in parsed:
            row.setdefault("manufacturer", manufacturer)
        return self._filter_target_manufacturers(parsed)

    @retry(
        reraise=True,
        stop=stop_after_attempt(retry_attempts),
        wait=wait_exponential(
            multiplier=retry_wait_multiplier_seconds,
            min=retry_wait_min_seconds,
            max=retry_wait_max_seconds,
        ),
        retry=retry_if_exception(_is_retryable_fetch_error),
    )
    def _request_csv_payload(self, client: httpx.Client, url: str, manufacturer: str) -> str:
        response = client.get(
            url,
            params={
                "manufacturer": manufacturer,
                "format": "csv",
            },
        )
        response.raise_for_status()
        return response.text or ""

    def _filter_target_manufacturers(
        self, records: Iterable[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        for row in records:
            if not isinstance(row, dict):
                continue
            haystack = " ".join(
                str(row.get(key) or "")
                for key in (
                    "manufacturer",
                    "make",
                    "mfr_name",
                    "aircraft_make",
                    "aircraft_model",
                    "model",
                )
            ).upper()
            if any(target in haystack for target in self.target_manufacturers):
                filtered.append(dict(row))
        return filtered

    def _record_identity(self, row: Dict[str, Any]):
        return (
            str(
                row.get("control_number")
                or row.get("sdr_number")
                or row.get("report_number")
                or row.get("id")
                or ""
            )
            .strip()
            .upper(),
            str(row.get("event_date") or row.get("date") or "").strip(),
            str(row.get("aircraft_model") or row.get("model") or "").strip().upper(),
        )

    def _looks_like_csv(self, payload: str) -> bool:
        stripped = (payload or "").strip()
        if not stripped:
            return False
        prefix = stripped[:64].lower()
        if prefix.startswith("<!doctype html") or prefix.startswith("<html"):
            return False
        head_line = stripped.splitlines()[0] if stripped.splitlines() else ""
        return "," in head_line or "\t" in head_line

    def _apply_incremental_window(self, records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Incremental imports rely on self.start_date (set from ImportState.last_successful_at)
        # to avoid re-fetching and re-processing older historical records.
        if self.start_date is None:
            return list(records)

        filtered: List[Dict[str, Any]] = []
        for row in records:
            record_date = self._extract_record_date(row)
            if record_date is None:
                continue
            if record_date >= self.start_date:
                filtered.append(dict(row))
        return filtered

    def _extract_record_date(self, row: Dict[str, Any]) -> Optional[datetime.date]:
        for key in ("event_date", "date", "report_date", "occurrence_date"):
            value = row.get(key)
            parsed_date = self._parse_date_value(value)
            if parsed_date is not None:
                return parsed_date
        return None

    def _parse_date_value(self, value: Any) -> Optional[datetime.date]:
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value

        text = str(value).strip()
        if not text:
            return None

        # FAA/legacy feeds can alternate date layouts; support the common variants.
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%d-%b-%Y"):
            try:
                return datetime.datetime.strptime(text, fmt).date()
            except ValueError:
                continue

        try:
            return datetime.date.fromisoformat(text[:10])
        except ValueError:
            return None
