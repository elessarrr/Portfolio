"""NTSB URL builders (CAROL, docket, legacy brief)."""

from typing import Any, Dict, List, Optional

from app.ingestion.link_schema import normalize_link_entry
from app.ingestion.link_schema import is_placeholder_url


def carol_detail_has_public_content(source_data: Optional[Dict[str, Any]]) -> bool:
    """CAROL detail SPA often renders empty despite bulk narrative (DirectorBrief, foreign-led)."""
    data = source_data or {}
    agency = (data.get("cm_agency") or "NTSB").strip().upper()
    if agency == "OTHER":
        # Accredited-rep cases (e.g. DCA17RA058 Bishkek): narrative may exist in bulk data
        # but CAROL detail and docket remain empty on ntsb.gov.
        return False
    report_type = (data.get("cm_reportType") or "").strip()
    if report_type == "DirectorBrief":
        # Engine/component briefs publish to the docket, not CAROL investigation detail.
        return False
    for key in ("factualNarrative", "prelimNarrative", "analysisNarrative"):
        text = (data.get(key) or "").strip()
        if len(text) > 40:
            return True
    if report_type and report_type not in ("None", "N/A"):
        return True
    return False


def _is_carol_detail_url(url: str) -> bool:
    return "carol.ntsb.gov/investigations/detail/" in (url or "").lower()


def build_ntsb_source_url(
    *,
    source_record_id: Optional[str],
    source_url: Optional[str] = None,
    source_data: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    links = build_ntsb_links(
        source_record_id=source_record_id,
        source_url=source_url,
        report_url=None,
        source_data=source_data,
    )
    for link in links:
        if link.get("role") in ("investigation", "primary", "brief"):
            return link["url"]
    for link in links:
        if link.get("role") != "docket":
            return link["url"]
    return links[0]["url"] if links else None


def build_ntsb_links(
    *,
    source_record_id: Optional[str],
    source_url: Optional[str] = None,
    report_url: Optional[str] = None,
    source_data: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    links: List[Dict[str, str]] = []
    data = source_data or {}

    if source_url and not is_placeholder_url(source_url):
        if _is_carol_detail_url(source_url) and not carol_detail_has_public_content(data):
            pass
        else:
            role = "investigation"
            if "brief.aspx" in source_url:
                role = "brief"
            elif "Docket" in source_url:
                role = "docket"
            links.append(normalize_link_entry(url=source_url, role=role, label="NTSB"))

    ntsb_num = (source_record_id or data.get("cm_ntsbNum") or data.get("ntsb_id") or "").strip()
    cm_key = data.get("cm_mkey") or data.get("mkey")
    if cm_key and carol_detail_has_public_content(data):
        carol = f"https://carol.ntsb.gov/investigations/detail/{cm_key}"
        if not any(link["url"] == carol for link in links):
            links.append(normalize_link_entry(url=carol, role="investigation", label="CAROL"))

    if ntsb_num and not ntsb_num.startswith("http"):
        is_prelim_wa = "WA" in ntsb_num.upper()
        foreign_led = (data.get("cm_agency") or "").strip().upper() == "OTHER"
        if (not is_prelim_wa and not foreign_led) or carol_detail_has_public_content(data):
            docket = f"https://data.ntsb.gov/Docket/?NTSBNumber={ntsb_num}"
            if not any(link["url"] == docket for link in links):
                links.append(normalize_link_entry(url=docket, role="docket", label="NTSB Docket"))

    ev_id = data.get("ev_id") or data.get("cm_ev_id")
    if ev_id is not None:
        brief = f"https://www.ntsb.gov/Pages/brief.aspx?ev_id={ev_id}&key=0"
        if not any(link["url"] == brief for link in links):
            links.append(normalize_link_entry(url=brief, role="brief", label="NTSB Brief"))

    if report_url and not is_placeholder_url(report_url):
        if not any(link["url"] == report_url for link in links):
            links.append(normalize_link_entry(url=report_url, role="report", label="NTSB Report"))

    return links
