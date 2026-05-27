"""NTSB single-URL resolution for IncidentSource.source_url (no links[] blob)."""

from __future__ import annotations

from typing import Any, Dict, Optional


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


def resolve_ntsb_source_url(
    source_record_id: Optional[str],
    source_data: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Pick one honest outbound URL at import time.
    Foreign-led (cm_agency=Other) and DirectorBrief never get CAROL detail URLs.
    """
    data = source_data or {}
    ntsb_num = (source_record_id or data.get("cm_ntsbNum") or data.get("ntsb_id") or "").strip()

    # Prefer CAROL when there is public content and an investigation key.
    # `carol_detail_has_public_content` already enforces "Other" + "DirectorBrief" rules.
    if carol_detail_has_public_content(data) and data.get("cm_mkey"):
        return f"https://carol.ntsb.gov/investigations/detail/{data['cm_mkey']}"

    if ntsb_num and not ntsb_num.startswith("http"):
        return f"https://data.ntsb.gov/Docket/?NTSBNumber={ntsb_num}"

    ev_id = data.get("ev_id") or data.get("cm_ev_id")
    if ev_id is not None:
        return f"https://www.ntsb.gov/Pages/brief.aspx?ev_id={ev_id}&key=0"

    return None


def is_foreign_led_ntsb(source_data: Optional[Dict[str, Any]]) -> bool:
    data = source_data or {}
    return (data.get("cm_agency") or "").strip().upper() == "OTHER"
