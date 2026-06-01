## Bug Report

### What I expected to happen
The Aircraft Safety Tracker application should display incidents from all ingested data sources (ASN, NTSB, FAA_AIDS, FAA_SDR) for a given aircraft model. When viewing an aircraft's detail page or incident list, all relevant historical incidents from these sources should be visible and contribute to the total incident counts.

### What actually happens
Only incidents primarily sourced from ASN are prominently displayed and linked to `aircraft_id`s, making other data sources (NTSB, FAA_AIDS, FAA_SDR) largely invisible in the UI. For example, an aircraft might show 0 incidents on its detail page, even if the database contains many incidents for that model from NTSB or FAA_AIDS. This gives the impression that only ASN data exists in the application.

### Steps to reproduce
1. Navigate to an aircraft detail page (e.g., a generic "BOEING 737" or "AIRBUS A320" if available, or any aircraft that should have NTSB/FAA incidents).
2. Observe the "Total Incidents" count and the incident list.
3. Note that the displayed incidents are predominantly from ASN, and the total count is significantly lower than the actual number of NTSB/FAA_AIDS incidents in the database for that model.
4. (If possible) Compare with the raw database counts for `incident` records where `aircraft_id IS NULL` but `source_id` points to NTSB or FAA_AIDS.

### Error messages / stack traces
No explicit error messages or stack traces are observed in the UI. The issue is a silent data visibility problem.

### What I've already tried
- Gemini claims to have run a backfill script (`backfill_aircraft_ids.py`) to link orphaned incidents, which reportedly linked ~3.7k NTSB/FAA incidents. However, this script is now deleted from the repository, and a large backlog of unlinked incidents (236k+) still exists.

### Suspected area of code
- `importer.resolve_aircraft()` in `base.py`: This function is responsible for mapping incident records to an `Aircraft` model. It appears to have limitations in matching NTSB/FAA generic make/model strings to existing `Aircraft` records, leading to `aircraft_id = None` for many incidents.
- `Incident` model: The `aircraft_id` column is `NULL` for a vast majority of non-ASN incidents.
- `app/routes.py`: The `aircraft_details` and incident listing routes filter incidents by `aircraft_id`, effectively hiding unlinked incidents.
- Ingestion pipelines for FAA_AIDS and FAA_SDR: The FAA_SDR pipeline appears to contribute zero processed records in the current environment, indicating a potential issue with its ingestion or linking process.
- `scripts/backfill_aircraft_ids.py`: The absence of a repeatable backfill script means the issue persists for newly ingested or previously unlinked data.