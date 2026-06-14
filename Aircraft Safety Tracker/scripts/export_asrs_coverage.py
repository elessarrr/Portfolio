#!/usr/bin/env python3
"""Export ASRS aircraft coverage summary for PRD 0010 ship gate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.ingestion.asrs_coverage import write_coverage_summary

DEFAULT_OUT = ROOT / "data/logs/asrs_coverage_summary.json"


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    app = create_app("development")
    with app.app_context():
        summary = write_coverage_summary(out)
    print(
        f"aircraft_with_data={summary['aircraft_with_data']} "
        f"ship_gate_pass={summary['ship_gate_pass']} -> {out}"
    )
    return 0 if summary["ship_gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
