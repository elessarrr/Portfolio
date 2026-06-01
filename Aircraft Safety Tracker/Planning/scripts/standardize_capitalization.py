import argparse
import os
import re
import sys
from typing import Dict

from sqlalchemy import func

# Comments for context:
# This one-time maintenance script standardizes historical capitalization
# so the UI shows a consistent format (Title Case). It is safe to run in dry-run
# mode first and only writes to DB when --apply is provided.

# Make project imports work when run from Planning/scripts.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from app import create_app, db
from app.models import Aircraft, AircraftVariant, Incident


def _title_case(value: str) -> str:
    normalized = re.sub(r"\s+", " ", (value or "").strip())
    return normalized.title()


def standardize_capitalization(*, dry_run: bool = True, batch_size: int = 500) -> Dict[str, int]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    summary = {
        "aircraft_manufacturer_updated": 0,
        "aircraft_model_updated": 0,
        "aircraft_model_conflicts": 0,
        "variant_name_updated": 0,
        "variant_name_conflicts": 0,
        "incident_raw_model_variant_updated": 0,
    }

    pending = 0

    for aircraft in Aircraft.query.order_by(Aircraft.id.asc()).yield_per(batch_size):
        if aircraft.manufacturer:
            target_manufacturer = _title_case(aircraft.manufacturer)
            if target_manufacturer != aircraft.manufacturer:
                aircraft.manufacturer = target_manufacturer
                summary["aircraft_manufacturer_updated"] += 1
                pending += 1

        if aircraft.model_name:
            target_model = _title_case(aircraft.model_name)
            if target_model != aircraft.model_name:
                conflict = Aircraft.query.filter(
                    Aircraft.id != aircraft.id,
                    func.upper(Aircraft.model_name) == target_model.upper(),
                ).first()
                if conflict:
                    summary["aircraft_model_conflicts"] += 1
                else:
                    aircraft.model_name = target_model
                    summary["aircraft_model_updated"] += 1
                    pending += 1

        if not dry_run and pending >= batch_size:
            db.session.commit()
            pending = 0

    for variant in AircraftVariant.query.order_by(AircraftVariant.id.asc()).yield_per(batch_size):
        if not variant.variant_name:
            continue

        target_variant = _title_case(variant.variant_name)
        if target_variant == variant.variant_name:
            continue

        conflict = AircraftVariant.query.filter(
            AircraftVariant.id != variant.id,
            AircraftVariant.aircraft_id == variant.aircraft_id,
            func.upper(AircraftVariant.variant_name) == target_variant.upper(),
        ).first()
        if conflict:
            summary["variant_name_conflicts"] += 1
            continue

        variant.variant_name = target_variant
        summary["variant_name_updated"] += 1
        pending += 1

        if not dry_run and pending >= batch_size:
            db.session.commit()
            pending = 0

    for incident in Incident.query.order_by(Incident.id.asc()).yield_per(batch_size):
        if not incident.raw_model_variant:
            continue

        target_raw_model = _title_case(incident.raw_model_variant)
        if target_raw_model == incident.raw_model_variant:
            continue

        incident.raw_model_variant = target_raw_model
        summary["incident_raw_model_variant_updated"] += 1
        pending += 1

        if not dry_run and pending >= batch_size:
            db.session.commit()
            pending = 0

    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()

    return summary


def _print_summary(summary: Dict[str, int], dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"=== standardize_capitalization ({mode}) ===")
    for key, value in summary.items():
        print(f"{key}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Standardize capitalization in Aircraft Safety Tracker tables.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes. By default, runs in dry-run mode.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Commit checkpoint size for apply mode.",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        summary = standardize_capitalization(
            dry_run=not args.apply,
            batch_size=args.batch_size,
        )
        _print_summary(summary, dry_run=not args.apply)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
