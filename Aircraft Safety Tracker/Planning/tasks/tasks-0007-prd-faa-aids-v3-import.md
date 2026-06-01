# Task List: PRD 0007 — FAA AIDS Enrichment (v3)

**PRD Reference:** `Planning/tasks/0007-prd-faa-aids-v3-import.md`  
**Branch:** `v3-boeing-airbus-links`  
**Depends on:** PRD 0006.3 complete — 603 NTSB sources, 77 tests green  

---

## Relevant Files

### New files to create
- `app/ingestion/url_builders/faa_aids.py` — `build_faa_aids_url(source_record_id)` (FR-3)
- `app/ingestion/faa_aids_mapping.py` — `FaaAidsMakeModelMapping`, `bootstrap_create_approved_pages` (FR-5)
- `app/ingestion/importers/faa_aids_importer.py` — `FAAAIDSImporter` class (FR-7)
- `scripts/export_faa_aids_boeing_airbus.py` — download ZIP, parse CSV, write Boeing/Airbus JSONL (FR-2)
- `scripts/export_faa_aids_make_model_catalog.py` — distinct make_model catalog for product review (FR-4)
- `scripts/faa_aids_dedupe_pass.py` — ASN dedupe scoring pass (FR-6)
- `scripts/bootstrap_faa_aids_create_approved_pages.py` — idempotent Aircraft page creation (FR-8)
- `scripts/faa_aids_pilot_import.py` — 30-row canary against cloned DB (FR-9)
- `scripts/faa_aids_bulk_import.py` — full import with mapping gate + stats recalc (FR-10)
- `scripts/audit_post_faa_aids_import.py` — post-import duplicate + URL audit (FR-11)
- `data/config/faa_aids_make_model_to_aircraft.jsonl` — approved mapping file (FR-5; product-authored)
- `tests/test_faa_aids_url_builder.py` — URL builder unit tests (FR-12.2)
- `tests/test_faa_aids_mapping.py` — mapping load + resolve unit tests (FR-12.3)
- `tests/test_faa_aids_importer.py` — importer unit tests (FR-12.1)

### Existing files to modify
- `app/link_picker.py` — add FAA_AIDS branch to `display_make_model()` (FR-13.3)

### Existing files to read / reference (do not modify)
- `app/ingestion/importers/ntsb_importer.py` — template for `FAAAIDSImporter`
- `app/ingestion/ntsb_mapping.py` — template for `faa_aids_mapping.py`
- `app/ingestion/url_builders/ntsb.py` — reference URL builder pattern
- `app/ingestion/dedupe/ntsb_asn.py` — reference dedupe scoring logic
- `app/ingestion/link_schema.py` — `assert_valid_source_url`, `is_catalog_url` (no changes)
- `app/ingestion/importers/base.py` — `is_boeing_or_airbus_make_model`, `find_boeing_airbus_aircraft_id`
- `scripts/ntsb_bulk_import.py` — reference for `recalc_aircraft_stats` and bulk import pattern
- `scripts/ntsb_pilot_import.py` — reference for pilot import pattern
- `scripts/audit_post_ntsb_import.py` — reference for post-import audit pattern

### Notes
- Run all tests with: `PYTHONPATH=. pytest -q` from the `Aircraft Safety Tracker/` directory (not `Portfolio/`)
- Use `python` (conda/venv) not bare `python3` — the conda env has Flask installed
- Stop the Flask dev server before any bulk DB write (single SQLite writer rule)
- Backup DB before pilot and bulk runs; `.gitignore` already covers `data/aircraft_safety_v3.db.*`
- Skip `#` comment lines in all JSONL-reading loops (`if line.startswith("#"): continue`)
- All new Python files need `from __future__ import annotations` as first line (Python 3.8 compatibility)

---

## Tasks

