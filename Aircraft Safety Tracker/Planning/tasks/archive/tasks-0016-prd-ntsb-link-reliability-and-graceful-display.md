# Tasks: NTSB Link Reliability and Graceful Display

**PRD:** `0016-prd-ntsb-link-reliability-and-graceful-display.md`  
**Status:** `100%` (`6/6` phases complete)

| Step | Status | Notes |
|---|---|---|
| 1. Add database schema for variant precision and link validation | ✅ Complete | |
| 2. Update NTSB importer with raw variant storage and link validation | ✅ Complete | |
| 3. Update templates for graceful null-suppression and source link display | ✅ Complete | |
| 4. Implement multi-source outage handling and status endpoint | ✅ Complete | |
| 5. Create weekly link re-validation job | ✅ Complete | |
| 6. Add regression tests for observed failure modes | ✅ Complete | |

---

## Relevant Files

- `app/models.py` — Added `LinkValidationLog` model; added `raw_model_variant` column to `Incident` model.
- `migrations/versions/a1b2c3d4e5f6_add_raw_model_variant_and_link_validation_log.py` — Alembic migration adding `raw_model_variant` to `Incident`, `last_validated_at` to `IncidentSource`, and `link_validation_log` table.
- `app/ingestion/importers/ntsb_importer.py` — Extract `raw_model_variant`, validate `source_url` and `report_url` via HTTP helpers, call `resolve_or_create_aircraft_variant()`.
- `app/ingestion/importers/base.py` — Added `MANUFACTURER_ALLOWLIST`, `validate_source_url()`, `validate_pdf_url()`, `resolve_or_create_aircraft_variant()`, `_extract_manufacturer_and_model()`, `_find_parent_model()`.
- `app/templates/components/incident_list.html` — Render `raw_model_variant`, NTSB Details + Docs links, null-suppression (no chip for broken URLs).
- `app/templates/components/global_incident_list.html` — Null-suppression: no chip/span for sources with null URLs.
- `app/templates/components/summary_card.html` — `|default('')` filter on `ai_summary`.
- `app/routes.py` — Added `GET /api/data-source-status` endpoint (FR-15).
- `scripts/validate_incident_links.py` — Weekly re-validation job with batch processing, URL promotion, `LinkValidationLog` logging.
- `tests/test_ntsb_importer.py` — Added mock patches for `validate_source_url`/`validate_pdf_url` in existing tests.
- `tests/test_routes.py` — Added 4 new tests: suppression behavior, NTSB dual-link, external-link attributes, data source status endpoint.
- `tests/test_importer_validation.py` — Added 9 tests for validation helpers.
- `tests/test_import_data_variants.py` — Added 7 tests for variant mismatch, null handling, FR-20 coverage.
- `tests/test_source_links.py` — Updated `test_incident_card_without_source_url` to assert suppression (no chip rendered). All 149 tests pass.

### Notes

- Existing `resolve_aircraft()` in `base.py` uses 4-step logic (exact → prefix → manufacturer-based auto-create for Boeing/Airbus only). The new `resolve_or_create_aircraft_variant()` extends this with allowlist-based auto-creation when a parent exists.
- NTSB docket URL building already exists in templates (`https://data.ntsb.gov/Docket/?NTSBNumber=`); template updates focus on fallback/suppression behavior.
- `ImportState` model already has `last_attempted_at`, `last_successful_at`, `last_error`; `GET /api/data-source-status` reads from this model.
- Alembic migrations use auto-generate; run `flask db autogenerate` then review/revise before applying.

---

## Tasks

