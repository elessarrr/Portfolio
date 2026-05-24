"""Shared helpers for FAA AIDS URL spike scripts."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
SPIKE_ROOT = REPO_ROOT / "Planning" / "spike-reports"
ARTIFACTS = SPIKE_ROOT / "artifacts"
SAMPLES = SPIKE_ROOT / "samples"
ZIP_CACHE = REPO_ROOT / "data" / "spike" / "faa_aids_zip"

# Latest segment per ASIAS download page (22-MAY-26); blob ck may expire — refresh from p=100:189 if 403.
LATEST_AIDS_ZIP_URL = (
    "https://www.asias.faa.gov/apex/apex_util.get_blob?"
    "s=2309445866411&a=100&c=16566457520604789&p=189&k1=296&k2=&"
    "ck=1NbBA2YZ9sVpuM-jFi3pEfn_Ucv63H5urjUtsKgVD3dytLjHQCAZRwY5SiqTCw7U6og8V0DMaJCc5B1Jhi1PPQ&rt=CR"
)
LATEST_AIDS_ZIP_NAME = "a2020_26.zip"
ASIAS_DOWNLOAD_PAGE = "https://www.asias.faa.gov/apex/f?p=100:189::::NO"

USER_AGENT = "AircraftSafetyTracker/1.0 (faa-aids-url-spike)"
RATE_LIMIT_SECONDS = 1.05

URL_LIKE_KEY_RE = re.compile(r"(url|link|href|http|www\.)", re.I)
CONTROL_IN_BODY_RE = None  # set per probe


def resolve_latest_aids_zip_url(client: Optional[httpx.Client] = None) -> str:
    """Fetch fresh blob URL for a2020_26.zip from ASIAS download page."""
    own = client is None
    if own:
        client = httpx.Client(follow_redirects=True, timeout=60.0, headers={"User-Agent": USER_AGENT})
    try:
        resp = client.get(ASIAS_DOWNLOAD_PAGE)
        resp.raise_for_status()
        # Table row: | a2020_26.zip | ... | href="https://...get_blob?...">
        import re

        pattern = re.compile(
            rf"{re.escape(LATEST_AIDS_ZIP_NAME)}.*?href=\"([^\"]+)\"",
            re.I | re.S,
        )
        m = pattern.search(resp.text)
        if m:
            href = m.group(1)
            if href.startswith("http"):
                return href
            return "https://www.asias.faa.gov/apex/" + href.lstrip("/")
        # Fallback: any get_blob link near filename
        alt = re.search(
            r"href=\"(https://www\.asias\.faa\.gov/apex/apex_util\.get_blob[^\"]+)\"[^>]*>\s*Download Zip File",
            resp.text,
            re.I,
        )
        if alt and LATEST_AIDS_ZIP_NAME.split(".")[0] in resp.text:
            # Last resort: first a2020 blob on page
            blobs = re.findall(
                r"href=\"(https://www\.asias\.faa\.gov/apex/apex_util\.get_blob[^\"]+)\"",
                resp.text,
            )
            for blob in blobs:
                if "k1=296" in blob or "a2020" in resp.text:
                    return blob
        raise RuntimeError(f"Could not find download URL for {LATEST_AIDS_ZIP_NAME} on ASIAS page")
    finally:
        if own:
            client.close()


def rate_sleep(last_ts: List[float]) -> None:
    if last_ts[0]:
        elapsed = time.time() - last_ts[0]
        if elapsed < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - elapsed)
    last_ts[0] = time.time()


def build_url_patterns() -> List[Dict[str, Any]]:
    """Candidate URL patterns (≥3). See spike report for rationale."""

    def _asias_clear(item: str, value: str) -> str:
        return (
            "https://www.asias.faa.gov/apex/f?p=100:12:::NO::"
            f"{item}:{quote(str(value), safe='')}"
        )

    return [
        {
            "id": "faa_catalog",
            "kind": "catalog",
            "label": "FAA.gov data catalog (current fallback)",
            "template": "https://www.faa.gov/data_research/accident_incident",
            "build": lambda row: "https://www.faa.gov/data_research/accident_incident",
        },
        {
            "id": "asias_aids_query_landing",
            "kind": "search",
            "label": "ASIAS AIDS query form (no parameters)",
            "template": "https://www.asias.faa.gov/apex/f?p=100:12::::::",
            "build": lambda row: "https://www.asias.faa.gov/apex/f?p=100:12::::::",
        },
        {
            "id": "asias_clear_aids_rprt_nbr",
            "kind": "direct",
            "label": "ASIAS Apex CLEAR P12_AIDS_RPRT_NBR (report number)",
            "template": "https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:{source_record_id}",
            "build": lambda row: _asias_clear("P12_AIDS_RPRT_NBR", row["source_record_id"])
            if row.get("source_record_id")
            else None,
        },
        {
            "id": "asias_clear_acft_reg",
            "kind": "search",
            "label": "ASIAS Apex CLEAR P12_ACFT_REGIST_NBR",
            "template": "https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_ACFT_REGIST_NBR:{registration}",
            "build": lambda row: _asias_clear("P12_ACFT_REGIST_NBR", row["registration"])
            if row.get("registration")
            else None,
        },
        {
            "id": "asias_clear_narr_srch",
            "kind": "search",
            "label": "ASIAS Apex CLEAR P12_NARR_SRCH (control # in narrative search)",
            "template": "https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_NARR_SRCH:{source_record_id}",
            "build": lambda row: _asias_clear("P12_NARR_SRCH", row["source_record_id"])
            if row.get("source_record_id")
            else None,
        },
    ]


def classify_response(
    *,
    status_code: int,
    final_url: str,
    body_text: str,
    control_number: str,
    pattern_kind: str,
) -> str:
    """Return match | redirect_ok | unrelated | fail."""
    if status_code >= 400 or status_code == 0:
        return "fail"
    if pattern_kind == "catalog":
        return "unrelated"

    needle = (control_number or "").strip()
    if not needle:
        return "fail"

    hay = (body_text or "")[:200_000].lower()
    if needle.lower() in hay:
        return "match" if status_code == 200 else "redirect_ok"

    # Registration-only search pages may not include control #
    if pattern_kind == "search" and status_code in (200, 302) and "aids" in hay:
        return "unrelated"

    return "unrelated"


def http_probe(url: str, last_ts: List[float]) -> Dict[str, Any]:
    rate_sleep(last_ts)
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = client.get(url)
            return {
                "status_code": resp.status_code,
                "final_url": str(resp.url),
                "body_text": resp.text[:200_000],
                "error": None,
            }
    except Exception as exc:
        return {
            "status_code": 0,
            "final_url": url,
            "body_text": "",
            "error": str(exc),
        }
