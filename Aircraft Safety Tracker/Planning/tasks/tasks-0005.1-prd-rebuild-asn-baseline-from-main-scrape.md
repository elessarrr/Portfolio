## Relevant Files

- `scripts/scraper_utils.py` - ASN fetch/parse helpers; must match deployed-main behavior.
- `scripts/scrape_boeing.py` - Boeing type-index scrape → `data/raw/boeing_incidents.json`.
- `scripts/scrape_airbus.py` - Airbus type-index scrape → `data/raw/airbus_incidents.json`.
- `scripts/import_data.py` - Loads raw JSON into `Aircraft` + `Incident.asn_url`; recalculates stats.
- `scripts/rebuild_asn_baseline.py` - Optional wrapper: scrape + import + verify (create if product approves FR-7 open question).
- `data/aircraft_safety_v3.db` - Target SQLite DB; generated locally, never committed.
- `data/raw/boeing_incidents.json` - Fresh scrape output artifact (local unless explicitly committed).
- `data/raw/airbus_incidents.json` - Fresh scrape output artifact (local unless explicitly committed).
- `app/link_picker.py` - ASN-first Details link rendering on v3.
- `app/templates/components/incident_list.html` - Incident list macro using `pick_primary_href`.
- `app/ingestion/url_builders/ntsb.py` - End-of-PRD fix: CAROL before docket when appropriate.
- `tests/test_ntsb_importer.py` - Resolver priority tests for FR-8.
- `tests/test_link_picker.py` - Existing ASN link tests; run after rebuild smoke checks.
- `JOURNAL.md` - Record PRD 0005.1 rebuild decision and final counts.
- `Planning/tasks/0005.1-prd-rebuild-asn-baseline-from-main-scrape.md` - PRD reference.

### Notes

- Do **not** use `data/aircraft_safety.db` (v2) as ASN source data.
- Scrape may take a long time (network + rate limits); run Boeing then Airbus sequentially.
- Run tests from `Aircraft Safety Tracker/` with `PYTHONPATH=. pytest -q`.
- App smoke tests use `DATABASE_URL=sqlite:////absolute/path/to/data/aircraft_safety_v3.db` or equivalent Flask config.

## Tasks

- [x] 1.0 Confirm scrape/import parity with deployed main
  - [x] 1.1 Confirm branch is `v3-boeing-airbus-links` and PRD 0005 revert commits are present (no `copy_v2_to_v3.py`).
  - [x] 1.2 Diff v3 `scripts/scrape_boeing.py`, `scrape_airbus.py`, and `scraper_utils.py` against deployed-main snapshot; note any intentional differences.
  - [x] 1.3 Confirm `scripts/import_data.py` still writes only to `Incident.asn_url` and does not create `IncidentSource` rows.
  - [x] 1.4 Document decision: use existing v3 scripts as-is, or sync any missing deployed-main behavior before scraping.

- [x] 2.0 Prepare clean v3 target database
  - [x] 2.1 Delete any existing `data/aircraft_safety_v3.db` from the wrong PRD 0005 copy (if present).
  - [x] 2.2 Run `flask db upgrade heads` against a fresh `data/aircraft_safety_v3.db` (v3 schema only).
  - [x] 2.3 Verify tables exist and are empty: `aircraft`, `incident`, `incident_source` (0 rows).

- [x] 3.0 Run fresh Boeing ASN scrape
  - [x] 3.1 Back up or rename stale `data/raw/boeing_incidents.json` (e.g. `boeing_incidents.json.bak`) before overwriting.
  - [x] 3.2 Run `python scripts/scrape_boeing.py` with network access; monitor logs for ASN errors.
  - [x] 3.3 Verify output JSON includes expected Boeing model families (spot-check for `Boeing 747` in `model_name` values).
  - [x] 3.4 Record row count and unique `model_name` count in scrape log or a short markdown note.

- [x] 4.0 Run fresh Airbus ASN scrape
  - [x] 4.1 Back up or rename stale `data/raw/airbus_incidents.json` before overwriting.
  - [x] 4.2 Run `python scripts/scrape_airbus.py` with network access.
  - [x] 4.3 Verify output JSON structure matches import expectations (`asn_url`, `narrative`, `category`, etc.).
  - [x] 4.4 Record row count and unique `model_name` count.

- [x] 5.0 Import scraped JSON into v3 database
  - [x] 5.1 Set `DATABASE_URL` (or Flask config) to point at `data/aircraft_safety_v3.db`.
  - [x] 5.2 Run `python scripts/import_data.py` (Boeing then Airbus via script’s `main()`).
  - [x] 5.3 Query DB: `incident_source` count must be **0**.
  - [x] 5.4 Query DB: all incidents have non-empty `asn_url`.
  - [x] 5.5 Recalculate verification: aircraft count, incident count, breakdown by manufacturer.

- [x] 6.0 Deployed-main parity verification (app smoke)
  - [x] 6.1 Start Flask against `aircraft_safety_v3.db`.
  - [x] 6.2 Confirm homepage HTTP 200.
  - [x] 6.3 Search `747` returns a Boeing 747 family aircraft with incidents (e.g. `Boeing 747-100`).
  - [x] 6.4 Open `Boeing 747-100` page: HTTP 200, incident rows visible, **~100** incidents (document actual count if ASN drift).
  - [x] 6.5 Spot-check a Boeing 727-family page and a representative Airbus page: not empty, Details links present.
  - [x] 6.6 Confirm no `href=""` and no `N/A` in Details column for copied ASN incidents.
  - [x] 6.7 Run `PYTHONPATH=. pytest -q`.

- [x] 7.0 Document rebuild and optional automation
  - [x] 7.1 Update `JOURNAL.md`: PRD 0005 superseded; PRD 0005.1 source = main scrape/import; final counts + parity notes.
  - [x] 7.2 Decide per open question: commit fresh raw JSON or keep local only; document in JOURNAL.
  - [ ] 7.3 (Optional) Add `scripts/rebuild_asn_baseline.py` wrapping scrape + import + print verification SQL.

- [x] 8.0 Fix NTSB URL resolver priority (end of PRD, before NTSB bulk)
  - [x] 8.1 Reorder `resolve_ntsb_source_url()` in `app/ingestion/url_builders/ntsb.py`: CAROL when `carol_detail_has_public_content` + `cm_mkey`, then docket, then brief.
  - [x] 8.2 Add tests: CAROL wins over docket when both eligible; DirectorBrief → docket only; `cm_agency=Other` → no CAROL.
  - [x] 8.3 Run `PYTHONPATH=. pytest -q` and commit fix separately from rebuild artifacts if desired.