- [ ] 1.0 Data Acquisition — download FAA AIDS ZIP and export Boeing/Airbus JSONL
  - [ ] 1.1 Write `scripts/export_faa_aids_boeing_airbus.py`: download the latest FAA AIDS ZIP from `https://www.faa.gov/data_research/accident_incident/`, extract the CSV, and filter rows where `c23` (make) starts with `BOEING` or `AIRBUS` (case-insensitive) using `is_boeing_or_airbus_make_model()` from `app/ingestion/importers/base.py`.
  - [ ] 1.2 Add `_looks_like_csv(text)` guard in the script: if the downloaded content starts with `<html` or `<!DOCTYPE`, raise an error with message `"FAA returned HTML instead of CSV — check URL or try again"`. This prevents silently processing a FAA error page (LEARNINGS §16).
  - [ ] 1.3 Handle CSV encoding: try `utf-8` first, fall back to `latin-1` with `errors='replace'` for older records. Log which encoding was used.
  - [ ] 1.4 Write each Boeing/Airbus row as one JSON object per line to `data/raw/faa_aids_boeing_airbus.jsonl`, preserving all raw field names (`c5`, `c9`, `c23`, `c24`, `c26`, `c28`, `c29`, `c34`, `c44`, `c203`, etc.). Write a `#` header comment line first (e.g. `# FAA AIDS Boeing/Airbus export — {date} — {count} rows`).
  - [ ] 1.5 Print a summary to stdout: total CSV rows read, Boeing/Airbus rows written, rows skipped (no `c5`, no date). Confirm `data/raw/faa_aids_boeing_airbus.jsonl` exists and has > 0 rows before proceeding.

- [ ] 2.0 Make/Model Catalog & Mapping — catalog distinct FAA strings, build mapping file and module
  - [ ] 2.1 Write `scripts/export_faa_aids_make_model_catalog.py`: read `data/raw/faa_aids_boeing_airbus.jsonl` (skip `#` lines), compute distinct `(c23.strip() + " " + c24.strip()).strip()` strings, and write `data/logs/faa_aids_make_model_catalog.jsonl`. Each row: `{"faa_make_model": "...", "incident_count": N, "char_length": N, "manufacturer_guess": "Boeing"|"Airbus"|"unknown", "sample_c5_ids": ["...", ...]}`. Sort descending by `incident_count`.
  - [ ] 2.2 Run the catalog export script and review `data/logs/faa_aids_make_model_catalog.jsonl`. For each distinct `faa_make_model` string, assign a `canonical_model_name` and `action` (`map_to_existing` | `create_approved` | `skip`). **This is a product/CTO review step — no code changes.**
  - [ ] 2.3 Write the approved `data/config/faa_aids_make_model_to_aircraft.jsonl` mapping file following the schema:
    ```jsonl
    {"faa_make_model": "BOEING 7373H4", "canonical_model_name": "Boeing 737-300", "action": "map_to_existing"}
    {"faa_make_model": "AIRBUS A320-211", "canonical_model_name": "Airbus A320", "action": "map_to_existing"}
    {"faa_make_model": "BOEING AG-1", "canonical_model_name": "Boeing AG-1", "action": "skip"}
    ```
    `create_approved` entries must also include `"manufacturer": "Boeing"` or `"manufacturer": "Airbus"`. **Gate: do not proceed to task 3 until this file is approved by product.**
  - [ ] 2.4 Write `app/ingestion/faa_aids_mapping.py` modelled exactly on `app/ingestion/ntsb_mapping.py`:
    - `FaaAidsMappingEntry` dataclass: `faa_make_model`, `canonical_model_name`, `action`, `canonical_aircraft_id` (optional), `manufacturer` (optional), `notes` (optional).
    - `FaaAidsMakeModelMapping` class with `.load(path)`, `.get(faa_make_model)`, `.resolve_aircraft_id(faa_make_model)`.
    - `load_faa_aids_make_model_mapping(path)` function.
    - `iter_create_approved_targets(mapping)` function.
    - `bootstrap_create_approved_pages(mapping, *, dry_run=False)` function — reuse `_validate_boeing_airbus_page_name` logic (canonical name must contain `Boeing` or `Airbus`).
    - Valid actions: `map_to_existing`, `create_approved`, `skip`. Raise `ValueError` on unknown action.
    - Raise `ValueError` on empty JSONL (no entries after skipping `#` lines).
  - [ ] 2.5 Write `tests/test_faa_aids_mapping.py`:
    - Load valid JSONL with `map_to_existing` → resolves to correct `aircraft_id`
    - `action=skip` → `None` from `resolve_aircraft_id`
    - `create_approved` → `bootstrap_create_approved_pages` creates an `Aircraft` row; second call is idempotent
    - Empty JSONL → `ValueError`
    - Missing required field → `ValueError`
    - `canonical_model_name` without `Boeing`/`Airbus` on `create_approved` → `ValueError`
  - [ ] 2.6 Run `PYTHONPATH=. pytest tests/test_faa_aids_mapping.py -q` — all tests must pass.