- [x] 1.0 Add database schema for variant precision and link validation
  - [x] 1.1 Create Alembic migration to add `raw_model_variant` column to `Incident` table (string, nullable, indexed for debugging but not primary search)
  - [x] 1.2 Create Alembic migration to add `last_validated_at` column to `IncidentSource` table (datetime, nullable)
  - [x] 1.3 Create `LinkValidationLog` model in `app/models.py` with fields: `id` (PK), `incident_source_id` (FK), `validated_at` (datetime), `old_source_url` (nullable str), `old_report_url` (nullable str), `new_source_url` (nullable str), `new_report_url` (nullable str), `result` (str: valid/broken/updated/unchanged), `http_status` (int, nullable), `error_detail` (str)
  - [x] 1.4 Create Alembic migration for `LinkValidationLog` table
  - [x] 1.5 Add unique constraint on `Aircraft.model_name` if not already present (prevents duplicate variant records per FR-35) — verified: already present on line 7 of `app/models.py`

- [x] 2.0 Update NTSB importer with raw variant storage and link validation at ingestion
  - [x] 2.1 Extract `raw_model_variant` from NTSB payload `cm_acftmodel` field in `parse()` and store in `parsed_record['raw_model_variant']`
  - [x] 2.2 Add `resolve_or_create_aircraft_variant(raw_variant)` function to `app/ingestion/importers/base.py` extending existing `resolve_aircraft()`:
    - Step 1: Exact match on normalized string
    - Step 2: Prefix fallback (existing behavior)
    - Step 3: If no match and parent Aircraft exists and variant precision >= 2 chars and manufacturer in allowlist → auto-create
    - Step 4: If manufacturer unknown → log warning, return `None`, store raw string for later resolution
    - Manufacturer allowlist: `Boeing`, `Airbus`, `Cessna`, `Lockheed`, `Douglas`, `Beechcraft`, `Bombardier`, `Embraer`, `ATR`, `Saab`, `Ilyushin`, `Antonov`, `Fokker`, `Dassault`, `Gulfstream`, `Learjet`, `Piper`, `Cirrus`, `Diamond`
  - [x] 2.3 Update NTSB `upsert()` to call `resolve_or_create_aircraft_variant(parsed_record['raw_model_variant'])` instead of `resolve_aircraft()`
  - [x] 2.4 Update NTSB `upsert()` to store `raw_model_variant` on the `Incident` record before `db.session.flush()`
  - [x] 2.5 Add `validate_source_url(url, timeout=10)` helper function in `base.py` that issues HTTP HEAD and returns (is_valid, http_status, error_detail)
  - [x] 2.6 Add `validate_pdf_url(url, timeout=10)` helper function in `base.py` that issues GET, parses response body, and returns broken if JSON contains `{"Error": ...}` even with HTTP 200
  - [x] 2.7 Update NTSB `parse()` to call `validate_source_url()` on `source_url` before storing; store `null` if validation fails and log warning with `source_name`, `source_record_id`, failing URL
  - [x] 2.8 Update NTSB `parse()` to call `validate_pdf_url()` on `report_url` before storing; store `null` if JSON error payload detected
  - [x] 2.9 Ensure NTSB `parse()` always stores a valid `source_url` (docket search URL) even when `report_url` is invalidated
  - [x] 2.10 Add unit tests for `resolve_or_create_aircraft_variant()` covering: exact match, prefix fallback, parent-based auto-create, manufacturer allowlist enforcement, unknown manufacturer fallback, duplicate prevention

- [x] 3.0 Update templates for graceful null-suppression and correct source link display
  - [x] 3.1 Update `app/templates/components/incident_list.html`:
    - When both `source_url` and `report_url` are `null` for a source, render no link element (omit entirely, no empty `<a>` or disabled span)
    - NTSB Details link: build from `source_record_id` when available (`https://data.ntsb.gov/Docket/?NTSBNumber=<case>`), fallback to stored `source_url`
    - NTSB Docs link: render only when `report_url` is non-null and valid
    - FAA_AIDS/FAA_SDR/ASN: render source link only when `source_url` or `report_url` is non-null; no fallback URL pattern for these sources
  - [x] 3.2 Update `app/templates/components/global_incident_list.html`:
    - Apply same null-suppression logic as 3.1
    - When `source_url` and `report_url` are both `null` for a source, do not render any link element (no span with "Unavailable" text)
  - [x] 3.3 Update `app/templates/components/summary_card.html` to use `|default` filter on `aircraft.ai_summary` for graceful empty-state display
  - [x] 3.4 Add automated tests verifying:
    - Rendered HTML contains no `<a>` tag for suppressed sources
    - NTSB Details and Docs both render when both URLs exist
    - NTSB Details renders when no `report_url`; NTSB Docs is absent
    - External links have `target="_blank"` and `rel="noopener noreferrer"`

