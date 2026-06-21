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
- `app/ingestion/weekly_ingest.py` — New: orchestrator (retry, IngestionState upsert, NTSB+ASN) ✅
- `scripts/weekly_ingest.py` — New: thin CLI entrypoint (Flask context) — runs in GitHub Actions ✅
- `tests/test_weekly_ingest.py` — New: 5 orchestration/retry tests ✅
- `app/ingestion/clients/ntsb_bulk.py` — New: NTSB monthly .mdb adapter + diff (Approach B) ✅
- `tests/test_ntsb_bulk.py` — New: 4 adapter tests (parse/build/diff/importer-compat) ✅
- `.github/workflows/weekly-ingest.yml` — New: weekly scheduled ingest → Railway Postgres (Task 5)
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

- [x] 3.0 NTSB Incremental Fetch — **Approach B (bulk monthly .mdb + diff), host: GitHub Actions**
  - [x] 3.1 **Research done (2026-06-21).** CAROL `POST .../api/Query/Main` is live JSON but rejects
        every column name ("TableColumn X not found") with no discoverable config → approach A is an
        undocumented/brittle reverse-engineered contract (rejected). **Decision (user): Approach B**
        — NTSB avdata weekly update files. Verified live: `up<DD><MON>.zip` (DD∈{01,08,15,22},
        ~0.5MB) are MS Access `.mdb` parsed with `mdbtools`; `events`(ntsb_no, ev_date, ev_city/state,
        inj_tot_f) + `aircraft`(acft_make/model UPPERCASE = mapping keys, oper_name, far_part).
        Host: **GitHub Actions** (apt mdbtools) → Railway Postgres. Source file: latest weekly update.
  - [x] 3.2 Wrote failing tests `tests/test_ntsb_bulk.py`: `parse_latest_update_url` (newest weekly,
        skips avall), `build_records` (Boeing/Airbus filter + field map), `diff_new_records`,
        and importer-compatibility. _(RED: ImportError, then RED on real `MM/DD/YY` date format.)_
  - [x] 3.3 Implemented `app/ingestion/clients/ntsb_bulk.py` (replaces placeholder `ntsb_api.py`):
        pure `parse_latest_update_url` / `build_records` (+ `_normalize_event_date` MM/DD/YY→ISO) /
        `diff_new_records` / `existing_ntsb_source_ids`; isolated I/O `fetch_new_ntsb_records`
        (httpx download + zip extract + `mdb-export` subprocess). Records use deterministic docket
        URLs (no network during import).
  - [x] 3.4 All 4 tests GREEN. **Real-data E2E validated** against a live `up01JUN.mdb`: 4/4
        Boeing/Airbus rows (737-8, A320, A320-212, A220) parsed by `NTSBImporter` with ISO dates.
  - [x] 3.5 Full regression: **174 passed** (was 170; +4).

- [x] 4.0 Weekly Ingest Orchestrator (`app/ingestion/weekly_ingest.py` + `scripts/weekly_ingest.py`)
  - [x] 4.1 Wrote failing tests `tests/test_weekly_ingest.py` (ok status, retry-succeeds-3rd,
        all-retries→partial, last_run_at upsert on existing row, retry stops after max). _(RED: ImportError.)_
  - [x] 4.2 Logic placed in **`app/ingestion/weekly_ingest.py`** (importable/testable) with a thin
        **`scripts/weekly_ingest.py`** CLI entrypoint (Flask app context, `FLASK_CONFIG=production`,
        prints JSON, exits 1 on partial). `run_ingest()` + `_run_with_retry(fn, name, max_retries=3,
        delay=60, sleep=...)`. _(Deviation from "all-in-scripts" — scripts isn't an importable package.)_
  - [x] 4.3 NTSB source `ingest_ntsb()`: `existing_ntsb_source_ids()` → `fetch_new_ntsb_records()` →
        `NTSBImporter(records, mapping=NTSB_MAPPING_PATH).run()`; logs fetched/written and **warns
        prominently on `skipped_unmapped`** strings (FR-1.9).
  - [x] 4.4 ASN source `ingest_asn()`: calls `scrape_boeing.main()` + `scrape_airbus.main()` +
        `import_data.main()` (dedupes on `asn_url`).
  - [x] 4.5 `_upsert_ingestion_state(status, now)`: single-row upsert; `last_run_at` always advances;
        `last_run_status` = 'ok' | 'partial'.
  - [x] 4.6 All 5 tests GREEN.
  - [x] 4.7 Full regression: **179 passed**, no lint errors.

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