- [ ] 3.0 URL Builder + Importer Core — `faa_aids.py`, `FAAAIDSImporter`, full unit tests
  - [ ] 3.1 Write `app/ingestion/url_builders/faa_aids.py`:
    - `build_faa_aids_url(source_record_id: Optional[str]) -> Optional[str]`: returns `None` when `source_record_id` is None or empty; otherwise returns `https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:{urllib.parse.quote(source_record_id, safe="")}`.
    - No catalog fallback — never return the FAA AIDS landing page as `source_url`.
  - [ ] 3.2 Write `tests/test_faa_aids_url_builder.py`:
    - `build_faa_aids_url("20050316X00394")` → URL contains `P12_AIDS_RPRT_NBR:20050316X00394`
    - `build_faa_aids_url(None)` → `None`
    - `build_faa_aids_url("")` → `None`
    - Result passes `assert_valid_source_url()` from `link_schema.py`
    - Result does **not** pass `is_catalog_url()` (i.e. is correctly identified as a per-record URL)
  - [ ] 3.3 Write `app/ingestion/importers/faa_aids_importer.py` modelled on `ntsb_importer.py`:
    - Class `FAAAIDSImporter`, `source_name = "FAA_AIDS"`.
    - Constructor `__init__(self, records=None, *, mapping=None)` — accepts `FaaAidsMakeModelMapping`, `str`, or `Path`; loads mapping if path given.
    - `run(self) -> int` — iterates records, calls `upsert`, commits, returns written count.
    - `parse(raw_record) -> Optional[dict]` (static method):
      - Returns `None` if `c5` missing/empty, `c9` date unparseable, or make/model not Boeing/Airbus.
      - Parses `c9` date from `MM/DD/YYYY` format.
      - Builds `faa_make_model` from `c23.strip() + " " + c24.strip()`.
      - Sets `source_url = build_faa_aids_url(c5)` — never `None` for a valid row.
      - Builds `location` from `c28` (city) + `c29` (state): `"city, state"`.strip(", ").
      - Coerces `c34` (fatalities) null/empty → `0` via `fatalities_like_import()` pattern (LEARNINGS §38).
      - Stores full raw row in `source_data`; adds key `faa_aids_make_model` = verbatim `faa_make_model` string.
    - `upsert(self, raw_record) -> bool`:
      - Calls `parse()`; returns `False` if `None`.
      - Calls `assert_source_data_metadata_only(source_data)` and `assert_valid_source_url(source_url)`.
      - Checks for existing `IncidentSource(source_name="FAA_AIDS", source_record_id=c5)` — update if exists (idempotent); insert new `Incident` + `IncidentSource` if not.
      - Uses `_resolve_aircraft_id(faa_make_model)` for `aircraft_id`.
    - `_resolve_aircraft_id(self, faa_make_model) -> Optional[int]`: uses mapping when provided (fail-closed, accumulates `skipped_unmapped`/`skipped_unresolved` lists); falls back to `resolve_boeing_airbus_aircraft_id()` only when no mapping.
  - [ ] 3.4 Write `tests/test_faa_aids_importer.py`:
    - `parse()` returns correct all-fields dict for a valid Boeing row
    - `parse()` returns `None` for a non-Boeing/Airbus `c23`
    - `parse()` returns `None` when `c5` is empty
    - `parse()` returns `None` when `c9` date is invalid
    - `parse()` sets `source_url` to a valid ASIAS URL for any valid row
    - `parse()` coerces null/empty `c34` → `fatalities=0`
    - `upsert()` with mapping: mapped string → inserts `Incident` + `IncidentSource`
    - `upsert()` with mapping: unmapped string → returns `False`; appended to `skipped_unmapped`
    - `upsert()` idempotent: running same row twice → 1 `IncidentSource`, no duplicate `Incident`
    - `upsert()` calls `assert_valid_source_url` — rejects any row where `source_url` would be catalog URL
    - `source_data` contains `faa_aids_make_model` key
    - `source_data` does not contain `links` key (`assert_source_data_metadata_only` passes)
  - [ ] 3.5 Run `PYTHONPATH=. pytest tests/test_faa_aids_url_builder.py tests/test_faa_aids_importer.py tests/test_faa_aids_mapping.py -q` — all must pass. Then run full suite `PYTHONPATH=. pytest -q` and confirm all 77 existing tests still green.

