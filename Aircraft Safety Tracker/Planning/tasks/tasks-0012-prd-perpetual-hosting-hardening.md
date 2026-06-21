# Task List: 0012 — Perpetual Hosting Hardening

**PRD:** `Planning/tasks/0012-prd-perpetual-hosting-hardening.md`  
**Branch:** `v6-perpetual-hosting-hardening`  
**Status:** Ready for implementation

---

## Relevant Files

- `app/models.py` — Added `summary_generated_at` to `Aircraft`; added `IngestionState` model ✅
- `migrations/versions/a1b2c3d4e5f6_add_summary_generated_at_to_aircraft.py` — New migration ✅
- `migrations/versions/b2c3d4e5f6a7_add_ingestion_state_table.py` — New migration ✅
- `tests/test_v6_models.py` — New: schema tests for both additions (4 tests) ✅
- `app/services/deepseek.py` — TTL cache gate `get_or_generate_summary` + `is_summary_fresh` ✅
- `app/routes.py` — `generate_summary_background` (force + failure-restore) & `regenerate_summary` (force param, freshness guard) ✅
- `app/__init__.py` — Registered `is_summary_fresh` + `summary_generating_marker` Jinja globals ✅
- `app/templates/components/summary_card.html` — Auto-trigger only when not fresh; manual button forces ✅
- `tests/test_ai_summary_cache.py` — New: 5 cache + 4 route/template tests ✅
- `tests/test_summary.py` — Updated mock target to `app.services.deepseek.DeepSeekService` ✅
- `scripts/weekly_ingest.py` — New: weekly cron entrypoint (NTSB + ASN, retry, state update)
- `app/ingestion/clients/ntsb_api.py` — New: NTSB incremental fetch (approach confirmed in 3.1)
- `scripts/scrape_boeing.py` — Existing ASN scraper (called by cron; no changes needed)
- `scripts/scrape_airbus.py` — Existing ASN scraper (called by cron; no changes needed)
- `scripts/import_data.py` — Existing ASN importer (safe to re-run; dedupes on `asn_url`)
- `app/ingestion/importers/ntsb_importer.py` — Existing; accepts `records` iterable; no changes
- `data/config/ntsb_make_model_to_aircraft.jsonl` — NTSB mapping; new records may be unmapped
- `tests/test_weekly_ingest.py` — New: orchestration, retry logic, state update tests
- `tests/test_ntsb_api_client.py` — New: mocked HTTP tests for NTSB fetch client

### Notes

- Run pytest from `Aircraft Safety Tracker/` with `PYTHONPATH=. pytest -q`
- TDD required: write failing test → confirm RED → implement → confirm GREEN for every sub-task
- **Task ordering:** Tasks 1 and 2 (migrations + AI cache) are fully independent of Tasks 3–5 (cron).
  Start with Task 2 (lower risk, no external dependencies) if preferred.
- **NTSB data source:** `data/raw/ntsb_records_full.json` was a one-time bulk export from v2 DB —
  NOT a live API pull. No NTSB API client exists yet. `carol.ntsb.gov` is a JS SPA (LEARNINGS §25).
  Task 3.1 is a research step that must be completed before writing any NTSB fetch code.
- **NTSB mapping gap:** New records with unrecognised make/model strings are silently skipped by
  `NTSBImporter.skipped_unmapped`. The cron must log this count prominently (see Task 4.5).

---

## Tasks

- [x] 1.0 Database Migrations
  - [x] 1.1 Write a failing test asserting that `Aircraft` model has a `summary_generated_at`
        attribute of type `DateTime` (nullable). _(RED: TypeError invalid kwarg)_
  - [x] 1.2 Add `summary_generated_at = db.Column(db.DateTime, nullable=True)` to `Aircraft`
        in `app/models.py`. Migration hand-written (`a1b2c3d4e5f6`, batch_alter for SQLite
        compat) instead of autogenerate (dev DB not at head; SQLite autogen flaky). Test GREEN.
  - [x] 1.3 Write a failing test asserting that an `IngestionState` model/table exists with
        columns: `id` (Integer PK), `last_run_at` (DateTime nullable), `last_run_status`
        (String 32, nullable). _(RED: ImportError)_
  - [x] 1.4 Add `IngestionState` model to `app/models.py`. Migration hand-written
        (`b2c3d4e5f6a7`, chained after `a1b2c3d4e5f6`). Test GREEN.
  - [x] 1.5 Ran `flask db upgrade head` against throwaway `/tmp` SQLite DB — full chain applies,
        single head `b2c3d4e5f6a7`, both column + table verified, temp DB removed.
  - [x] 1.6 Full regression: **161 passed** (was 157; +4 new schema tests).

