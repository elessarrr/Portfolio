#!/usr/bin/env python3
"""Export distinct FAA AIDS make/model strings for mapping review (PRD 0007 FR-4)."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data/raw/faa_aids_boeing_airbus.jsonl"
DEFAULT_OUT = ROOT / "data/logs/faa_aids_make_model_catalog.jsonl"


def _faa_make_model(row: Dict[str, Any]) -> str:
    make = str(row.get("c23") or "").strip()
    model = str(row.get("c24") or "").strip()
    return (f"{make} {model}".strip() if model else make).strip()


def _manufacturer_guess(faa_make_model: str) -> str:
    u = faa_make_model.upper()
    if u.startswith("AIRBUS"):
        return "Airbus"
    if u.startswith("BOEING"):
        return "Boeing"
    return "unknown"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def build_catalog(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = defaultdict(int)
    samples: Dict[str, List[str]] = defaultdict(list)
    for row in rows:
        mm = _faa_make_model(row)
        if not mm:
            continue
        counts[mm] += 1
        c5 = str(row.get("c5") or "").strip()
        if c5 and len(samples[mm]) < 5:
            samples[mm].append(c5)
    catalog = []
    for mm, count in counts.items():
        catalog.append(
            {
                "faa_make_model": mm,
                "incident_count": count,
                "char_length": len(mm),
                "manufacturer_guess": _manufacturer_guess(mm),
                "sample_c5_ids": samples[mm],
            }
        )
    catalog.sort(key=lambda r: (-r["incident_count"], r["faa_make_model"]))
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input_path", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    rows = load_jsonl(args.input_path)
    catalog = build_catalog(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        f.write(f"# FAA AIDS make_model catalog — {len(catalog)} distinct strings\n")
        for entry in catalog:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "input": str(args.input_path),
                "output": str(args.out),
                "distinct_strings": len(catalog),
                "total_rows": len(rows),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