- [ ] 4.0 Pre-Import Pipeline — dedupe pass, bootstrap, pilot import, product sign-off
  - [ ] 4.1 Write `scripts/faa_aids_dedupe_pass.py`:
    - Reads `data/raw/faa_aids_boeing_airbus.jsonl` (skip `#` lines).
    - For each row, resolves `aircraft_id` via `find_boeing_airbus_aircraft_id()` (lookup-only, no writes) using the mapping file.
    - Queries ASN `Incident` rows for that `aircraft_id` within ±2 days of the FAA date.
    - Scores each candidate: `date_close` (within 1 day = strong), `fatalities_close` (delta ≤ 1 after null→0 coercion = strong), `location_fuzzy` (weak), `operator_fuzzy` (weak).
    - Marks `dedupe_status`: `asn_covered` if ≥ 2 strong signals; `import` otherwise. Rows with no resolvable `aircraft_id` are marked `unmapped` (skipped at bulk import).
    - Writes `data/logs/faa_aids_dedupe_audit.jsonl` with fields: `c5`, `faa_make_model`, `dedupe_status`, `closest_asn_incident_id`, `score_detail`.
    - Prints summary: total rows, `asn_covered` count, `import` count, `unmapped` count.
  - [ ] 4.2 Review `data/logs/faa_aids_dedupe_audit.jsonl` counts. Confirm the `import` count is sensible (not 0, not suspiciously close to total). If `asn_covered` rate seems too high (> 30%), spot-check a few rows manually before proceeding.
  - [ ] 4.3 Write `scripts/bootstrap_faa_aids_create_approved_pages.py`:
    - Accepts `--mapping` path and optional `--dry-run` flag.
    - Calls `bootstrap_create_approved_pages(mapping, dry_run=...)` from `faa_aids_mapping.py`.
    - Prints: how many `create_approved` targets found, how many created, how many already existed.
    - Dry-run run first: `DATABASE_URL=... python scripts/bootstrap_faa_aids_create_approved_pages.py --dry-run`. Review output. Then run without `--dry-run`.
  - [ ] 4.4 Write `scripts/faa_aids_pilot_import.py` modelled on `scripts/ntsb_pilot_import.py`:
    - Accepts `--db` (real v3 DB path), `--pilot-db` (clone target), `--dedupe-audit` (JSONL), `--mapping`, `--limit` (default 30), `--report-out`.
    - Clones the real v3 DB: `shutil.copy(db_path, pilot_db_path)`.
    - Selects first `--limit` rows with `dedupe_status=import` from the dedupe audit JSONL.
    - Runs `FAAAIDSImporter(records=..., mapping=...)` against the pilot DB clone.
    - Verifies each imported row: `source_url` non-null, `aircraft_id` matches expected page, no duplicate `Incident` on same date+aircraft.
    - Writes `data/logs/faa_aids_pilot_import_report.json` with: rows_attempted, rows_imported, verification_issues (list), sample_source_urls (5 rows).
  - [ ] 4.5 Run the pilot import: `DATABASE_URL="sqlite:////…/data/aircraft_safety_v3.db" python scripts/faa_aids_pilot_import.py`. Review `data/logs/faa_aids_pilot_import_report.json`. Spot-check 5 ASIAS URLs from `sample_source_urls` via `curl -I` or browser to confirm HTTP 200 with event-specific content.
  - [ ] 4.6 **Product sign-off gate**: CTO reviews pilot report. Confirm: correct aircraft pages, valid ASIAS URLs, no duplicate incidents, Make/Model strings look sensible. Do not proceed to task 5 without approval.