- [x] 2.0 AI Summary Caching
  - [x] 2.1 Wrote 5 failing tests in `tests/test_ai_summary_cache.py` (hit/miss/stale/force/failure).
        _(RED: ImportError on `get_or_generate_summary`.)_
  - [x] 2.2 TTL read via `int(os.environ.get('AI_SUMMARY_TTL_DAYS', '7'))` in the service layer
        (`_summary_ttl_days()`, default const `DEFAULT_SUMMARY_TTL_DAYS = 7`). No UI.
  - [x] 2.3 Added `get_or_generate_summary(aircraft, *, force, ai_service, commit)` + `is_summary_fresh`
        + `_usable_cached_summary` to `app/services/deepseek.py`. Sets `ai_summary` +
        `summary_generated_at` on success; preserves usable cache on failure (excludes in-progress
        `GENERATING_MARKER`).
  - [x] 2.4 `generate_summary_background(..., force, prev_summary, prev_generated_at)` now routes
        through the gate and restores the prior good summary on failure (FR-2.5).
  - [x] 2.5 `regenerate_summary` route: `?force=true` (manual button) bypasses cache; fresh + no-force
        page-load trigger serves cached card with **no API call**. Template auto-triggers only when
        `not is_summary_fresh` and not mid-generation; manual button passes `force='true'`.
  - [x] 2.6 All 5 service tests + 4 new route/template tests GREEN (9 new).
  - [x] 2.7 Full regression: **170 passed**, no lint errors.

- [ ] 3.0 NTSB Incremental Fetch (research + build)
  - [ ] 3.1 **Research (no code yet):** Make a manual HTTP request to
        `https://data.ntsb.gov/carol-main-public/api/Query/GetInvestigations` with a small
        date range (e.g. last 7 days). Inspect the response shape, pagination, and available
        filter parameters. Document findings as a comment block at the top of
        `app/ingestion/clients/ntsb_api.py` before any implementation. If this endpoint is
        unavailable or unsuitable, evaluate the NTSB bulk data download
        (`ntsb.gov/safety/data/Pages/AviationDataSystems.aspx`) and decide on approach:
        **A** (REST API with dateFrom) or **B** (periodic bulk download + diff on `cm_ntsbNum`
        against existing `IncidentSource.source_record_id` values in DB).
  - [ ] 3.2 Write failing tests in `tests/test_ntsb_api_client.py` with mocked HTTP:
        (a) `fetch_ntsb_since(since_date)` returns a list of raw record dicts;
        (b) records are filtered to Boeing/Airbus only (`is_boeing_or_airbus_make_model`);
        (c) function handles pagination if the API paginates results;
        (d) returns empty list (not error) when no records match the date range.
        Confirm all RED before implementing.
  - [ ] 3.3 Implement `app/ingestion/clients/ntsb_api.py` with a single public function
        `fetch_ntsb_since(since: datetime) -> list[dict]`. For approach A: use `httpx` with
        the confirmed API endpoint and `dateFrom` parameter. For approach B: download the
        bulk JSON, load it, filter to records with `cm_eventDate > since`, and return only
        those not already in DB (`cm_ntsbNum` not in existing `source_record_id` values).
        Apply the `is_boeing_or_airbus_make_model` filter in both approaches.
  - [ ] 3.4 Confirm all tests from 3.2 GREEN.
  - [ ] 3.5 Run full regression: `PYTHONPATH=. pytest -q`. All tests green.

