#!/usr/bin/env python3
"""Verify audit JSONL working-link sample against live NTSB pages (date, location, make_model)."""

from __future__ import annotations

import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from thefuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "data/logs/ntsb_enrichment_audit_rows.jsonl"
DEFAULT_SAMPLE_OUT = ROOT / ".gstack/qa-reports/ntsb_working_link_sample.json"
DEFAULT_RESULTS = ROOT / ".gstack/qa-reports/ntsb_working_link_verification.json"

USER_AGENT = "AircraftSafetyTracker/1.0 (NTSB working-link field QA)"
PER_REQUEST_DELAY = 0.2


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        t = data.strip()
        if t:
            self.parts.append(t)


def norm_space(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def norm_location(text: Optional[str]) -> str:
    t = norm_space(text).upper()
    t = t.replace(",", " ")
    t = re.sub(r"\b(AO|US|USA)\b", "", t)
    return norm_space(t)


def norm_make_model(text: Optional[str]) -> str:
    t = norm_space(text).upper()
    t = re.sub(r"\b(AIRBUS INDUSTRIE|AIRBUS|BOEING|BOEING HELICOPTERS DIV\.?)\b", "", t)
    t = re.sub(r"[^A-Z0-9]+", " ", t)
    return norm_space(t)


def parse_date(value: Optional[str]) -> Optional[datetime.date]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def fetch_url(url: str, timeout: int = 30) -> Tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def parse_docket_page(html: str) -> Dict[str, Optional[str]]:
    parser = TextExtractor()
    parser.feed(html)
    text = "\n".join(parser.parts)

    def field(label: str) -> Optional[str]:
        m = re.search(rf"{re.escape(label)}:\s*(.+)", text, re.I)
        return norm_space(m.group(1)) if m else None

    city = field("City")
    state = field("State/Region") or field("State")
    location = ", ".join(p for p in [city, state] if p) or None
    return {
        "date": field("Date of Accident"),
        "location": location,
        "city": city,
        "state": state,
        "description": field("Description"),
        "ntsb_number": field("NTSB Number"),
        "page_text": text[:4000],
    }


def compare_date(expected: Optional[str], page_date: Optional[str]) -> Tuple[str, str]:
    exp = parse_date(expected)
    got = parse_date(page_date)
    if exp and got:
        if exp == got:
            return "match", f"page={page_date}"
        return "mismatch", f"expected={expected} page={page_date}"
    if exp and page_date and expected in page_date:
        return "match", f"page={page_date}"
    if not page_date:
        return "unknown", "date not found on page"
    return "mismatch", f"expected={expected} page={page_date}"


def compare_location(expected: Optional[str], page_location: Optional[str]) -> Tuple[str, str]:
    if not expected or not page_location:
        return "unknown", f"expected={expected!r} page={page_location!r}"
    exp = norm_location(expected)
    got = norm_location(page_location)
    ratio = fuzz.token_set_ratio(exp, got)
    if ratio >= 85:
        return "match", f"ratio={ratio} page={page_location}"
    # city-only fallback when audit has CITY, ST
    exp_tokens = set(exp.split())
    got_tokens = set(got.split())
    if exp_tokens and exp_tokens.issubset(got_tokens):
        return "match", f"token_subset page={page_location}"
    return "mismatch", f"ratio={ratio} expected={expected} page={page_location}"


def compare_make_model(expected: Optional[str], page_text: Optional[str]) -> Tuple[str, str]:
    if not expected:
        return "unknown", "no expected make_model"
    if not page_text:
        return "unknown", "no page text"
    exp_norm = norm_make_model(expected)
    if not exp_norm:
        return "unknown", f"could not normalize {expected!r}"
    page_norm = norm_make_model(page_text)
    ratio = fuzz.token_set_ratio(exp_norm, page_norm)
    # also require major tokens (737, A320, etc.)
    tokens = [t for t in exp_norm.split() if len(t) >= 3 or t.isdigit()]
    hits = sum(1 for t in tokens if t in page_norm)
    if ratio >= 70 or (tokens and hits >= max(1, len(tokens) // 2)):
        return "match", f"ratio={ratio} tokens_hit={hits}/{len(tokens)}"
    return "mismatch", f"ratio={ratio} expected={expected}"


def fetch_carol_with_playwright(url: str) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        text = page.inner_text("body")
        browser.close()
        return text


def parse_carol_page(text: str) -> Dict[str, Optional[str]]:
    # CAROL detail pages expose labeled rows in plain text after JS render.
    def field(label: str) -> Optional[str]:
        m = re.search(rf"{re.escape(label)}\s*\n\s*(.+)", text, re.I)
        if m:
            return norm_space(m.group(1))
        m = re.search(rf"{re.escape(label)}:\s*(.+)", text, re.I)
        return norm_space(m.group(1)) if m else None

    city = field("City")
    state = field("State") or field("State/Region")
    location = ", ".join(p for p in [city, state] if p) or field("Location")
    return {
        "date": field("Event Date") or field("Date of Accident") or field("Accident Date"),
        "location": location,
        "city": city,
        "state": state,
        "description": field("Description") or field("Aircraft"),
        "ntsb_number": field("NTSB Number") or field("NTSB No"),
        "page_text": text[:4000],
    }


@dataclass
class FieldResult:
    status: str
    detail: str


@dataclass
class RecordResult:
    index: int
    source_record_id: str
    ntsb_url: str
    page_type: str
    expected_date: Optional[str]
    expected_location: Optional[str]
    expected_make_model: Optional[str]
    page_date: Optional[str]
    page_location: Optional[str]
    page_description: Optional[str]
    date: FieldResult
    location: FieldResult
    make_model: FieldResult
    overall: str
    error: Optional[str] = None


def verify_record(idx: int, rec: Dict[str, Any], use_playwright: bool) -> RecordResult:
    url = rec.get("ntsb_url") or ""
    expected_date = rec.get("date")
    expected_location = rec.get("location")
    expected_make_model = rec.get("make_model")
    source_id = rec.get("source_record_id") or ""

    page_type = "carol" if "carol.ntsb.gov/investigations/detail" in url else "docket"
    page_date = page_location = page_description = None
    page_text = None
    err = None

    try:
        if page_type == "carol":
            if not use_playwright:
                raise RuntimeError("playwright unavailable for CAROL SPA")
            text = fetch_carol_with_playwright(url)
            parsed = parse_carol_page(text)
            page_text = parsed.get("page_text") or text
        else:
            _, html = fetch_url(url)
            parsed = parse_docket_page(html)
            page_text = parsed.get("page_text") or html
        page_date = parsed.get("date")
        page_location = parsed.get("location")
        page_description = parsed.get("description")
    except Exception as exc:
        err = str(exc)
        return RecordResult(
            index=idx,
            source_record_id=source_id,
            ntsb_url=url,
            page_type=page_type,
            expected_date=expected_date,
            expected_location=expected_location,
            expected_make_model=expected_make_model,
            page_date=None,
            page_location=None,
            page_description=None,
            date=FieldResult("error", err),
            location=FieldResult("error", err),
            make_model=FieldResult("error", err),
            overall="error",
            error=err,
        )

    date_r = FieldResult(*compare_date(expected_date, page_date))
    loc_r = FieldResult(*compare_location(expected_location, page_location))
    mm_text = " ".join(filter(None, [page_description, page_text]))
    mm_r = FieldResult(*compare_make_model(expected_make_model, mm_text))

    statuses = [date_r.status, loc_r.status, mm_r.status]
    if any(s == "mismatch" for s in statuses):
        overall = "mismatch"
    elif any(s == "error" for s in statuses):
        overall = "error"
    elif any(s == "unknown" for s in statuses):
        overall = "partial"
    else:
        overall = "pass"

    return RecordResult(
        index=idx,
        source_record_id=source_id,
        ntsb_url=url,
        page_type=page_type,
        expected_date=expected_date,
        expected_location=expected_location,
        expected_make_model=expected_make_model,
        page_date=page_date,
        page_location=page_location,
        page_description=page_description,
        date=date_r,
        location=loc_r,
        make_model=mm_r,
        overall=overall,
    )


def load_working_sample(jsonl_path: Path, every_nth: int = 10) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rec = json.loads(line)
            if rec.get("bucket") == "viable_with_working_link":
                records.append(rec)
    return records[::every_nth]


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


def main() -> int:
    jsonl_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSONL
    sample = load_working_sample(jsonl_path)
    use_pw = playwright_available()

    results: List[RecordResult] = []
    for i, rec in enumerate(sample):
        if i > 0:
            time.sleep(PER_REQUEST_DELAY)
        results.append(verify_record(i, rec, use_pw))
        print(f"[{i+1}/{len(sample)}] {rec.get('source_record_id')} -> {results[-1].overall}", flush=True)

    DEFAULT_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "jsonl_path": str(jsonl_path),
        "sample_size": len(sample),
        "sample_stride": 10,
        "playwright_used": use_pw,
        "summary": {
            "pass": sum(1 for r in results if r.overall == "pass"),
            "partial": sum(1 for r in results if r.overall == "partial"),
            "mismatch": sum(1 for r in results if r.overall == "mismatch"),
            "error": sum(1 for r in results if r.overall == "error"),
        },
        "results": [asdict(r) for r in results],
    }
    DEFAULT_RESULTS.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {DEFAULT_RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
