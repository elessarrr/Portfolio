#!/usr/bin/env python
"""FR-3.2–3: Rate-limited URL validation for sample CSV."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.spikes.faa_aids_spike_lib import (  # noqa: E402
    ARTIFACTS,
    SAMPLES,
    build_url_patterns,
    classify_response,
    http_probe,
)

SAMPLE_PATH = SAMPLES / "faa-aids-url-sample-500.csv"
RESULTS_PATH = SAMPLES / "faa-aids-url-validation-results.csv"
SUMMARY_PATH = ARTIFACTS / "faa-aids-url-validation-summary.json"


def load_sample():
    rows = []
    with SAMPLE_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def main():
    if not SAMPLE_PATH.exists():
        print(f"Missing {SAMPLE_PATH}; run faa_aids_export_sample.py first")
        sys.exit(1)

    rows = load_sample()
    patterns = build_url_patterns()
    last_ts = [0.0]
    results = []
    summary: Counter = Counter()
    by_pattern: Dict[str, Counter] = defaultdict(Counter)

    catalog_probed = False
    for row in rows:
        control = row["source_record_id"]
        for pat in patterns:
            if pat["id"] == "faa_catalog":
                if catalog_probed:
                    results.append(
                        {
                            "incident_source_id": row["incident_source_id"],
                            "source_record_id": control,
                            "pattern_id": pat["id"],
                            "pattern_kind": pat["kind"],
                            "url": pat["template"],
                            "http_status": 200,
                            "final_url": pat["template"],
                            "outcome": "unrelated",
                            "error": "catalog baseline (not per-record)",
                        }
                    )
                    by_pattern[pat["id"]]["unrelated"] += 1
                    continue
                catalog_probed = True

            url = pat["build"](row)
            if not url:
                outcome = "skipped"
                status = 0
                final_url = ""
                err = "missing fields"
            else:
                probe = http_probe(url, last_ts)
                outcome = classify_response(
                    status_code=probe["status_code"],
                    final_url=probe["final_url"],
                    body_text=probe["body_text"],
                    control_number=control,
                    pattern_kind=pat["kind"],
                )
                status = probe["status_code"]
                final_url = probe["final_url"]
                err = probe["error"]
            results.append(
                {
                    "incident_source_id": row["incident_source_id"],
                    "source_record_id": control,
                    "pattern_id": pat["id"],
                    "pattern_kind": pat["kind"],
                    "url": url or "",
                    "http_status": status,
                    "final_url": final_url,
                    "outcome": outcome,
                    "error": err or "",
                }
            )
            key = f"{pat['id']}:{outcome}"
            summary[key] += 1
            by_pattern[pat["id"]][outcome] += 1

    SAMPLES.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as f:
        fields = list(results[0].keys())
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    pattern_stats = {}
    for pat in patterns:
        c = by_pattern[pat["id"]]
        tested = sum(v for k, v in c.items() if k != "skipped")
        success = c.get("match", 0) + c.get("redirect_ok", 0)
        pattern_stats[pat["id"]] = {
            "kind": pat["kind"],
            "label": pat["label"],
            "template": pat["template"],
            "counts": dict(c),
            "success_pct": round(100.0 * success / tested, 1) if tested else 0.0,
        }

    best = max(
        pattern_stats.items(),
        key=lambda x: x[1]["success_pct"]
        if x[1]["kind"] != "catalog"
        else -1,
    )

    out = {
        "sample_size": len(rows),
        "patterns_tested": len(patterns),
        "pattern_stats": pattern_stats,
        "best_non_catalog_pattern": best[0],
        "best_non_catalog_success_pct": best[1]["success_pct"],
    }
    SUMMARY_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"Wrote {RESULTS_PATH} ({len(results)} probes)")
    print(f"Wrote {SUMMARY_PATH}")
    for pid, st in pattern_stats.items():
        print(f"  {pid}: {st['success_pct']}% success ({st['counts']})")


if __name__ == "__main__":
    main()
