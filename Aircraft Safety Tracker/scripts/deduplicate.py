import json
import logging
import os
from copy import deepcopy
from dateutil import parser


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INPUT_FILES = {
    "ASN": [
        "data/raw/boeing_incidents.json",
        "data/raw/airbus_incidents.json"
    ],
    "FAA": ["data/raw/faa_incidents.json"],
    "NTSB": ["data/raw/ntsb_incidents.json"]
}
UNIFIED_OUTPUT = "data/processed/unified_incidents.json"
DISCREPANCY_OUTPUT = "data/processed/discrepancies.json"


def parse_date(value):
    if not value:
        return None
    try:
        return parser.parse(str(value), fuzzy=True).date()
    except Exception:
        return None


def normalize_text(value):
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def load_source_records():
    records = []
    for source_name, paths in INPUT_FILES.items():
        for path in paths:
            if not os.path.exists(path):
                logger.warning(f"Input file missing, skipping: {path}")
                continue
            with open(path, "r") as file:
                source_records = json.load(file)
            for record in source_records:
                normalized = normalize_record(record, source_name)
                records.append(normalized)
            logger.info(f"Loaded {len(source_records)} records from {path}")
    logger.info(f"Loaded {len(records)} total source records")
    return records


def normalize_record(record, source_name):
    event_date = parse_date(record.get("date") or record.get("event_date"))
    model = record.get("variant_name") or record.get("make_model") or record.get("model_name") or record.get("type")
    location = record.get("location")
    registration = record.get("registration")
    fatalities = record.get("fatalities")
    source_url = record.get("source_url") or record.get("asn_url")
    normalized = {
        "source_name": source_name,
        "event_date": event_date.isoformat() if event_date else None,
        "event_date_obj": event_date,
        "model": model,
        "model_norm": normalize_text(model),
        "location": location,
        "location_norm": normalize_text(location),
        "registration": registration,
        "registration_norm": normalize_text(registration),
        "fatalities": int(fatalities) if isinstance(fatalities, int) or str(fatalities).isdigit() else None,
        "source_url": source_url,
        "raw": deepcopy(record)
    }
    return normalized


def group_exact_matches(records):
    groups = []
    used = set()
    lookup = {}
    for index, record in enumerate(records):
        key = (record["event_date"], record["registration_norm"])
        if not key[0] or not key[1]:
            continue
        lookup.setdefault(key, []).append(index)

    for indexes in lookup.values():
        if len(indexes) > 1:
            group = [records[index] for index in indexes]
            groups.append(group)
            used.update(indexes)
    return groups, used


def is_fuzzy_match(record_a, record_b):
    date_a = record_a["event_date_obj"]
    date_b = record_b["event_date_obj"]
    if not date_a or not date_b:
        return False
    day_delta = abs((date_a - date_b).days)
    if day_delta > 1:
        return False
    if not record_a["model_norm"] or not record_b["model_norm"]:
        return False
    model_match = record_a["model_norm"] in record_b["model_norm"] or record_b["model_norm"] in record_a["model_norm"]
    if not model_match:
        return False
    if not record_a["location_norm"] or not record_b["location_norm"]:
        return False
    location_match = (
        record_a["location_norm"] in record_b["location_norm"] or
        record_b["location_norm"] in record_a["location_norm"]
    )
    return location_match


def group_fuzzy_matches(records, used_indexes):
    groups = []
    for index, record in enumerate(records):
        if index in used_indexes:
            continue
        matched_group = None
        for group in groups:
            if any(is_fuzzy_match(record, member) for member in group):
                matched_group = group
                break
        if matched_group is not None:
            matched_group.append(record)
        else:
            groups.append([record])
    return groups


def merge_group(group):
    fatalities = [item["fatalities"] for item in group if item["fatalities"] is not None]
    unique_fatalities = sorted(set(fatalities))
    discrepancies = []
    if len(unique_fatalities) > 1:
        discrepancies.append({
            "field": "fatalities",
            "values": unique_fatalities,
            "message": "Fatality counts differ across sources"
        })

    merged = {
        "event_date": next((item["event_date"] for item in group if item["event_date"]), None),
        "model": next((item["model"] for item in group if item["model"]), None),
        "location": next((item["location"] for item in group if item["location"]), None),
        "registration": next((item["registration"] for item in group if item["registration"]), None),
        "fatalities": unique_fatalities[-1] if unique_fatalities else None,
        "source_count": len(group),
        "sources": [
            {
                "source_name": item["source_name"],
                "source_url": item["source_url"],
                "fatalities": item["fatalities"]
            }
            for item in group
        ],
        "discrepancies": discrepancies
    }
    return merged


def build_unified_view(records):
    exact_groups, used_indexes = group_exact_matches(records)
    fuzzy_groups = group_fuzzy_matches(records, used_indexes)
    all_groups = exact_groups + fuzzy_groups
    unified = [merge_group(group) for group in all_groups]
    discrepancies = [record for record in unified if record["discrepancies"]]
    return unified, discrepancies


def save_outputs(unified_records, discrepancies):
    os.makedirs(os.path.dirname(UNIFIED_OUTPUT), exist_ok=True)
    with open(UNIFIED_OUTPUT, "w") as unified_file:
        json.dump(unified_records, unified_file, indent=2)
    with open(DISCREPANCY_OUTPUT, "w") as discrepancy_file:
        json.dump(discrepancies, discrepancy_file, indent=2)
    logger.info(f"Wrote {len(unified_records)} unified incidents to {UNIFIED_OUTPUT}")
    logger.info(f"Wrote {len(discrepancies)} discrepancy records to {DISCREPANCY_OUTPUT}")


def main():
    records = load_source_records()
    unified_records, discrepancies = build_unified_view(records)
    save_outputs(unified_records, discrepancies)


if __name__ == "__main__":
    main()
