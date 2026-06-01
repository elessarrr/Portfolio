"""NTSB single-URL resolution for IncidentSource.source_url (no links[] blob)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from app.ingestion.url_builders.ntsb_viability import Fetcher, validate_ntsb_url


def carol_detail_has_public_content(source_data: Optional[Dict[str, Any]]) -> bool:
    data = source_data or {}
    agency = (data.get("cm_agency") or "NTSB").strip().upper()
    if agency == "OTHER":
        return False
    report_type = (data.get("cm_reportType") or "").strip()
    if report_type == "DirectorBrief":
        return False
    for key in ("factualNarrative", "prelimNarrative", "analysisNarrative"):
        text = (data.get(key) or "").strip()
        if len(text) > 40:
            return True
    if report_type and report_type not in ("None", "N/A"):
        return True
    return False


def _docket_url(ntsb_num: str) -> Optional[str]:
    if ntsb_num and not ntsb_num.startswith("http"):
        return f"https://data.ntsb.gov/Docket/?NTSBNumber={ntsb_num}"
    return None


def _carol_detail_url(source_data: Dict[str, Any]) -> Optional[str]:
    if carol_detail_has_public_content(source_data) and source_data.get("cm_mkey"):
        return f"https://carol.ntsb.gov/investigations/detail/{source_data['cm_mkey']}"
    return None


def resolve_ntsb_source_url_checked(
    source_record_id: Optional[str],
    source_data: Optional[Dict[str, Any]] = None,
    *,
    fetcher: Fetcher,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate CAROL then docket (then brief) via `fetcher`; return (url, failure_reason).
    """
    data = source_data or {}
    ntsb_num = (source_record_id or data.get("cm_ntsbNum") or data.get("ntsb_id") or "").strip()

    carol_url = _carol_detail_url(data)
    docket_url = _docket_url(ntsb_num)
    last_reason = "no_viable_url"

    for candidate in (carol_url, docket_url):
        if not candidate:
            continue
        viable, _, reason = validate_ntsb_url(candidate, fetcher=fetcher)
        if viable:
            return candidate, None
        if reason:
            last_reason = reason

    ev_id = data.get("ev_id") or data.get("cm_ev_id")
    if ev_id is not None:
        brief = f"https://www.ntsb.gov/Pages/brief.aspx?ev_id={ev_id}&key=0"
        viable, _, reason = validate_ntsb_url(brief, fetcher=fetcher)
        if viable:
            return brief, None
        if reason:
            last_reason = reason

    return None, last_reason


def resolve_ntsb_source_url(
    source_record_id: Optional[str],
    source_data: Optional[Dict[str, Any]] = None,
    *,
    fetcher: Optional[Fetcher] = None,
) -> Optional[str]:
    """
    Pick one honest outbound URL at import time.
    Foreign-led (cm_agency=Other) and DirectorBrief never get CAROL detail URLs.

    When `fetcher` is provided, CAROL and docket candidates are validated via
    `validate_ntsb_url()` (CAROL empty SPA shells fall back to docket).
    """
    data = source_data or {}
    ntsb_num = (source_record_id or data.get("cm_ntsbNum") or data.get("ntsb_id") or "").strip()

    carol_url = _carol_detail_url(data)
    docket_url = _docket_url(ntsb_num)

    if fetcher is not None:
        url, _ = resolve_ntsb_source_url_checked(
            source_record_id, source_data, fetcher=fetcher
        )
        return url

    if carol_url:
        return carol_url

    if docket_url:
        return docket_url

    ev_id = data.get("ev_id") or data.get("cm_ev_id")
    if ev_id is not None:
        return f"https://www.ntsb.gov/Pages/brief.aspx?ev_id={ev_id}&key=0"

    return None


def is_foreign_led_ntsb(source_data: Optional[Dict[str, Any]]) -> bool:
    data = source_data or {}
    return (data.get("cm_agency") or "").strip().upper() == "OTHER"
