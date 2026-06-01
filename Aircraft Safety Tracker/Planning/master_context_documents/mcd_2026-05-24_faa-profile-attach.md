# Master Context Document — FAA Profile Attach (PRD 0003)

**Date:** 2026-05-24  
**Branch:** `v2-(first-round-of-feedback-from-RJ)`

## Summary

Orphan FAA Boeing/Airbus incidents (ASIAS URLs, `aircraft_id IS NULL`) are attached to aircraft profiles via `FAAAIDSImporter.resolve_aircraft()`. Optional exact date+registration merge reparents FAA sources onto no-link profile incidents when exactly one FAA match exists.

## New module

`app/ingestion/linking/faa_profile_attach.py`

- `is_boeing_airbus_faa()` — scope filter (c23 BOEING/AIRBUS, active, ASIAS URL)
- `attach_aircraft_ids()` — sets `incident.aircraft_id` in batches
- `exact_merge_faa_to_profile()` — exact key only; skips 0 or >1 matches
- `run_faa_profile_attach()` — orchestrates attach then merge; writes JSON summary

## CLI

```bash
flask import-data attach-faa-boeing-airbus [--dry-run] [--attach-only] [--merge-only] [--limit N] [--batch-size N]
```

## Data flow

```
FAA_AIDS orphan incidents (aircraft_id NULL, Boeing/Airbus)
  → resolve_aircraft(make_model from c23/c24)
  → UPDATE incident.aircraft_id
  → profile pages show incidents via existing incident_list.html + resolve_source_href
```

## Constraints

- No fuzzy merge (`find_best_incident_match` not used)
- GA FAA rows out of scope
- Reuses `incident_linker._reparent_sources` for exact merge only

## Live run stats

- Attached: 5,877 / 6,848 scanned
- Merge linked: 0
- Boeing profile link rate: 54.7% → 81.9%
