import json
import logging
import os
import re
import sys
import time

from dateutil import parser

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.ingestion.importers.base import strip_duplicate_words
from app.models import Aircraft, AircraftVariant, Incident

app = create_app()


def parse_date(date_str):
    try:
        # Try fuzzy parsing which handles most formats
        # "11 May 1933" -> 1933-05-11
        # "May 1933" -> 1933-05-?? (default day=1?)
        # "1933" -> 1933-??-?? (default month=1, day=1?)

        # Clean date string
        clean_date = date_str.strip()

        # Handle "?? ??? 1933" or similar ASN oddities
        if "??" in clean_date:
            clean_date = clean_date.replace("??", "01")

        # Handle "xx May 1938" -> Replace xx with 01
        if "xx" in clean_date.lower():
            clean_date = clean_date.lower().replace("xx", "01")

        # Handle "unk. date 1943" -> Extract year
        if "unk. date" in clean_date.lower():
            # Try to find a 4-digit year
            import re

            match = re.search(r"\d{4}", clean_date)
            if match:
                clean_date = f"01 Jan {match.group(0)}"
            else:
                return None

        return parser.parse(clean_date).date()
    except Exception as e:
        logger.error(f"Error parsing date '{date_str}': {e}")
        return None


def parse_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).strip()
        if text == "":
            return default
        return int(float(text))
    except Exception:
        return default


def derive_variant_name(model_name, aircraft_type):
    normalized_type = (aircraft_type or "").replace("\xa0", " ").strip()
    if not normalized_type:
        return None

    normalized_model = (model_name or "").strip()
    if normalized_model and normalized_type.lower().startswith(normalized_model.lower()):
        suffix = normalized_type[len(normalized_model) :].strip()
        if suffix:
            derived = f"{normalized_model} {suffix}".strip()
            return re.sub(r"\s+", " ", derived)
        return normalized_model

    return re.sub(r"\s+", " ", normalized_type)


def import_file(filepath, manufacturer):
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return

    logger.info(f"Importing {filepath}...")
    with open(filepath, "r") as f:
        data = json.load(f)

    with app.app_context():
        count = 0
        variant_stats = {}
        for item in data:
            model_name = item.get("model_name")
            if not model_name:
                continue

            model_name = strip_duplicate_words(model_name).strip()
            manufacturer = strip_duplicate_words(manufacturer).strip()

            # Find or create Aircraft
            aircraft = Aircraft.query.filter_by(model_name=model_name).first()
            if not aircraft:
                aircraft = Aircraft(
                    manufacturer=manufacturer,
                    model_name=model_name,
                    total_incidents=0,
                    fatal_incidents=0,
                    total_fatalities=0,
                )
                db.session.add(aircraft)
                db.session.commit()  # Commit to get ID

            # Create Incident
            date_obj = parse_date(item.get("date"))

            if date_obj and date_obj.year < 1985:
                logger.debug(f"Skipping old incident from {date_obj.year}")
                continue

            fatalities = parse_int(item.get("fatalities", 0), default=0)

            variant_name = item.get("variant_name") or derive_variant_name(
                model_name, item.get("type")
            )
            if variant_name:
                variant_name = strip_duplicate_words(variant_name).strip()

            # Check if incident already exists (avoid dupes on re-run)
            existing = Incident.query.filter_by(asn_url=item.get("asn_url")).first()

            if existing:
                # Update existing record
                existing.date = date_obj
                existing.fatalities = fatalities
                existing.description = item.get("narrative")
                existing.location = item.get("location")
                existing.incident_type = item.get("category")
                existing.operator = item.get("operator")
                if variant_name:
                    existing.variant_name = variant_name
            else:
                incident = Incident(
                    aircraft_id=aircraft.id,
                    date=date_obj,
                    operator=item.get("operator"),
                    location=item.get("location"),
                    fatalities=fatalities,
                    description=item.get("narrative"),
                    asn_url=item.get("asn_url"),
                    incident_type=item.get("category"),
                    variant_name=variant_name,
                )
                db.session.add(incident)

            if variant_name:
                key = (aircraft.id, variant_name)
                if key not in variant_stats:
                    variant_stats[key] = {"total": 0, "fatal": 0}
                variant_stats[key]["total"] += 1
                if fatalities and fatalities > 0:
                    variant_stats[key]["fatal"] += 1

            # Commit changes to ensure incident data is up to date before stats calculation
            db.session.commit()

            # Recalculate stats for this aircraft
            # This is safer than incremental updates
            stats = (
                db.session.query(
                    db.func.count(Incident.id),
                    db.func.sum(Incident.fatalities),
                    db.func.sum(db.case((Incident.fatalities > 0, 1), else_=0)),
                )
                .filter_by(aircraft_id=aircraft.id)
                .first()
            )

            aircraft.total_incidents = stats[0] or 0
            aircraft.total_fatalities = stats[1] or 0
            aircraft.fatal_incidents = stats[2] or 0

            count += 1

        for (aircraft_id, variant_name), stats in variant_stats.items():
            variant = AircraftVariant.query.filter_by(
                aircraft_id=aircraft_id, variant_name=variant_name
            ).first()
            if not variant:
                variant = AircraftVariant(aircraft_id=aircraft_id, variant_name=variant_name)
                db.session.add(variant)
            variant.total_incidents = stats["total"]
            variant.fatal_incidents = stats["fatal"]

        db.session.commit()
        logger.info(f"Imported {count} new incidents for {manufacturer}.")

        return {
            "manufacturer": manufacturer,
            "incidents_processed": count,
            "variants_upserted": len({variant_name for (_, variant_name) in variant_stats.keys()}),
        }


def main():
    boeing_result = import_file("data/raw/boeing_incidents.json", "Boeing")
    airbus_result = import_file("data/raw/airbus_incidents.json", "Airbus")

    try:
        import asn_sync

        state = asn_sync.read_sync_state()
        state.update(
            {
                "last_successful_asn_sync_at": int(time.time()),
                "last_successful_asn_sync_source": "import_data.py",
                "last_successful_asn_sync_summary": {
                    "Boeing": boeing_result,
                    "Airbus": airbus_result,
                },
            }
        )
        asn_sync.write_sync_state(state)

        try:
            report = asn_sync.build_reconciliation_report()
            asn_sync.write_reconciliation_report(report)
        except Exception:
            pass
    except Exception:
        pass


if __name__ == "__main__":
    main()
