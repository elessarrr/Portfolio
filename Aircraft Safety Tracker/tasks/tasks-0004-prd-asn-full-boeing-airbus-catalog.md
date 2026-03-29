## Relevant Files

- `Planning/0004-prd-asn-full-boeing-airbus-catalog.md` - PRD defining scope, goals, and requirements.
- `scripts/scrape_boeing.py` - ASN scraper entrypoint for Boeing type index; needs full catalog coverage.
- `scripts/scrape_airbus.py` - ASN scraper entrypoint for Airbus type index; needs full catalog coverage.
- `scripts/scraper_utils.py` - Shared ASN parsing utilities; likely needs hardening for full type index coverage.
- `scripts/import_data.py` - Imports ASN JSON into DB; needs variant upsert support and idempotency checks.
- `scripts/asn_sync.py` - Sync lock + sync state helpers for weekly ASN catalog refresh.
- `data/raw/boeing_incidents.json` - Current Boeing raw dataset; used as seed/source for ingestion.
- `data/raw/airbus_incidents.json` - Current Airbus raw dataset; used as seed/source for ingestion.
- `scripts/update_data.sh` - Existing “weekly update” runner; candidate to extend with catalog sync + reporting.
- `scripts/com.aircraftsafetytracker.weeklyupdate.plist` - Existing scheduled job definition; candidate to extend/align with weekly sync.
- `run.py` - Current startup hooks (AUTO_SEED, host/port); needs “if last ASN sync > 7 days, trigger background sync”.
- `app/routes.py` - Search endpoint + aircraft details; may need to surface variants in UI/search.
- `app/templates/components/search_results.html` - Search results UI; “Series / Models” column behavior.
- `app/templates/index.html` - Search input and quick filters; may need tweaks to show variants.
- `app/models.py` - Contains `AircraftVariant`; may need new sync state storage model (if stored in DB).
- `migrations/` - If we add a DB-backed sync state table, we’ll need a migration.
- `tests/test_routes.py` - Search behavior tests; should be extended for type+variant result expectations.
- `tests/test_models.py` - Model tests; should cover any new sync state model and variant upsert behavior.
- `tests/test_import_data_variants.py` - Tests variant derivation/upsert idempotency in importer.
- `tests/test_asn_sync.py` - Tests sync lock behavior and weekly trigger logic.

### Notes

- Use `PYTHONPATH=. pytest -v` to run the backend test suite.
- Reuse the existing ASN pipeline (`scrape_*` → `data/raw/*.json` → `import_data.py`) rather than introducing a parallel system.

## Tasks

- [x] 1.0 Expand ASN catalog discovery for full Boeing/Airbus coverage
  - [x] 1.1 Measure current coverage vs ASN type index counts (Boeing, Airbus). DB: Boeing=8, Airbus=32. ASN index: Boeing=81, Airbus=35.
  - [x] 1.2 Harden `get_model_links` parsing to capture all ASN type entries.
  - [x] 1.3 Add a catalog discovery output artifact (raw list of discovered types).
  - [x] 1.4 Add safe rate limiting, retries, and skip logging for type discovery.
  - [x] 1.5 Validate discovery results for Boeing and Airbus and record coverage. Raw/DB coverage: Boeing=8/81 (~9.9%), Airbus=32/35 (~91.4%).
- [x] 2.0 Enhance importer to upsert variants from ASN data
  - [x] 2.1 Confirm scraper JSON includes `variant_name` for ASN incidents. Current `data/raw/*_incidents.json` do not include `variant_name`, so importer must derive it (e.g., from `type`) or datasets must be regenerated.
  - [x] 2.2 Update `import_data.py` to upsert `AircraftVariant` records per aircraft.
  - [x] 2.3 Add idempotency protections for variants (no duplicates on reruns).
  - [x] 2.4 Backfill variants for existing imported incidents.
- [x] 3.0 Add ASN sync state, locking, and weekly auto-sync on startup
  - [x] 3.1 Choose sync state storage mechanism (DB table vs lockfile under `data/`). Selected: lockfile + JSON state under `data/` to avoid schema changes.
  - [x] 3.2 Implement an exclusive sync lock to prevent overlapping runs.
  - [x] 3.3 Implement “last successful ASN sync” timestamp recording.
  - [x] 3.4 Add startup check: if last sync > 7 days, trigger background sync.
  - [x] 3.5 Add manual CLI/script entrypoint for sync and a dry-run mode.
- [x] 4.0 Update UI and search to show series and variants reliably
  - [x] 4.1 Define how variants map into existing “Series / Models” search UI. Series = current `series_name` grouping; Models = aggregated `AircraftVariant.variant_name` across aircraft in that series.
  - [x] 4.2 Update search endpoint to include variants in results (without breaking series).
  - [x] 4.3 Update search results component to render models/variants per series.
  - [x] 4.4 Add clear empty states when a series has no variants.
- [x] 5.0 Add reconciliation reporting and automated test coverage
  - [x] 5.1 Add post-sync reconciliation report with discovered/imported counts and errors.
  - [x] 5.2 Add tests for variant upsert idempotency and correctness.
  - [x] 5.3 Add tests for search returning series + variants as expected.
  - [x] 5.4 Add tests for startup auto-sync trigger conditions and locking.
  - [x] 5.5 Add a regression test for “missing models” scenario using sample fixtures.
