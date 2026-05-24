#!/usr/bin/env python
"""FR-3.3: Re-probe top URLs from validation results (run ≥24h after validate)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.spikes.faa_aids_spike_lib import (  # noqa: E402
    ARTIFACTS,
    SAMPLES,
    classify_response,
    http_probe,
)

RESULTS_PATH = SAMPLES / "faa-aids-url-validation-results.csv"
STABILITY_PATH = ARTIFACTS / "faa-aids-url-stability.json"
MAX_URLS = 50


def main():
    if not RESULTS_PATH.exists():
        print("Run faa_aids_url_validate.py first")
        sys.exit(1)

    picks = []
    with RESULTS_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["outcome"] in ("match", "redirect_ok") and row["pattern_kind"] != "catalog":
                picks.append(row)
            if len(picks) >= MAX_URLS:
                break

    last_ts = [0.0]
    stable = 0
    details = []
    for row in picks:
        probe = http_probe(row["url"], last_ts)
        outcome = classify_response(
            status_code=probe["status_code"],
            final_url=probe["final_url"],
            body_text=probe["body_text"],
            control_number=row["source_record_id"],
            pattern_kind=row["pattern_kind"],
        )
        ok = outcome in ("match", "redirect_ok")
        stable += int(ok)
        details.append(
            {
                "source_record_id": row["source_record_id"],
                "pattern_id": row["pattern_id"],
                "first_outcome": row["outcome"],
                "second_outcome": outcome,
                "stable": ok,
            }
        )

    out = {
        "urls_retested": len(picks),
        "stable_count": stable,
        "stability_pct": round(100.0 * stable / len(picks), 1) if picks else 0.0,
        "note": "For true FR-3.3, re-run this script ≥24h after initial validate.",
        "details": details[:10],
    }
    STABILITY_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {STABILITY_PATH}: {out['stability_pct']}% stable ({stable}/{len(picks)})")


if __name__ == "__main__":
    main()