- [ ] 5.0 Bulk Import + Post-Import Audit + UI verification
  - [ ] 5.1 Backup real v3 DB before bulk: `cp data/aircraft_safety_v3.db data/aircraft_safety_v3.db.pre-faa-aids-bulk`. Confirm backup exists before proceeding.
  - [ ] 5.2 Write `scripts/faa_aids_bulk_import.py` modelled on `scripts/ntsb_bulk_import.py`:
    - Accepts `--db`, `--dedupe-audit`, `--mapping` (required), `--batch-size` (default 1000), `--report-out`.
    - Reads `data/logs/faa_aids_dedupe_audit.jsonl`, filters to `dedupe_status=import`.
    - Runs `FAAAIDSImporter(records=..., mapping=...)` in batches of `--batch-size`.
    - Calls `recalc_aircraft_stats(aircraft_ids)` for all touched `aircraft_id`s after import.
    - Writes `data/logs/faa_aids_bulk_import_report.json`: rows_read, imported, skipped_unmapped, skipped_asn_covered, skipped_no_date, errors, aircraft_pages_updated, before/after incident counts.
    - Second run must be idempotent (0 new rows).
  - [ ] 5.3 Stop the Flask dev server on port 5003 before running bulk import (single SQLite writer). Run: `DATABASE_URL="sqlite:////…/data/aircraft_safety_v3.db" python scripts/faa_aids_bulk_import.py --mapping data/config/faa_aids_make_model_to_aircraft.jsonl`. Monitor progress logs. Restart Flask after completion.
  - [ ] 5.4 Write `scripts/audit_post_faa_aids_import.py` modelled on `scripts/audit_post_ntsb_import.py`:
    - Checks FAA AIDS incidents that match an ASN incident with ≥ 2 strong dedupe signals (post-write safety net).
    - Checks any `IncidentSource(source_name="FAA_AIDS")` rows with `source_url` failing `assert_valid_source_url`.
    - Accepts `--remediate` flag: deletes confirmed FAA AIDS duplicate incidents.
    - Writes `data/logs/faa_aids_post_import_audit.json` with: duplicate_count, bad_url_count, samples.
  - [ ] 5.5 Run post-import audit: `python scripts/audit_post_faa_aids_import.py`. Review report. If `duplicate_count > 0`, run with `--remediate` and re-audit to confirm 0. Audit must pass (0 critical issues) before marking complete.
  - [ ] 5.6 Update `display_make_model()` in `app/link_picker.py` to also return `faa_aids_make_model` from `source_data` for `FAA_AIDS` rows (same pattern as NTSB branch already in the function).
  - [ ] 5.7 Run full test suite: `PYTHONPATH=. pytest -q`. All tests (77 existing + new FAA tests) must be green.
  - [ ] 5.8 Manual smoke test on `http://127.0.0.1:5003`:
    - Search `?q=Boeing` and `?q=Airbus` — confirm pages load.
    - Open an aircraft page that received FAA AIDS rows (check `faa_aids_bulk_import_report.json` for a touched aircraft_id). Confirm FAA incidents appear in the incident table.
    - Click a `Details ↗` link on a FAA AIDS row — confirm it opens an ASIAS page specific to that event (not the catalog landing page).
    - Confirm the `Make/Model` column shows the raw FAA string (e.g. `BOEING 7373H4`).
    - Confirm existing ASN and NTSB rows are unaffected on the same page.
  - [ ] 5.9 Update `JOURNAL.md` with a completion entry: branch, final FAA AIDS counts (imported, skipped, aircraft pages updated), test count, date.
