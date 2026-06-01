"""Tests for NTSB pilot row selection (FR-20.1)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ntsb_pilot_import.py"


def _load_pilot_module():
    spec = importlib.util.spec_from_file_location("ntsb_pilot_import", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_select_pilot_rows_25_known_5_mapped():
    pilot = _load_pilot_module()
    normalized = []
    for i in range(25):
        normalized.append(
            {
                "source_record_id": f"KNOWN{i:02d}",
                "unknown_aircraft": False,
                "dedupe_repasse_status": "import",
                "make_model": "Boeing 737-300",
                "mapped_model_name": "Boeing 737-300",
            }
        )
    pages = ["Boeing 757-200", "Airbus A320", "Boeing 767-300", "Boeing 777-200", "Boeing-Stearman Kaydet"]
    for i, page in enumerate(pages):
        normalized.append(
            {
                "source_record_id": f"MAP{i}",
                "unknown_aircraft": True,
                "dedupe_repasse_status": "import",
                "make_model": f"STRING {i}",
                "mapped_model_name": page,
            }
        )

    selected = pilot.select_pilot_rows(normalized)
    assert len(selected) == 30
    assert sum(1 for r in selected if r["pilot_cohort"] == "known_aircraft") == 25
    assert sum(1 for r in selected if r["pilot_cohort"] == "mapped_string") == 5
