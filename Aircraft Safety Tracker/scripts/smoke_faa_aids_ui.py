#!/usr/bin/env python3
"""Post-import FAA AIDS UI smoke (catalog pages + FAA source links).

Usage:
    export FLASK_APP=run.py DATABASE_URL=sqlite:///.../data/aircraft_safety_v3.db
    flask run -p 5003
    PYTHONPATH=. python scripts/smoke_faa_aids_ui.py --base-url http://127.0.0.1:5003
"""

from __future__ import annotations

import argparse
import re
import sys

import httpx

DEFAULT_PAGES = [
    (11, "Boeing 727-200", ["727", "Make/Model", "asias.faa.gov"]),
    (23, "Boeing 737-800", ["737", "Make/Model"]),
    (78, "Airbus A320", ["A320", "Make/Model"]),
    (99, "Airbus Helicopters AS350", ["AS350", "Make/Model"]),
]

FAA_HREF_SAMPLE = 3
REQUEST_TIMEOUT = 30


def check(name: str, ok: bool, detail: str, issues: list[str]) -> None:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        issues.append(f"{name}: {detail}")


def run_smoke(base_url: str, sample_hrefs: int) -> int:
    client = httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True)
    issues: list[str] = []
    print(f"FAA AIDS UI smoke — {base_url}\n")

    r = client.get(f"{base_url}/search?q=Boeing")
    check("search HTTP 200", r.status_code == 200, str(r.status_code), issues)

    for aid, label, needles in DEFAULT_PAGES:
        print(f"\n/aircraft/{aid} ({label})")
        r = client.get(f"{base_url}/aircraft/{aid}")
        check("page HTTP 200", r.status_code == 200, str(r.status_code), issues)
        check("Make/Model column", "Make/Model" in r.text, "", issues)
        for needle in needles:
            check(f"contains {needle!r}", needle in r.text, "", issues)
        hrefs = re.findall(r'href="(https://www\.asias\.faa\.gov[^"]+)"', r.text)
        check(
            "FAA AIDS hrefs present",
            len(hrefs) > 0,
            f"found {len(hrefs)}",
            issues,
        )
        sample = hrefs[:sample_hrefs]
        print(f"    FAA hrefs: {len(hrefs)} on page; URL shape check on {len(sample)}")
        for href in sample:
            ok = "asias.faa.gov" in href and (
                "AP_BRIEF_RPT_VAR" in href or "f?p=100:18" in href
            )
            check(f"FAA brief URL shape {href[-24:]}", ok, "", issues)

    print()
    if issues:
        print("FAILED:", len(issues), "issue(s)")
        for item in issues:
            print(" -", item)
        return 1
    print("All checks passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5003")
    parser.add_argument("--sample-hrefs", type=int, default=FAA_HREF_SAMPLE)
    args = parser.parse_args()
    return run_smoke(args.base_url.rstrip("/"), args.sample_hrefs)


if __name__ == "__main__":
    sys.exit(main())