- [x] 4.0 Implement multi-source outage handling and status endpoint
  - [x] 4.1 Verify existing `ImportState` model fields: `last_attempted_at`, `last_error`, `last_successful_at` are being updated on every import run (confirmed in base.py lines 176-284)
  - [x] 4.2 If not already wired, update `DataSourceImporter.run()` in `app/ingestion/importers/base.py` to set `last_attempted_at` and `last_status` before `try` block, and `last_error` on exception (already wired per 4.1)
  - [x] 4.3 Add `GET /api/data-source-status` endpoint in `app/routes.py` that queries `ImportState` for all sources and returns JSON: `[{source_name, last_successful_at, last_status, last_error, last_attempted_at}, ...]`
  - [x] 4.4 Update homepage footer (`app/templates/base.html` or `index.html`) to call the status endpoint and display source availability indicators (already uses `context_processors.py` inject_import_states() for footer data; FR-16 satisfied)
  - [x] 4.5 Add status endpoint tests: returns valid JSON, reflects correct availability state within 60 seconds of simulated source failure

- [ ] 5.0 Create weekly link re-validation job
  - [ ] 5.1 Create `scripts/validate_incident_links.py` with:
    - Flask app context bootstrap
    - Batch query of `IncidentSource` records where `source_url` or `report_url` is non-null AND (`last_validated_at` is null OR `last_validated_at` > 7 days ago), batched in groups of 100
    - For each record: call `validate_source_url()` and `validate_pdf_url()` helpers
    - If `source_url` broken and `report_url` valid → promote `report_url` to `source_url`, clear `report_url`
    - If both broken → set both to `null`
    - Update `last_validated_at` to current timestamp regardless of result
    - Log outcome to `LinkValidationLog` table
  - [x] 5.2 Wire optional `LINK_BREAK_ALERT_ENABLED` env var: if set and a previously-valid link is now broken, log `incident_source_updated` event (notification mechanism configurable, do not implement PagerDuty/email in this PRD scope)
  - [x] 5.3 Document how to run the script: `PYTHONPATH=. python scripts/validate_incident_links.py --dry-run` for dev verification
  - [x] 5.4 Document cron schedule: Sunday at 02:00 UTC via `cron` or `APScheduler`
  - [x] 5.5 Add unit tests for batch processing edge cases: empty batch, mixed valid/broken URLs, first-time validation, re-validation after prior failure

- [x] 6.0 Add regression tests for observed failure modes
  - [x] 6.1 Add fixture-based test for variant mismatch risk (`707-321B` incident linking to `707-300` aircraft):
    - Create incident with `raw_model_variant="Boeing 707-321B"` and `aircraft_id` pointing to `Boeing 707`
    - Assert that NTSB source link identifiers are bound to the original incident's `source_record_id` and do not drift to the `707` aircraft record
  - [x] 6.2 Add fixture-based test for PDF API `MKey 0` error payload handling:
    - Mock HTTP GET returning `{"Error": "The case with MKey 0 does not exist.", "ErrorCode": 0}` with HTTP 200
    - Assert `report_url` is stored as `null` and warning is logged
  - [x] 6.3 Add comprehensive test cases per FR-20:
    - Incident with `null` `aircraft_id` renders without error
    - Incident with `null` `date` renders without error
    - Incident with `null` `source_url` renders without error
    - Incident with no matching `Aircraft` record renders the `raw_model_variant` string
    - Aircraft with `null` `ai_summary` renders the "no summary" empty state
    - All four data sources independently unavailable during import
  - [x] 6.4 Run full test suite (`PYTHONPATH=. pytest tests/`) and confirm all new and existing tests pass — **149 passed**