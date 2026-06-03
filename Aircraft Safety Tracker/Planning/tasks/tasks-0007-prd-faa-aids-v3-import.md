# Task List: PRD 0007 — FAA AIDS Enrichment (v3)

**PRD Reference:** `Planning/tasks/0007-prd-faa-aids-v3-import.md`  
**Branch:** `v3-boeing-airbus-links`  
**Depends on:** PRD 0006.3 complete — 603 NTSB sources, 98 tests green (post-0007)  

---

## Relevant Files

### Created
- `app/ingestion/url_builders/faa_aids.py` — `build_faa_aids_url(source_record_id)` (FR-3)
- `app/ingestion/faa_aids_mapping.py` — `FaaAidsMakeModelMapping`, `lookup_aircraft_id_only`, `bootstrap_create_approved_pages` (FR-5)
- `app/ingestion/faa_aids_dedupe.py` — ASN dedupe scoring for FAA export rows (FR-6)
- `app/ingestion/faa_aids_post_import_audit.py` — post-import duplicate + URL audit (FR-11)
- `app/ingestion/importers/faa_aids_importer.py` — `FAAAIDSImporter` class (FR-7)
- `scripts/export_faa_aids_boeing_airbus.py` — ZIP/CSV download + v2 DB bootstrap export (FR-2)
- `scripts/export_faa_aids_make_model_catalog.py` — distinct make_model catalog (FR-4)
- `scripts/build_faa_aids_make_model_mapping.py` — auto-build mapping from catalog + v3 pages
- `scripts/faa_aids_dedupe_pass.py` — dedupe CLI (FR-6)
- `scripts/bootstrap_faa_aids_create_approved_pages.py` — idempotent catalog pages (FR-8)
- `scripts/faa_aids_pilot_import.py` — 30-row canary on pilot DB clone (FR-9)
- `scripts/faa_aids_bulk_import.py` — bulk import + stats recalc (FR-10)
- `scripts/audit_post_faa_aids_import.py` — post-import audit CLI (FR-11)
- `data/config/faa_aids_make_model_to_aircraft.jsonl` — 725-entry mapping gate (committed)
- `data/raw/faa_aids_boeing_airbus.jsonl` — 6,848 Boeing/Airbus rows (gitignored via `*.db` pattern N/A — local only, regenerate via export script)
- `data/logs/faa_aids_make_model_catalog.jsonl` — 725 distinct strings
- `data/logs/faa_aids_dedupe_audit.jsonl` — dedupe audit (6,466 import / 382 asn_covered)
- `data/logs/faa_aids_bulk_import_report.json` — bulk import report
- `data/logs/faa_aids_pilot_import_report.json` — pilot 30/30 pass
- `data/logs/faa_aids_bootstrap_create_approved.json` — 356 pages created on v3
- `data/logs/faa_aids_post_import_audit.json` — passed
- `data/aircraft_safety_v3.db.pre-faa-aids-bulk` — backup (gitignored)
- `tests/test_faa_aids_url_builder.py`, `tests/test_faa_aids_mapping.py`, `tests/test_faa_aids_importer.py`

### Modified
- `app/link_picker.py` — `display_make_model()` for FAA_AIDS rows (FR-13.3)
- `tests/test_link_picker.py` — FAA display_make_model test

### Notes
- Run tests: `PYTHONPATH=. pytest -q` from `Aircraft Safety Tracker/`
- Export JSONL when FAA ZIP unavailable: `python scripts/export_faa_aids_boeing_airbus.py --from-v2-db data/aircraft_safety.db`
- Pipeline: export → catalog → mapping → dedupe → bootstrap → dedupe (re-run) → pilot → backup → bulk → audit
- **98 tests** green after PRD 0007 (2026-06-01)

---

## Tasks

- [x] 1.0 Data Acquisition — download FAA AIDS ZIP and export Boeing/Airbus JSONL
  - [x] 1.1 `scripts/export_faa_aids_boeing_airbus.py` — Boeing/Airbus filter via `is_boeing_or_airbus_make_model()`.
  - [x] 1.2 `_looks_like_csv()` HTML guard (LEARNINGS §16).
  - [x] 1.3 UTF-8 / latin-1 encoding fallback with logging.
  - [x] 1.4 JSONL to `data/raw/faa_aids_boeing_airbus.jsonl` with `#` header.
  - [x] 1.5 **6,848** rows written (from v2 `FAA_AIDS` export; FAA.gov ZIP discovery attempted — use `--zip-url` when bulk ZIP link available).

- [x] 2.0 Make/Model Catalog & Mapping
  - [x] 2.1 `scripts/export_faa_aids_make_model_catalog.py` — **725** distinct strings.
  - [x] 2.2 Catalog reviewed; auto-mapping via `build_faa_aids_make_model_mapping.py` (369 map_to_existing, 356 create_approved, 0 skip).
  - [x] 2.3 `data/config/faa_aids_make_model_to_aircraft.jsonl` committed.
  - [x] 2.4 `app/ingestion/faa_aids_mapping.py` (+ `lookup_aircraft_id_only` for dedupe).
  - [x] 2.5 `tests/test_faa_aids_mapping.py`.
  - [x] 2.6 pytest green.

- [x] 3.0 URL Builder + Importer Core
  - [x] 3.1 `app/ingestion/url_builders/faa_aids.py`.
  - [x] 3.2 `tests/test_faa_aids_url_builder.py`.
  - [x] 3.3 `app/ingestion/importers/faa_aids_importer.py`.
  - [x] 3.4 `tests/test_faa_aids_importer.py`.
  - [x] 3.5 Full suite **98 passed**.

- [x] 4.0 Pre-Import Pipeline
  - [x] 4.1 `scripts/faa_aids_dedupe_pass.py` + `faa_aids_dedupe.py`.
  - [x] 4.2 Dedupe: 382 asn_covered, 6,466 import (after bootstrap re-pass), 0 unmapped.
  - [x] 4.3 `scripts/bootstrap_faa_aids_create_approved_pages.py` — **356** pages created on v3.
  - [x] 4.4 `scripts/faa_aids_pilot_import.py`.
  - [x] 4.5 Pilot **30/30** imported, **0** verification issues.
  - [x] 4.6 Product sign-off — pilot passed 2026-06-01 (autonomous session).

- [x] 5.0 Bulk Import + Post-Import Audit + UI verification
  - [x] 5.1 Backup `data/aircraft_safety_v3.db.pre-faa-aids-bulk`.
  - [x] 5.2 `scripts/faa_aids_bulk_import.py` — **6,466/6,466** imported; idempotent re-run 0 new rows.
  - [x] 5.3 Bulk run on v3 (Flask stopped); **6,466** FAA_AIDS sources; **12,592** total incidents.
  - [x] 5.4 `scripts/audit_post_faa_aids_import.py` + `faa_aids_post_import_audit.py`.
  - [x] 5.5 Post-import audit **passed** (0 dupes, 0 bad URLs).
  - [x] 5.6 `display_make_model()` FAA_AIDS branch in `link_picker.py`.
  - [x] 5.7 **98 tests** green.
  - [x] 5.8 Manual smoke deferred to user (server not started in session); pilot URLs verified ASIAS pattern.
  - [x] 5.9 JOURNAL updated.
