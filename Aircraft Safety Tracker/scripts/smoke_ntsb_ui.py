#!/usr/bin/env python3
"""Post-import NTSB UI smoke check (Task 7.3 repeatability).

Requires a running Flask app and DATABASE_URL pointing at aircraft_safety_v3.db
(development config defaults to v3 when DATABASE_URL is unset).

Usage:
    export FLASK_APP=run.py
    flask run -p 5003
    PYTHONPATH=. python scripts/smoke_ntsb_ui.py --base-url http://127.0.0.1:5003
"""

from __future__ import annotations

import argparse
import re
import sys
import httpx

# Aircraft pages: Stearman, A320, AS350, 737-800 (jet + helicopter coverage)
DEFAULT_PAGES = [
    (68, "Stearman", ["Kaydet", "Make/Model", "Boeing A75"]),
    (78, "Airbus A320", ["Airbus A320", "Make/Model", "Airbus Industrie"]),
    (99, "AS350 helicopter", ["AS350", "Make/Model", "AIRBUS"]),
    (23, "Boeing 737-800", ["737-800", "Make/Model", "Boeing 737-800"]),
]

NTSB_HREF_SAMPLE = 3
REQUEST_TIMEOUT = 30
DOCKET_TIMEOUT = 20


def check(name: str, ok: bool, detail: str, issues: list[str]) -> None:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        issues.append(f"{name}: {detail}")


def run_smoke(base_url: str, sample_hrefs: int) -> int:
    client = httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True)
    issues: list[str] = []

    print(f"NTSB UI smoke — {base_url}\n")

    r = client.get(f"{base_url}/search?q=Boeing")
    check("search HTTP 200", r.status_code == 200, str(r.status_code), issues)
    check(
        "search finds Boeing",
        r.status_code == 200 and "Boeing" in r.text and "No aircraft found" not in r.text,
        "",
        issues,
    )

    for aid, label, needles in DEFAULT_PAGES:
        print(f"\n/aircraft/{aid} ({label})")
        r = client.get(f"{base_url}/aircraft/{aid}")
        check("page HTTP 200", r.status_code == 200, str(r.status_code), issues)
        check("Make/Model column", "Make/Model" in r.text, "", issues)
        check(
            "Boeing or Airbus on page",
            "Boeing" in r.text or "Airbus" in r.text,
            "",
            issues,
        )
        for needle in needles:
            check(f"contains {needle!r}", needle in r.text, "", issues)
        check("Details links", "Details" in r.text, "", issues)
        check(
            "no unreleased docket copy in HTML",
            "not been released" not in r.text.lower(),
            "",
            issues,
        )

        hrefs = re.findall(r'href="(https://data\.ntsb\.gov[^"]+)"', r.text)
        sample = hrefs[:sample_hrefs]
        print(f"    NTSB hrefs: {len(hrefs)} on page; checking {len(sample)}")
        for href in sample:
            try:
                hr = client.get(
                    href,
                    timeout=DOCKET_TIMEOUT,
                    headers={"User-Agent": "AircraftSafetyTracker-smoke/1.0"},
                )
                body = (hr.text or "")[:8000].lower()
                bad = "has not been released" in body
                check(
                    f"docket {href[-24:]}",
                    hr.status_code == 200 and not bad,
                    f"status={hr.status_code}",
                    issues,
                )
            except httpx.HTTPError as exc:
                check(f"docket {href[-24:]}", False, str(exc), issues)

    client.close()

    if issues:
        print(f"\nFAILED ({len(issues)} issue(s)):")
        for item in issues:
            print(f"  - {item}")
        return 1

    print("\nALL PASS")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5003",
        help="Flask base URL (default: http://127.0.0.1:5003)",
    )
    parser.add_argument(
        "--sample-hrefs",
        type=int,
        default=NTSB_HREF_SAMPLE,
        help="NTSB docket URLs to fetch per aircraft page",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    sys.exit(run_smoke(base, args.sample_hrefs))


if __name__ == "__main__":
    main()