- [ ] 4.0 Weekly Ingest Script (`scripts/weekly_ingest.py`)
  - [ ] 4.1 Write failing tests in `tests/test_weekly_ingest.py`:
        (a) `run_ingest()` with mocked importers completes and sets `ingestion_state.last_run_status = 'ok'`;
        (b) a source that raises on first two attempts succeeds on third (retry logic);
        (c) a source that fails all three retries is skipped; `last_run_status` is set to `'partial'`;
        (d) `ingestion_state.last_run_at` is updated to `NOW()` whether status is `ok` or `partial`.
        Confirm all RED.
  - [ ] 4.2 Create `scripts/weekly_ingest.py` with a Flask app context setup (mirrors other
        scripts in `scripts/`). Structure: `run_ingest()` orchestration function + `_run_with_retry(fn, name, max_retries=3, delay=60)` helper.
  - [ ] 4.3 Wire **NTSB source** inside `run_ingest()`:
        read `last_run_at` from `IngestionState` (default to 90 days ago on first run);
        call `fetch_ntsb_since(last_run_at)` → pass records to `NTSBImporter(records=..., mapping=MAPPING_PATH).run()`;
        log: records fetched, records written, `skipped_unmapped` count (must be explicit — see Notes).
  - [ ] 4.4 Wire **ASN source** inside `run_ingest()`:
        call `scrape_boeing.main()` then `scrape_airbus.main()` to refresh
        `data/raw/boeing_incidents.json` and `data/raw/airbus_incidents.json`;
        call `import_data.main()` to import into DB;
        log: new rows inserted vs skipped (dedupe on `asn_url`).
  - [ ] 4.5 After all sources: update `IngestionState` row (upsert — create if not exists);
        set `last_run_at = datetime.utcnow()`, `last_run_status = 'ok'` or `'partial'`.
        Log final table counts for `aircraft`, `incident`, `incident_source`.
  - [ ] 4.6 Confirm all tests from 4.1 GREEN.
  - [ ] 4.7 Run full regression: `PYTHONPATH=. pytest -q`. All tests green.

- [ ] 5.0 Railway Cron Service Configuration & Smoke Validation
  - [ ] 5.1 Commit all v6 work (models, migrations, services, scripts, tests) to
        `v6-perpetual-hosting-hardening` and push to origin. Confirm CI passes (or run
        `PYTHONPATH=. pytest -q` locally as a stand-in).
  - [ ] 5.2 In Railway dashboard → Portfolio-v5 project → **+ New** → **Cron Service**:
        - Source: same GitHub repo, branch `v6-perpetual-hosting-hardening`
        - Root Directory: `Aircraft Safety Tracker`
        - Start Command: `PYTHONPATH=. python scripts/weekly_ingest.py`
        - Schedule: `0 2 * * 1` (every Monday 02:00 UTC)
        - Environment: add `DATABASE_URL` = `${{Postgres-cYEh.DATABASE_URL}}`, `FLASK_CONFIG=production`
  - [ ] 5.3 Deploy Portfolio-v5 web service from the same v6 branch (this applies the DB
        migrations via `flask db upgrade head` in the start command, which should already
        be `flask db upgrade head && gunicorn run:app`). Confirm deploy succeeds.
  - [ ] 5.4 Trigger a **manual first run** of the cron service (Railway → Cron → "Run Now").
        Watch the deploy logs. Confirm: no Python errors, NTSB fetch logs output, ASN scrape
        starts, `ingestion_state` updated message appears.
  - [ ] 5.5 Query Postgres-cYEh directly to confirm `ingestion_state.last_run_at` is set and
        `last_run_status` is `'ok'` or `'partial'`.
        ```sql
        SELECT last_run_at, last_run_status FROM ingestion_state;
        ```
  - [ ] 5.6 Load `/aircraft/23` (Boeing 737-800) on the live Portfolio-v5 URL. Confirm the AI
        summary loads from cache (no visible delay on second load). Check `summary_generated_at`
        is set in DB:
        ```sql
        SELECT model_name, summary_generated_at FROM aircraft WHERE id = 23;
        ```
  - [ ] 5.7 Update `JOURNAL.md` and `LEARNINGS.md` with any new bugs or patterns encountered
        during this task. Run compound session close-out per AGENTS.md.
