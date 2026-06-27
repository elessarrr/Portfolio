# Project Learnings

## Proactive Prevention (patterns we keep hitting)

*   **Always run from the app folder:** run Flask/pytest from `Aircraft Safety Tracker/` (not the repo root) to avoid import/path confusion.
*   **Dev DB default is v3:** `DevelopmentConfig` uses `data/aircraft_safety_v3.db` unless `DATABASE_URL` is set — do not point local Flask at `aircraft_safety.db` (v2) by mistake.
*   **NTSB UI smoke:** with Flask running, `PYTHONPATH=. python scripts/smoke_ntsb_ui.py --base-url http://127.0.0.1:5003`.
*   **ASN scraping fails from cloud IPs (HTTP 403):** aviation-safety.net blocks datacenter/cloud ranges (GitHub Actions, Railway), so ASN cannot run in the weekly cron — and the scraper *swallows* the 403 and returns 0 rows, which looks like success. The cron is **NTSB-only**; ASN is an opt-in **local** refresh from a residential IP (`scripts/weekly_ingest.py --asn-only`), and `ingest_asn()` now raises on a 0-incident scrape so a block can never report green. See `docs/solutions/integration-issues/asn-403-datacenter-ip-cloud-scrape.md`.
*   **NTSB incremental = avdata `.mdb`, not CAROL API:** the CAROL `Query/Main` JSON API rejects all column names with no discoverable config (undocumented). Use the avdata weekly `up*.zip` (.mdb via mdbtools) + diff on `source_record_id`, hosted on GitHub Actions (mdbtools installs via apt). `mdb-export -D` does NOT normalize dates — normalize `MM/DD/YY` in code. See `docs/solutions/integration-issues/ntsb-incremental-bulk-mdb-not-carol-api.md`.
*   **FAA AIDS export when ZIP fails:** `python scripts/export_faa_aids_boeing_airbus.py --from-v2-db data/aircraft_safety.db` — FAA.gov page may only list one-off zips; full AIDS bulk needs ASIAS or v2 bootstrap.
*   **FAA dedupe must not auto-create pages:** use `lookup_aircraft_id_only()` during dedupe; run `bootstrap_faa_aids_create_approved_pages.py` then **re-run dedupe** before bulk import.
*   **ASIAS is the only public per-record URL source for FAA AIDS data.** `av-info.faa.gov` redirects to ASIAS; FAA removed AIDS data from `faa.gov/data_research` (confirmed 2022 DOT PIA); no data.gov per-record dataset exists. `av-info.faa.gov/data/AID/tab/*.txt` has static bulk narratives only (c5 + remark), not individual record pages.
- **macOS cron has no `python` on PATH:** jobs fail with `/bin/sh: python: command not found`. Use a shell wrapper with full python path (e.g. `scripts/run_faa_brief_retry4_when_live.sh`), not bare `python`.
*   **Railway mise Python build:** if `mise python@3.13.1` fails with "No GitHub artifact attestations", add `Aircraft Safety Tracker/mise.toml` with `python.github_attestations = false` (or set env `MISE_PYTHON_GITHUB_ATTESTATIONS=false`).
*   **ASIAS global outages are real.** The ASIAS backend can fail site-wide (Akamai CDN error page on homepage), not just per-record. The liveness probe must require HTTP 2xx on the homepage before running any URL audit — 503 on the homepage = all individual checks will also 503, producing a false-positive mass wipe of `is_active`.
*   **URL spike vs. URL audit are different questions.** The spike (PRD 0001) proves the URL *format* works (100% on 500 rows). The audit (PRD 0007.1) checks whether each of the N specific records *still returns content* — different question, needs ASIAS to be up. Spike result does NOT make the audit unnecessary.
*   **`/audit-urls` skill:** generic workflow in skill body; FAA rules in `audit-urls/references/faa-asias.md`. JSONL buckets: `working_brief_report`, `working_search_prefill`, `not_working`.
*   **FAA overlap before bucket apply:** Run `apply_faa_audit_buckets_to_db.py` only with `--overlap-audit` or re-run `audit_faa_baseline_overlap.py --apply` after bucket apply — otherwise brief rows in overlap report get reactivated.
*   **ASIAS per-record 503/403 under load ≠ bad URLs:** retry5 at concurrency 3, timeout 25s, jitter 500–1500ms turned 49/49 prior `not_working` into `working_brief_report`; use gentle settings for tail retries.
*   **FAA URL audit:** `audit_faa_aids_urls.py --url-mode brief` (default) audits page 18; `--url-mode search` for page 12. DB write-back: brief mode keeps active only for `working_brief_report`. Migrate: `migrate_faa_aids_urls_to_brief.py --apply --require-audit <jsonl>`.
*   **FAA URL audit speed:** `--concurrency 16`, `--timeout 15`, jitter on; `validate_faa_aids_url_extended(retry_once=True)`. Re-check: `--retry-failures-from` + `--merge-into`.
*   **ASIAS URL viability:** ASIAS returns 503 (Akamai CDN error) for dead/expired records — same class as NTSB CAROL empty-SPA. Use `validate_faa_aids_url()` + liveness probe before bulk checks; 503 = `asias_cdn_error`; follow all redirects to final URL then check body for content markers.
*   **FAA audit CLI pattern:** `ThreadPoolExecutor` for HTTP (8 workers + 50-200ms jitter), main thread only for DB writes in batches of 500. Worker threads return plain tuples — no SQLAlchemy session inside threads.
*   **FAA mapping catalog-only:** `build_faa_aids_make_model_mapping.py` targets aircraft `id <= 113` via `faa_variant_resolution.py`; avoid `create_approved` bloat. After bulk import, `remediate_faa_aids_mapping.py` + `export_faa_aids_final_import.py`.
*   **FAA UI smoke:** `PYTHONPATH=. python scripts/smoke_faa_aids_ui.py --base-url http://127.0.0.1:5003` (checks local pages + URL shape; FAA.gov may 503 on live HEAD).
*   **FAA AIDS pipeline order:** export → catalog → mapping → dedupe → bootstrap → dedupe → pilot → backup → bulk → `audit_post_faa_aids_import.py`.
*   **FAA audit overlay merge:** merge retry batches with `scripts/merge_faa_aids_audit_overlay.py merge` (newer row wins per `source_record_id`) — do not blind-concat retry1–4 JSONL; gap-fill missing IDs before merge; compare valid ID counts in vs out.
*   **DeepSeek `.env` key change:** restart Flask after editing `.env`; stale `aircraft.ai_summary` error blobs need regenerate or `display_ai_summary()` — new safe code does not rewrite old DB text.
*   **FAA page-18 tests:** importer/audit tests must assert `AP_BRIEF_RPT_VAR` / page 18, not `P12_AIDS_RPRT_NBR`, after PRD 0007.2.
*   **Keep dev ports explicit:** if `5001` is busy, kill the listener (or pick a new port) before starting Flask.
*   **Treat LLM calls as unreliable I/O:** handle 401 (bad key) and proxy/network failures without breaking page UX.
*   **Don’t ignore “warnings”:** Python 3.8 + pytest-asyncio defaults will keep generating noise until we upgrade / pin config.
*   **v3 → Postgres one-time load:** use `scripts/push_v3_sqlite_to_postgres.py --apply` after `flask db upgrade head`; batch inserts via `execute_batch`; terminate other DB sessions before TRUNCATE on Railway (Portfolio-v5 gunicorn holds connections).
*   **NTSB link viability ≠ HTTP 200:** docket pages can return 200 with `"has not been released"`; run body checks before import (`validate_ntsb_url`).
*   **Skip ASN aggregate family rows at import:** global `asn_url` dedupe makes “(all series)” / “ family” aircraft pages look empty in search.
*   **ASN bulk QA:** use gstack `browse` with throttling for link verification; generic headless Playwright often fails ASN anti-bot parsing.
*   **SQLite single-writer:** do not run concurrent `sqlite3` reads or a second Flask/backfill job against `data/*.db` while a bulk write is in progress (~25 min FAA backfill; ~35–40 min NTSB full link audit).
*   **Cursor agent git commits:** sandbox may block `.git/index.lock` under the parent `Portfolio/` repo — retry with full permissions or commit from a local terminal.
*   **NTSB audit scripts:** set `DATABASE_URL=sqlite:////.../data/aircraft_safety_v3.db` explicitly; JSONL export files start with `#` comment lines — skip them before `json.loads`.
*   **CAROL empty SPA ≠ viable link:** `carol.ntsb.gov/investigations/detail/{mkey}` can return HTTP 200 with `<main id="root"></main>` and no investigation text — reject via `is_carol_empty_spa_shell()` / reason `carol_empty_spa`; fall back to docket.
*   **NTSB full link audit duration:** ~3,649 HTTP checks ≈ **35–40 min** wall clock (0.2s/domain throttle + fetch); do not budget 26 min unless using a persistent link cache.
*   **NTSB import needs make/model map first:** `resolve_boeing_airbus_aircraft_id()` auto-creates `Aircraft` rows on exact string match — 632/657 working audit rows are `unknown_aircraft=true` (279 distinct strings vs 97 catalog rows). Normalize before Task 6.0 bulk import.
*   **Mock NTSB viability in tests at `ntsb.py`:** after FR-12, audit uses `resolve_ntsb_source_url_checked()` which imports `validate_ntsb_url` from `app.ingestion.url_builders.ntsb`, not `audit_ntsb_enrichment`.
*   **NTSB `mapping=` accepts `str` or `Path`:** `NTSBImporter(mapping=Path(...))` must call `load_ntsb_make_model_mapping()` — passing a raw `Path` without load causes `AttributeError: 'PosixPath' object has no attribute 'get'`.
*   **Use pytest's Python for app imports:** bare `python3` on this machine may lack Flask (`ModuleNotFoundError: No module named 'flask'`); use the conda/venv interpreter that runs `PYTHONPATH=. pytest`.
*   **Bootstrap before NTSB incident import:** run `scripts/bootstrap_ntsb_create_approved_pages.py` on pilot/real v3 DB (FR-20.0) — do not defer all 15 catalog rows to first incident insert.
*   **Dedupe vs import fatalities alignment:** `fatalities_like_import()` in `ntsb_asn.py` — dedupe re-pass must score null audit fatalities as **0** (same as `NTSBImporter`) or duplicates slip through (LEARNINGS §38).
*   **Family-page dedupe is single `aircraft_id`:** dedupe re-pass on generic `Boeing 737` will not match ASN rows on `Boeing 737-300` variant pages — expect NTSB-only family pages unless dedupe logic expands.
*   **Git gstack symlink:** `error: expected submodule path '.../.claude/skills/gstack' not to be a symbolic link` breaks `git status` in the Portfolio monorepo — fix submodule/symlink before agent commits (separate from `index.lock` sandbox issue).
*   **API secrets in `.env` only:** `config.py` lines like `DEEPSEEK_API_KEY = os.environ.get(...)` are readers, not storage — put keys in `Aircraft Safety Tracker/.env` and **restart Flask** after edits.
*   **Post–family-rollup NTSB import:** if product moves 737/787/EC130 from generic family pages to series pages, run `scripts/remediate_ntsb_variant_mapping.py` and recalc `Aircraft` stats (see `data/logs/ntsb_variant_mapping_remediation.json`).
*   **gstack browse binary path:** after `./setup` in `.claude/gstack/`, call `.claude/gstack/browse/dist/browse` — `.claude/skills/gstack/browse/dist/browse` is often missing (symlink only).
*   **Playwright in Cursor agent sandbox:** `Failed to get CPU information (ERR_SYSTEM_ERROR)` → re-run browse/QA shell with `required_permissions: ["all"]`.
*   **browse `@e` refs:** run `snapshot` after every `goto`/`wait` before `@eN` clicks; prefer CSS selectors (`select[name=type]`) when refs go stale.
*   **ORM `lazy='dynamic'`:** never `joinedload` on `Incident.sources` / `system_tags`; use batch queries or `selectinload` on non-dynamic relations only.

## 1. Database-Level Fuzzy Matching with PostgreSQL (`pg_trgm`)
One of the most powerful features of using a robust database like PostgreSQL is the ability to offload complex logic from your application code to the database engine.

*   **The "Trick":** Instead of writing Python code to loop through every record and calculate similarity scores (which is slow and memory-intensive), we can enable the `pg_trgm` (Trigram) extension directly in Postgres.
*   **How it works:** It breaks strings into 3-character chunks (trigrams). For example, "Boeing" becomes `  b`, ` bo`, `boe`, `oei`, `ein`, `ing`, `ng `. It then compares these chunks to find matches, handling typos efficiently.
*   **Implementation:**
    1.  **Enable it:** We verify checking `conn.dialect.name == 'postgresql'` and running `CREATE EXTENSION IF NOT EXISTS pg_trgm;` in a migration.
    2.  **Query it:** We can then use SQL operators like `%` (similarity) or `<->` (distance) directly in our queries.
    *   *Example:* `SELECT * FROM aircraft WHERE model_name % 'Boing';` returns "Boeing 737".

**Key Takeaway:** Always check if your database has a built-in solution for search or data processing before writing custom application logic!

## 2. Railway (Platform as a Service)
Railway is a modern deployment platform that abstracts away the complexity of managing servers (like AWS EC2).

*   **Automated CI/CD:** It connects directly to your GitHub repository. Every time you `git push`, Railway automatically builds and deploys your new code.
*   **Infrastructure as Code:**
    *   **`Procfile`**: Tells Railway exactly how to run your app (e.g., `web: gunicorn run:app`).
    *   **`runtime.txt`**: Ensures the production server uses the exact same Python version as your local environment.
*   **Managed Services:**
    *   It provisions a **PostgreSQL database** with one click.
    *   It automatically handles **Environment Variables** (secrets) like `DATABASE_URL` and `DEEPSEEK_API_KEY`, injecting them securely into your app.
    *   It provides a **Public URL** (HTTPS) out of the box.

**Key Takeaway:** Railway allows you to focus 100% on code and 0% on server maintenance, making it perfect for rapid prototyping and MVPs.

## 3. Client-Side Interactivity (Performance)
*   **Context:** For the search results "Master-Detail" view (Series -> Models), we needed instant switching between tabs.
*   **Implementation:** We rendered all data upfront but hid the inactive lists.
*   **Key Takeaway:** Interactivity: Added a small, embedded JavaScript function (`showSeries`) to handle the tab-switching logic instantly without needing a server round-trip.

## 4. Flask app import errors are usually “wrong working directory”

*   **Error message:** `Error: Could not import 'run'.`
*   **Root cause:** Running `flask run` from the repo root (`Portfolio/`) while setting `FLASK_APP=run.py`—but `run.py` lives under the `Aircraft Safety Tracker/` subdirectory, so the module isn’t importable from that cwd/PYTHONPATH.
*   **Fix / prevention:**
    *   `cd "Aircraft Safety Tracker" && export FLASK_APP=run.py && flask run`
    *   Or run: `python -m flask --app run.py run` from inside `Aircraft Safety Tracker/`

## 5. Port collisions: Flask “Address already in use”

*   **Error message:** `Address already in use` / `Port 5001 is in use by another program.`
*   **Root cause:** A prior dev server still listening on `127.0.0.1:5001`.
*   **Fix / prevention:**
    *   Kill the listener: `lsof -tiTCP:5001 -sTCP:LISTEN | xargs kill`
    *   Or start on a new port: `flask run -p 5003`

## 6. DeepSeek 401s: invalid API key should not crash UX

*   **Error message:** `openai.AuthenticationError: Error code: 401 - {'error': {'message': 'Authentication Fails, Your api key: ... is invalid', ...}}`
*   **Root cause:** Missing/invalid `DEEPSEEK_API_KEY` (or wrong env loaded) when calling the DeepSeek OpenAI-compatible API.
*   **Fix / prevention:**
    *   Ensure `.env`/Railway variables include a valid `DEEPSEEK_API_KEY`.
    *   Keep summary regeneration resilient: treat this as a recoverable error and return a user-safe message instead of failing the request.

## 7. DeepSeek “Connection error” via Proxy 403

*   **Error message:** `httpx.ProxyError: 403 Forbidden` (wrapped as `openai.APIConnectionError: Connection error.`)
*   **Root cause:** Requests routed through a proxy (local or environment-configured) that rejects the outbound call.
*   **Fix / prevention:**
    *   Check and unset proxy env vars for local dev (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`) if present.
    *   In app code, catch `APIConnectionError` and degrade gracefully (don’t block page render).

## 8. Test/run warnings: Python 3.8 and pytest-asyncio defaults

*   **Warnings observed:**
    *   `PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.`
    *   `FutureWarning: You are using a non-supported Python version (3.8.8)...`
*   **Root cause:** Local environment is Python 3.8; pytest-asyncio is warning about an upcoming default change; Google libs are warning about dropping 3.8 support.
*   **Fix / prevention:**
    *   Upgrade local Python to ≥3.10 when convenient (this will reduce ecosystem breakage).
    *   Pin pytest-asyncio loop scope explicitly in pytest config when async tests are introduced.

## 9. Wrong v3 ASN baseline from local v2 SQLite (PRD 0005 bridge)

*   **Error message:** v3 DB showed only **1,796 ASN-linked incidents** and many **empty aircraft pages** (e.g. Boeing 747-100 missing deployed-main parity).
*   **Root cause:** PRD 0005 bridged from local v2 SQLite (`data/aircraft_safety.db`) instead of the deployed-`main` scrape/import pipeline. v2 data was incomplete and not equivalent to a fresh ASN scrape.
*   **Fix / prevention:**
    *   Rebuild ASN baseline via `python scripts/scrape_boeing.py`, `python scripts/scrape_airbus.py`, `python scripts/import_data.py` into a **fresh** `data/aircraft_safety_v3.db`.
    *   Reverted PRD 0005 bridge commits (`7653e58`–`d98d16d`); superseded by PRD 0005.1 (`Planning/tasks/0005.1-prd-rebuild-asn-baseline-from-main-scrape.md`).
    *   Never use v2 DB as v3 source of truth — code pipeline is the reference, not stale local SQLite.

## 10. ASN aggregate “family” aircraft pages show 0 incidents after global `asn_url` dedupe

*   **Error message:** (symptom) Search lists aircraft like `Boeing 737 family` or `(all series)` variants with **0 incidents** while specific variants (e.g. `Boeing 737-800`) have full histories.
*   **Root cause:** ASN scrape includes aggregate model rows whose incidents share the same `asn_url` values as specific variants. Import dedupes globally on `asn_url`, so incidents attach to whichever aircraft row imported first — aggregate pages lose all rows.
*   **Fix / prevention:**
    *   Skip aggregate rows at import in `scripts/import_data.py`:
      ```python
      if "(all series)" in lower_model or lower_model.endswith(" family") or " family (" in lower_model:
          continue
      ```
    *   Family rollup (query-time aggregation) is a separate future phase — do not import aggregate pages until rollup exists.

## 11. NTSB docket HTTP 200 with “not released” body is a dead link

*   **Error message:** `The docket for this investigation has not been released`
*   **Root cause:** For foreign-led accredited-rep cases (`*WA*`, `*RA*`, `cm_agency=Other`) and many `DirectorBrief` records, NTSB blocks CAROL and the docket fallback returns HTTP **200** with an empty/unreleased HTML body — not a timing delay; structurally unreleased.
*   **Fix / prevention:**
    *   Use `validate_ntsb_url()` in `app/ingestion/url_builders/ntsb_viability.py` — GET the URL and reject when body contains `"has not been released"`.
    *   Full-corpus audit (2026-05-28): **679** viable working links vs **2970** viable-with-broken-link — gate imports on viability, not HTTP status alone.
    *   Never store docket URLs as `source_url` without passing this check at write time.

## 12. NTSB resolver preferred docket over CAROL when CAROL had public content

*   **Error message:** (symptom) “Details” opened sparse NTSB docket pages instead of richer CAROL investigation detail URLs.
*   **Root cause:** `resolve_ntsb_source_url()` priority ordered docket before CAROL even when bulk `source_data` indicated public CAROL narrative content (`cm_mkey` present, `carol_detail_has_public_content()` true).
*   **Fix / prevention:**
    *   FR-8 fix (commit `6f41ec9`): prefer CAROL detail when public content exists; fall back to docket only when CAROL is blocked (`Other`, `DirectorBrief`).
    *   Add/keep unit test in `tests/test_ntsb_importer.py` asserting CAROL wins over docket for eligible records.

## 13. NTSB PDF API returns JSON error payload with HTTP 200

*   **Error message:** `{"Error":"The case with MKey 0 does not exist.","ErrorCode":0}`
*   **Root cause:** Some NTSB CAROL PDF/report endpoints return HTTP 200 with a JSON error body instead of a PDF — HEAD/status-only checks pass incorrectly.
*   **Fix / prevention:**
    *   Validate response **body** on GET, not just status code.
    *   Treat `"MKey 0"` / `{"Error":` JSON payloads as broken links; do not render or store as `report_url`.
    *   Reference: `Planning/Observations/25_Apr_Observations.md` (DCA90MA019).

## 14. Gemini unit tests must mock `google_genai`, not `genai`

*   **Error message:** `AttributeError: <module 'app.services.gemini'> does not have the attribute 'genai'`
*   **Root cause:** `app/services/gemini.py` imports `google.generativeai as google_genai`; tests that patch `app.services.gemini.genai` target a non-existent attribute.
*   **Fix / prevention:**
    *   Patch `app.services.gemini.google_genai` and set `HAS_GEMINI=True` in tests (`tests/test_gemini.py`).
    *   When dependency missing, `HAS_GEMINI=False` — tests should assert mock/disabled path, not assume library present.

## 15. Empty SQLite database shows misleading “No aircraft found” search UX

*   **Error message:** `No aircraft found matching 'boeing'` (when DB has **0** `Aircraft` rows).
*   **Root cause:** Fresh/empty dev DB — search endpoint works but there is no data; UI does not distinguish “database empty” from “query had no matches”.
*   **Fix / prevention:**
    *   After branch checkout or fresh DB, run scrape + import before manual QA.
    *   Consider dev-only seed or distinct empty-DB message (`Planning/Debugging errors/plan-fix-search-empty-database.md`).
    *   Quick check: `flask shell` → `Aircraft.query.count()`.

## 16. gstack browse / Playwright setup missing on fresh machines

*   **Error message:** Playwright/Chromium not installed; `bun`/`bunx` not on PATH when running browse QA.
*   **Root cause:** gstack browse depends on Playwright browser binaries that are not bundled with the repo; shell PATH may not include bun.
*   **Fix / prevention:**
    *   One-time: `playwright install chromium` and `playwright install chromium-headless-shell`.
    *   Use absolute path to browse binary or ensure `~/.claude/skills/gstack/browse/dist/browse` is on PATH.
    *   Documented in `Planning/sessions/2026-05-27_exhaustive_local_QA_127.0.0.1_5003.md` §1.

## 17. ASN headless automation fails anti-bot parsing; gstack browse succeeds

*   **Error message:** (symptom) Standalone Playwright harness loaded ASN pages but could not extract parseable `Date` / `Owner/operator` fields for bulk verification.
*   **Root cause:** aviation-safety.net serves different or stripped content to generic headless clients vs the gstack browse stack used interactively.
*   **Fix / prevention:**
    *   Use gstack `browse` with throttling for ASN link QA (`scripts/verify_asn_checkset.py`).
    *   Completed run: **194/200 PASS** (strict date+operator match); 1 dead ASN 404, 5 alias/partial-date edge cases documented in QA addendum.
    *   Do not treat failed generic Playwright parses as bad scrape data without retry via browse.

## 18. Raw DeepSeek error strings leak into user-visible AI summary card — **fixed 2026-06-01**

*   **Error message:** UI showed `Authentication Fails, Your api key: ... is invalid` or `Failed to generate summary: Error generating summary: Connection error.`
*   **Root cause:** `generate_summary_background()` wrapped error strings; `summary_card.html` used `| safe`.
*   **Fix / prevention:**
    *   `SUMMARY_UNAVAILABLE_USER_MESSAGE` in `app/services/deepseek.py`; catch `AuthenticationError` / `APIConnectionError`; no exception text to callers.
    *   `app/routes.py` persists only success text or the generic message.
    *   Summary card renders with autoescape (no `| safe`).
    *   Tests: `tests/test_deepseek.py`, `tests/test_summary.py::test_generate_summary_background_stores_safe_message_on_api_failure`.

## 19. SQLite “database is locked” when reading during bulk write

*   **Error message:** `Error: stepping, database is locked (5)`
*   **Root cause:** A long-running bulk write (e.g. `refresh_source_links('FAA_AIDS')` updating 157,342 rows in ~25 min) holds SQLite’s single-writer lock. A concurrent `sqlite3` CLI query or second Flask/import job against the same file blocks or partially fails.
*   **Fix / prevention:**
    *   Treat “database is locked” during backfill as **expected** — wait for the job to finish; check terminal for `DONE in …s`.
    *   Serialize jobs: one writer at a time against `data/aircraft_safety.db` / `data/aircraft_safety_v3.db`.
    *   Find blockers: `lsof "data/aircraft_safety.db"`; kill stale Flask/backfill PIDs before starting a new write.
    *   Observed during PRD 0002 FAA ASIAS backfill (2026-05-24); partial query output (`157342`) may still print before the lock error.

## 20. GitHub push fails — SSH port 22 timeout

*   **Error message:** `ssh: connect to host github.com port 22: Operation timed out`
*   **Root cause:** Local network or firewall blocks outbound SSH on port 22. Commits remain local; this is a transport/routing issue, not a git or repo problem.
*   **Fix / prevention:**
    *   Switch remote to HTTPS: `git remote set-url origin https://github.com/<org>/<repo>.git`
    *   Or configure SSH over port 443 per [GitHub’s SSH-over-HTTPS docs](https://docs.github.com/en/authentication/troubleshooting-ssh/using-ssh-over-the-https-port).
    *   Retry from a network that allows outbound 22.
    *   Observed on `v2-(first-round-of-feedback-from-RJ)` when branch was commits-ahead of origin (2026-05-24 session).

## 21. Cursor sandbox blocks git `index.lock` on Portfolio parent repo

*   **Error message:** `fatal: Unable to create '/Users/Bhavesh/Documents/GitHub/Portfolio/.git/index.lock': Operation not permitted`
*   **Root cause:** Cursor agent sandbox restricts writes to the parent monorepo `.git` directory (`Portfolio/`), even when committing paths under `Aircraft Safety Tracker/`.
*   **Fix / prevention:**
    *   Re-run `git add` / `git commit` with full permissions (`required_permissions: ["all"]` in agent shell).
    *   Or commit from a local terminal outside the sandbox.
    *   Pattern seen repeatedly when agent first used `git_write` only, then succeeded on retry with `all` (PRD 0002–0006 commits).

## 22. pytest cannot import `scripts.audit_ntsb_enrichment` as a package module

*   **Error message:** `ModuleNotFoundError: No module named 'scripts.audit_ntsb_enrichment'`
*   **Root cause:** `tests/test_ntsb_audit_export.py` used `from scripts.audit_ntsb_enrichment import run_audit`. `scripts/` is not importable as a dotted package path for standalone script files on `PYTHONPATH` the way `app.*` modules are.
*   **Fix / prevention:**
    *   Load the script via `importlib.util.spec_from_file_location` pointing at `scripts/audit_ntsb_enrichment.py` (see `tests/test_ntsb_audit_export.py`).
    *   Alternative: invoke audit via subprocess CLI in integration tests instead of importing the script module.
    *   Keep `PYTHONPATH=.` when running pytest from repo root.

## 23. NTSB dedupe unit test false “covered” when both fatalities are zero

*   **Error message:** `assert 1 == 2` (expected `strong_count() == 1`; got `2`) and/or `assert decision.asn_covered is False` (got `True`)
*   **Root cause:** In `score_ntsb_vs_asn()`, when both `ntsb_fatalities=0` and `asn_fatalities=0`, `fatalities_close` becomes `True` (delta ≤ 1). Combined with `date_close=True` on adjacent dates, that yields **2 strong signals** and incorrectly marks the row ASN-covered in a test meant to assert “date only → not covered”.
*   **Fix / prevention:**
    *   Use `ntsb_fatalities=None, asn_fatalities=None` in negative dedupe tests where fatalities should not contribute (`tests/test_ntsb_dedupe.py::test_date_plus_one_day_one_strong_signal_only_not_covered`).
    *   Treat `0/0` fatalities as a valid strong signal in production dedupe — only use `None` when fatality data is genuinely unknown/missing.
    *   Relevant logic: `app/ingestion/dedupe/ntsb_asn.py` lines 81–83.

## 24. JSONL audit export `#` comment lines break naive `json.loads` loops

*   **Error message:** `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`
*   **Root cause:** `data/logs/ntsb_enrichment_audit_rows.jsonl` (PRD 0006.2) begins with `#`-prefixed legend and section headers (`# TO ADD TO DATABASE …`, `# OTHER LINKS …`). A loop that calls `json.loads(line)` on every non-empty line hits comment rows first.
*   **Fix / prevention:**
    *   Skip comment lines: `if line.startswith("#"): continue` before parsing.
    *   Use `count_export_buckets()` / `validate_export_against_report()` in `app/ingestion/audit_export.py` — they already skip `#` lines.
    *   CLI filter: `grep -v '^#' data/logs/ntsb_enrichment_audit_rows.jsonl | jq 'select(.bucket=="viable_with_working_link")'`

## 25. CAROL detail URLs pass HTTP 200 with empty React SPA shell

*   **Error message:** (symptom) CAROL detail page title loads but body is empty; static HTML contains `<main id="root"></main>` with no `NTSB Number` / `Event Date` markers. QA reason code: `carol_empty_spa`.
*   **Root cause:** `carol.ntsb.gov/investigations/detail/{mkey}` is a JavaScript SPA. Static HTTP GET (and headless fetch without rendered content) returns the bootstrap shell only. Pre-FR-12, `validate_ntsb_url()` treated CAROL HTTP 200 as viable — **22 false positives** in the working-link bucket (679 → **657** after re-audit).
*   **Fix / prevention:**
    *   `is_carol_empty_spa_shell()` + reject in `validate_ntsb_url()` when URL is CAROL detail and body lacks content markers (`ntsb number`, `event date`, etc.).
    *   `resolve_ntsb_source_url_checked()` tries CAROL first, then **docket fallback** when CAROL fails.
    *   Manual browser QA (2026-05-31): all 7 Section H sample CAROL URLs rendered blank; 4 moved to docket URL, 3 to broken/no link.
    *   Post-FR-12 working bucket: **0 CAROL URLs** — all 657 use `data.ntsb.gov/Docket/`.
    *   Reference: `.gstack/qa-reports/qa-report-ntsb-working-link-field-check-2026-05-30.md` Section H; PRD 0006.2 FR-12.

## 26. Playwright Chromium CDN download fails in agent sandbox / flaky networks

*   **Error message:** `Error: Download failed: server closed connection. URL: https://cdn.playwright.dev/builds/cft/148.0.7778.96/mac-arm64/chrome-mac-arm64.zip`
*   **Error message (follow-on):** `Failed to install browsers` / `Error: Failed to download Chrome for Testing 148.0.7778.96 (playwright chromium v1223), caused by` `Error: Download failure, code=1`
*   **Root cause:** `playwright install chromium` downloads ~169 MB from CDN; agent sandbox or unstable network drops the connection mid-download. Lock contention when multiple install processes run concurrently also observed.
*   **Fix / prevention:**
    *   Install in project venv from a **local terminal** (not agent sandbox): `cd ".gstack/qa-venv" && python -m playwright install chromium`
    *   Optional isolated browser path: `PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright-ast playwright install chromium`
    *   For NTSB **docket-only** field QA, HTTP fetch in `scripts/verify_ntsb_working_link_sample.py` is sufficient — Playwright only needed for CAROL SPA (now excluded from working bucket post-FR-12).
    *   gstack `browse` binary remains preferred over raw Playwright for site QA when available.

## 27. Audit export test must patch `ntsb.validate_ntsb_url` after FR-12 resolver change

*   **Error message:** `assert report["viable_with_working_link"] == 1` → `assert 0 == 1` in `tests/test_ntsb_audit_export.py::test_run_audit_writes_export_buckets`
*   **Root cause:** Test patched `audit_ntsb_enrichment.validate_ntsb_url`, but FR-12 audit path calls `resolve_ntsb_source_url_checked()` which imports `validate_ntsb_url` from `app.ingestion.url_builders.ntsb`. Mock never applied → all links failed in test.
*   **Fix / prevention:**
    *   Patch at definition site: `patch("app.ingestion.url_builders.ntsb.validate_ntsb_url")`.
    *   When adding new indirection layers, patch where the name is **looked up**, not where the CLI script re-exports it.

## 28. NTSB import auto-creates `Aircraft` rows from raw make/model strings

*   **Error message:** (symptom) Product spot-check finds unfamiliar model names (e.g. `BOEING A75N1(PT17)`, `BOEING 737-7H4`) not on deployed aircraft pages; audit shows **632/657** working rows with `unknown_aircraft=true`.
*   **Root cause:** `resolve_boeing_airbus_aircraft_id()` in `app/ingestion/importers/base.py` does exact `model_name` lookup; on miss it **creates** a new `Aircraft` row. Audit uses lookup-only `find_boeing_airbus_aircraft_id()` — understates write-path catalog bloat. **279** distinct `make_model` strings in the 657 working set vs **97** rows in v3 catalog.
*   **Fix / prevention:**
    *   **Block Task 6.0 bulk import** until NTSB → canonical family mapping exists (PRD 0006.1 FR-6.3 open).
    *   Pilot import on **25 rows** with known `aircraft_id` first; then normalized bulk.
    *   Keep raw NTSB string in `IncidentSource.source_data.cm_vehicles` for audit; map only at `Incident.aircraft_id` assignment.
    *   Stearman/helicopter variants (`A75N1`, `B75N1`, `E75`, `AS350`) need explicit keep/skip policy for Boeing/Airbus portfolio scope.
    *   Reference: product review 2026-05-31; `context/context-2026-05-31.md` §7–§8.

## 29. `NTSBImporter(mapping=Path(...))` fails if only `str` is handled

*   **Error message:** `AttributeError: 'PosixPath' object has no attribute 'get'` (when `_resolve_aircraft_id()` calls `self._mapping.get(make_model)`)
*   **Root cause:** `NTSBImporter.__init__` only loaded the mapping file when `isinstance(mapping, str)`. Tests and CLI pass `pathlib.Path`; the raw `Path` was stored as `_mapping` instead of a loaded `NtsbMakeModelMapping`.
*   **Fix / prevention:**
    *   Accept both: `if isinstance(mapping, (str, Path)): mapping = load_ntsb_make_model_mapping(mapping)`.
    *   Prefer passing loaded `NtsbMakeModelMapping` in unit tests when exercising resolver logic only.
    *   File: `app/ingestion/importers/ntsb_importer.py` (fixed 2026-05-30 session).

## 30. Git commands fail when gstack skill path is a symlink

*   **Error message:** `error: expected submodule path 'Aircraft Safety Tracker/.claude/skills/gstack' not to be a symbolic link`
*   **Root cause:** Portfolio monorepo registers `.claude/skills/gstack` as a git submodule, but the path is a symlink (gstack setup). Git refuses normal operations including `git status`.
*   **Fix / prevention:**
    *   Commit from a local terminal after fixing submodule config, or copy/replace symlink with a real submodule checkout.
    *   Distinct from §21 (`index.lock` sandbox) — this error occurs even with full permissions.
    *   Observed when agent attempted Task 5.18 commit (2026-05-30).

## 31. Bare `python3` missing Flask while pytest interpreter works

*   **Error message:** `ModuleNotFoundError: No module named 'flask'` when running `python3 -c "from app import create_app"`.
*   **Root cause:** System `python3` is not the conda/venv environment where project dependencies (Flask, SQLAlchemy) are installed. `PYTHONPATH=. pytest` uses a different interpreter (`python` on PATH).
*   **Fix / prevention:**
    *   Use the same interpreter as pytest: `python` (anaconda) or project venv, not bare `python3`, for one-off app/DB scripts.
    *   Or activate venv explicitly before `python3` ad-hoc commands.
    *   Observed during dedupe re-pass / catalog overlap checks (2026-05-30).

## 32. Python 3.8 tests need `from __future__ import annotations` for PEP 604 syntax

*   **Error message:** `TypeError: 'type' object is not subscriptable` or parse errors on `list[dict]`, `Path | str`, `Dict[str, Any]` in test/module files at runtime on 3.8.
*   **Root cause:** Local Python 3.8.8 does not treat built-in generics as subscriptable without postponed evaluation of annotations.
*   **Fix / prevention:**
    *   Add `from __future__ import annotations` as first line in new test modules (`tests/test_ntsb_dedupe_repasse.py`, etc.).
    *   Long-term: upgrade to Python ≥3.10 (see §8).
    *   Match pattern already used in `app/ingestion/ntsb_mapping.py`.

## 33. Empty mapping JSONL rejected at load time

*   **Error message:** `ValueError: /path/to/mapping.jsonl: no mapping entries`
*   **Root cause:** `NtsbMakeModelMapping.load()` requires at least one JSON object row after skipping `#` comments. Tests that write an empty mapping file (header only) cannot load.
*   **Fix / prevention:**
    *   For “unmapped string” tests, include a dummy mapped row for a *different* string; assert the target string gets `skip_unmapped`.
    *   Do not use empty JSONL as a stand-in for “no mapping file” — omit `mapping=` on importer instead.
    *   File: `app/ingestion/ntsb_mapping.py` line 54–55.

## 34. FR-12 CAROL→docket fallback increases full re-audit wall clock

*   **Error message:** (symptom) Full link re-audit took **~36–40 min** vs an earlier **~26 min** budget expectation.
*   **Root cause:** `resolve_ntsb_source_url_checked()` tries CAROL viability first, then docket fallback when CAROL fails (`carol_empty_spa`, etc.). Many rows incur **two HTTP fetches** per link check (CAROL GET + docket GET), on top of 0.2s/domain throttle across ~3,649 viable rows.
*   **Fix / prevention:**
    *   Budget **35–40 min** for full `--check-links` re-audit post-FR-12; do not plan 26 min unless skipping CAROL attempt or using persistent link cache.
    *   Post-FR-12 outcome: working bucket **679 → 657**; all 657 working URLs are docket-only.
    *   Log: `data/logs/ntsb_fr12_reaudit_2026-05-31.log`; reference QA report v2.

## 35. NTSB dedupe re-pass does not cross family/variant aircraft pages

*   **Error message:** (symptom) After bootstrap, **210** rows still show `skip_pending_create` or `import` on generic family pages; dedupe does not remove NTSB rows that duplicate ASN incidents on variant pages (e.g. `Boeing 737-300`).
*   **Root cause:** `score_ntsb_vs_asn()` candidate query filters `Incident.aircraft_id == mapped_id` only. Family rollup maps NTSB to new generic `Boeing 737` page; ASN baseline incidents live on variant-specific pages with different `aircraft_id`s.
*   **Fix / prevention:**
    *   Treat as **accepted design** for PRD 0006.3 (FR-20.0.5) unless product requests multi-page dedupe scope.
    *   Bootstrap catalog pages (FR-20.0) helps import/UX but **will not materially shrink** dedupe counts for family rollups.
    *   Files: `app/ingestion/ntsb_dedupe_repass.py`, `app/ingestion/dedupe/ntsb_asn.py`.

## 36. NTSB working-link field QA: docket HTML often lacks make/model

*   **Error message:** (symptom) QA script flags Section D/E — make/model “missing” on live docket page despite correct audit export values.
*   **Root cause:** Public docket landing pages often omit structured make/model; bulk JSON (`cm_vehicles` / `ntsb_records_full.json`) is **richer** than docket HTML. Strict string match against page body fails even when incident is correct.
*   **Fix / prevention:**
    *   Trust bulk JSON + audit export for make/model at import; use docket QA for date/location/link viability only.
    *   Post-FR-12 sample: **12/66** make/model unverifiable from docket HTML; **0** wrong-aircraft matches in sample.
    *   Reference: `.gstack/qa-reports/qa-report-ntsb-working-link-field-check-2026-05-30_v2.md` Sections D/E.

## 37. NTSB mapping gate shipped — bulk import still requires Task 6.0 wiring

*   **Error message:** (symptom) §28 catalog-bloat risk partially addressed; importer without `mapping=` still auto-creates `Aircraft` rows.
*   **Root cause:** PRD 0006.3 Tasks 5.16–5.17 added `data/config/ntsb_make_model_to_aircraft.jsonl`, `NtsbMakeModelMapping`, fail-closed `NTSBImporter(mapping=...)`, dedupe re-pass, and bootstrap tooling — but **no bulk write to v3** until 5.20 pilot / 5.21 bulk (Task 6.0 enrichment mode).
*   **Fix / prevention:**
    *   Require `--mapping` on bulk import CLI (Task 6.7); never run bulk import without mapping file.
    *   Import subset: `dedupe_repasse_status=import` (**396 rows**), not raw 657.
    *   Pilot order: clone DB → bootstrap 15 pages → optional dedupe re-pass → 30-row canary.
    *   Status: **57 pytest** green; awaiting 5.19.3 product sign-off (2026-05-30).

## 38. Dedupe re-pass missed dupes when audit fatalities were null (post-import audit caught 3)

*   **Error message:** (symptom) Post-import audit flagged 3 NTSB/ASN incident duplicates after bulk import; dedupe re-pass had marked those rows `import`.
*   **Root cause:** Audit JSONL had `fatalities: null` for many rows. Dedupe scoring only counts `fatalities_close` when **both** sides are non-null — so only **date** matched (1 signal, not enough). `NTSBImporter` writes `fatalities=parsed.get("fatalities") or 0`, so after import NTSB rows had `fatalities=0`. Post-import audit compared DB rows: date + fatalities both 0 → **2 signals** → duplicate.
*   **Fix / prevention:**
    *   `fatalities_like_import()` in `app/ingestion/dedupe/ntsb_asn.py`; dedupe re-pass uses it so pre-import scoring matches what import will store.
    *   Test: `test_null_fatalities_coerced_like_import_skips_duplicate` in `tests/test_ntsb_dedupe_repasse.py`.
    *   Post-import audit (`audit_post_ntsb_import.py`) remains the safety net for anything still missed.
    *   Remediated on v3: `ATL02LA075`, `FTW96LA269`, `SEA02FA060` via `--remediate`.

## 39. Git commit blocked — gstack path registered as submodule but on-disk symlink

*   **Date & Error:** [2026-05-30] — `error: expected submodule path 'Aircraft Safety Tracker/.claude/skills/gstack' not to be a symbolic link`; `git status` fails.
*   **Root cause:** Index had `gstack` as gitlink (`160000` submodule) from commit `0876a11`, but disk was replaced with `ln -snf ../gstack` → `.claude/gstack` (vendored clone). Git forbids a submodule path being a symlink; sibling skills (`browse`, `qa`, …) are correctly `120000` symlinks.
*   **The Resolution:** `git update-index --force-remove "Aircraft Safety Tracker/.claude/skills/gstack"`, `ln -snf ../gstack` that path, `git add` it (stages `typechange` to `120000`). Do not run `./setup` expecting a submodule checkout at that path — keep one clone at `.claude/gstack`.

## 40. DeepSeek API key is configured in `.env`, not in `config.py`

*   **Error message:** (symptom) User expects to paste the key at `config.py` line `DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')`; summary regeneration still fails with 401 until `.env` is fixed.
*   **Root cause:** `config.py` only **reads** environment variables. `load_dotenv(os.path.join(basedir, '.env'))` loads secrets from `Aircraft Safety Tracker/.env` at app startup. `.env.example` did not list `DEEPSEEK_API_KEY`, which added confusion.
*   **Fix / prevention:**
    *   Add to **`.env`** (gitignored): `DEEPSEEK_API_KEY=sk-...` (get key from DeepSeek console).
    *   **Restart** the Flask process after any `.env` change — env is not hot-reloaded.
    *   On Railway/production, set `DEEPSEEK_API_KEY` in the host environment variables panel.
    *   Never commit API keys into `config.py` or source control.
    *   Observed 2026-06-01 on `GET /aircraft/77/regenerate-summary` with `AuthenticationError: Error code: 401` (see also §6, §18).

## 41. Legacy `example.com` placeholder URLs in DB look like real Details links

*   **Error message:** (symptom) Clicking **Details** opens the IANA placeholder page: *"This domain is established to be used for illustrative examples in documents."* Stored URLs include `https://example.com/asn/1` and `https://example.com/asn/2`.
*   **Root cause:** Early test/import rows used RFC 2606 example domains. `link_schema.is_placeholder_url()` now rejects `example.com` at ingest, and `pick_primary_href()` filters placeholders at render — but **legacy rows** can remain in older SQLite files (e.g. v2 `aircraft_safety.db`).
*   **Fix / prevention:**
    *   On v3 ASN-only baseline, confirm no `example.com` in `Incident.asn_url` / `IncidentSource.source_url` before QA.
    *   Remove bad rows: `DELETE` incidents tied to `source_url LIKE '%example.com%'` (or deactivate `IncidentSource.is_active`).
    *   Do not treat placeholder hosts as broken external links — they are test data, not NTSB/ASN outages.
    *   Reference: branch debrief v2 §1; Boeing 707 debug session (2026-05).

## 42. Family-rollup bulk import placed NTSB incidents on wrong aircraft pages (variant remediation)

*   **Error message:** (symptom) After bulk import, NTSB incidents for variants (e.g. `BOEING 737-8H4`, `BOEING 787-9`) appeared on generic **`Boeing 737`** / **`Boeing 787`** family pages instead of series pages (`Boeing 737-800`, `Boeing 787-9 Dreamliner`, etc.).
*   **Root cause:** Initial `ntsb_make_model_to_aircraft.jsonl` used family rollup targets for many 737/787 suffix strings. Product policy (2026-06) requires **variant series pages** for 737 and 787, plus a dedicated **Airbus Helicopters EC130** page (not EC135).
*   **Fix / prevention:**
    *   Run `scripts/remediate_ntsb_variant_mapping.py` (updates mapping JSONL + moves `Incident.aircraft_id` for existing NTSB sources).
    *   Live run (2026-06): **43** mapping rows patched, **112** incidents moved; report at `data/logs/ntsb_variant_mapping_remediation.json`.
    *   Script recalculates `Aircraft.total_incidents` / fatals on touched pages — verify counts after remediation.
    *   Resolver logic: `app/ingestion/ntsb_variant_resolution.py` (`resolve_boeing_737_series_page`, `resolve_boeing_787_page`, EC130 helpers).
    *   Re-run `scripts/audit_post_ntsb_import.py` after large moves if dupes/orphans are a concern.

## 43. SQLAlchemy `InvalidRequestError` — `joinedload` on `lazy='dynamic'` relationships

*   **Error message:** `sqlalchemy.exc.InvalidRequestError` when applying `joinedload()` to `Incident.sources` (relationship declared `lazy='dynamic'`).
*   **Root cause:** Dynamic relationships return an `AppenderQuery`, not a loaded collection; SQLAlchemy forbids joined eager loading on them. CSV export and list routes that tried `joinedload(Incident.sources)` hit this at query-build time (v2 branch, 2026-04).
*   **Fix / prevention:**
    *   Do not use `joinedload` on `Incident.sources` or `Incident.system_tags` — batch-load with `_load_sources_by_incident_id()` pattern in `app/routes.py`.
    *   For N+1 on export, prefetch sources in a second query keyed by `incident_id`, not per-row `.sources.all()` in a tight loop without caching.
    *   Reference: `Planning/branch-debrief-v2.md` §4 item 8; `Planning/Reviews/Code_Review_Report_4Apr2026.md`.

## 44. `DetachedInstanceError` when ORM objects cross Flask app context / threads

*   **Error message:** `sqlalchemy.orm.exc.DetachedInstanceError: Parent instance <Incident ...> is not bound to a Session`
*   **Root cause:** `Incident` / `Aircraft` instances loaded in one `app.app_context()` (or request) were passed into a background thread or used after `db.session` was closed. Lazy loads then fail (observed twice on v2: 2026-04-26, 2026-05-02).
*   **Fix / prevention:**
    *   Pass **primitive IDs** into `generate_summary_background()` and re-query inside `with app_context():` (pattern in `app/routes.py`).
    *   In templates, avoid touching unloaded relationships on detached instances; eager-load or pass DTOs from the route.
    *   Reference: `Planning/branch-debrief-v2.md` §4 item 9; PRD `0017` aircraft template audit.

## 45. `UNIQUE constraint failed` when `source_record_id` is low-cardinality (e.g. domain only)

*   **Error message:** `UNIQUE constraint failed` on `incident_source` when multiple rows used the same `source_record_id` (e.g. bare domain string shared across incidents).
*   **Root cause:** v2 stored placeholder/catalog keys with insufficient cardinality; second insert for a different incident but same domain violated the unique `(source_type, source_record_id)` constraint (2026-05-03).
*   **Fix / prevention:**
    *   Derive `source_record_id` from an **incident-specific** identifier (NTSB number, ASN wikibase id, FAA AIDS report id) plus a deterministic hash when needed.
    *   Never use bare hostname/domain as the global unique key.
    *   Enforce at import via `link_schema.normalize_link_entry()` before `IncidentSource` insert.
    *   Reference: `Planning/branch-debrief-v2.md` §4 item 5.

## 46. Playwright `browse` fails in Cursor sandbox — `ERR_SYSTEM_ERROR` on CPU detection

*   **Error message:**
    ```text
    error: Failed to get CPU information
    code: "ERR_SYSTEM_ERROR"
    ...
    at .../playwright-core/.../hostPlatform.js:60:50
    ```
*   **Root cause:** gstack `browse` starts a Playwright server that calls `node:os.cpus()` for host platform detection. Cursor’s default agent sandbox blocks or breaks that syscall, so the server never starts (QA skill run 2026-06-01).
*   **Fix / prevention:**
    *   Re-run browse commands with **`required_permissions: ["all"]`** (or from a local terminal outside the agent sandbox).
    *   Prefer repo binary: `.claude/gstack/browse/dist/browse` after `cd .claude/gstack && ./setup`.
    *   Symptom: `[browse] Server failed to start` before any `goto` / screenshot.

## 47. Wrong gstack browse path — `No such file or directory` under `.claude/skills/gstack/`

*   **Error message:**
    ```text
    --: /Users/Bhavesh/Documents/GitHub/Portfolio/Aircraft Safety Tracker/.claude/skills/gstack/browse/dist/browse: No such file or directory
    ```
*   **Root cause:** Skills symlink `.claude/skills/gstack` → `../gstack` points at the skill tree, but the **compiled binary** lives under the vendored clone `.claude/gstack/browse/dist/browse` after `./setup`. QA subagent and early session commands used the skills path literally (2026-06-01).
*   **Fix / prevention:**
    *   `B=".claude/gstack/browse/dist/browse"` (or `~/.claude/skills/gstack/browse/dist/browse` only if globally built).
    *   One-time: `cd "Aircraft Safety Tracker/.claude/gstack" && ./setup && bun run build`.
    *   Clarifies §16 — global `~/.claude/skills/gstack/...` is optional; repo-local path is authoritative for this project.

## 48. gstack `browse` stale `@e` ref after navigation

*   **Error message:** (symptom) `browse attrs @e54` / `click @e54` fails with a **not found** error after `goto`, `wait`, or tab switch; assistant log: *"refs being invalidated due to a load"*.
*   **Root cause:** Element refs (`@eN`) are tied to the last `snapshot`. Any navigation or DOM update invalidates prior refs (`browse/SKILL.md`: *"Refs are invalidated on navigation"*).
*   **Fix / prevention:**
    *   Run `browse snapshot` immediately before `attrs`, `click`, or `select` on `@eN`.
    *   For HTMX filters, prefer stable selectors: `browse select "select[name=type]" "fatal"` (used successfully on `/aircraft/25` QA).
    *   For ASN **Details** links (`target="_blank"`), use `attrs @eN` → `newtab "<href>"` instead of `click` (click may not leave the app tab).

## 49. Request Missing Data — empty submit shows no visible validation (QA)

*   **Error message:** (symptom) After empty submit on `/feedback/request`, page stays on the same URL with **no visible** error messaging (QA ISSUE-002, 2026-06-01).
*   **Root cause:** Server-side `RequestDataForm` has `DataRequired()` on `aircraft_model` and template loops `form.aircraft_model.errors` — so a normal POST should re-render errors. QA used headless **click** on submit without confirming a full POST/CSRF round-trip; possible false negative, but UX gap remains if errors render off-screen or CSRF fails silently.
*   **Fix / prevention:**
    *   Manually verify: empty POST → expect red *"This field is required."* under Aircraft Model (`app/templates/request_data.html`).
    *   If missing: ensure `{{ form.hidden_tag() }}` / CSRF and `method="POST"` intact; add client-side `required` for faster feedback.
    *   browse QA: use `browse fill` + explicit submit, then `browse snapshot` to capture error text.
    *   Reference: `Planning/sessions/2026-05-27_exhaustive_local_QA_127.0.0.1_5003.md` § QA skill review ISSUE-002.

## 50. Stale ASN URL in v3 DB — live page 404 (QA addendum)

*   **Error message:** (symptom) `incident_id=4333` → `https://aviation-safety.net/wikibase/197625` returns **404** on live ASN; DB still has `asn_url` populated.
*   **Root cause:** ASN retired or moved the wikibase page after scrape; import does not periodically re-validate external URLs.
*   **Fix / prevention:**
    *   Treat as **data hygiene**, not app regression — update or clear `Incident.asn_url` for that row.
    *   Wide QA (2026-05-27): **194/200** strict pass; 1 dead link + 5 alias/partial-date edge cases documented in addendum.
    *   Re-verify with `scripts/verify_asn_checkset.py` (gstack browse) before bulk URL fixes.

## 42. FAA brief tail `not_working` while ASIAS homepage was up (retry5 recovery)

*   **Date & Error:** [2026-06-03] — 49 rows `not_working` (`asias_cdn_error` / `http_403` / `asias_backend_timeout`) after retry4; liveness probe true.
*   **Root cause:** retry4 used concurrency 6, 15s timeout, 200–700ms jitter — Akamai/FAA throttled bulk per-record fetches, not missing AIDS IDs.
*   **The Resolution:** retry5 on `faa_aids_brief_retry5_in_2026-06-03.jsonl` with `--concurrency 3 --timeout 25 --jitter-min-ms 500 --jitter-max-ms 1500` → 49/49 `working_brief_report`; `merge_faa_aids_audit_overlay.py merge` + `apply_faa_audit_buckets_to_db.py --apply --overlap-audit`.

## 51. FAA importer unit test still asserts page-12 URL after page-18 migration

*   **Error message:**
    ```text
    AssertionError: assert 'P12_AIDS_RPRT_NBR' in 'https://www.asias.faa.gov/apex/f?p=100:18:::NO::AP_BRIEF_RPT_VAR:20050316X00394'
    ```
    (`tests/test_faa_aids_importer.py::test_parse_valid_boeing_row`)
*   **Root cause:** PRD 0007.2 switched `FAAAIDSImporter` / `build_faa_aids_brief_report_url()` to ASIAS page 18 (`AP_BRIEF_RPT_VAR`); the test was written for page 12 search URLs (`P12_AIDS_RPRT_NBR`).
*   **Fix / prevention:**
    *   Update the assertion to `assert "AP_BRIEF_RPT_VAR" in parsed["source_url"]` (or exact brief template match).
    *   Re-run `PYTHONPATH=. pytest tests/test_faa_aids_importer.py` — full suite was **152 passed, 1 failed** until fixed (2026-06-02 health check).

## 52. FAA audit overlay merge left stale `not_working` despite later retry successes

*   **Error message:** (symptom) Merged brief audit showed **6416/6466** brief while retry4 JSONL had **345** new `working_brief_report` rows for the same IDs; DB apply left **~22** FAA sources inactive that retry files had classified as brief.
*   **Root cause:** Base `*_merged.jsonl` was built from earlier retry passes without overlaying **complete** retry4/gap/retry5 outputs keyed by `source_record_id`. Older `not_working` timestamps stayed in the merged file when retry successes lived only in separate `*_retry4_browserua.jsonl` files.
*   **Fix / prevention:**
    *   Backup base, then: `python scripts/merge_faa_aids_audit_overlay.py merge --base data/logs/faa_aids_url_audit_brief_*_merged.jsonl --overlay data/logs/faa_aids_url_audit_brief_*_retry4_browserua.jsonl ...`
    *   Do **not** blind-concatenate retry1–4 JSONL (retry1 can contain corrupt lines — see §55).
    *   Re-run `apply_faa_audit_buckets_to_db.py --apply --overlap-audit` after merge.
    *   Reference: JOURNAL 2026-06-03 re-merge; `/audit-urls` skill v1.2 overlay section.

## 53. `httpx.ReadTimeout` aborts FAA brief URL experiment under high concurrency

*   **Error message:**
    ```text
    httpx.ReadTimeout: The read operation timed out
    ```
    (wrapped from `httpcore.ReadTimeout: The read operation timed out`)
*   **Root cause:** `scripts/export_faa_aids_report_url_experiment.py --validate --concurrency 24` saturated ASIAS or exceeded default read timeout; `ThreadPoolExecutor` worker raised uncaught timeout and crashed the whole script mid-batch (terminal `132150.txt`, 2026-06-01).
*   **Fix / prevention:**
    *   Use audit-style gentle settings: lower concurrency (3–8), `--timeout 25`, jitter between requests.
    *   Catch per-URL timeouts in worker functions and record `not_working` / `asias_backend_timeout` instead of aborting the batch.
    *   Align with `audit_faa_aids_urls.py` defaults and LEARNINGS proactive §16 for tail retries.

## 54. DeepSeek safe-card fix does not clear legacy `aircraft.ai_summary` error blobs

*   **Error message:** (symptom) UI still shows:
    ```text
    Failed to generate summary: Error generating summary: Error code: 401 - {'error': {'message': 'Authentication Fails, Your api key: ****0749 is invalid', ...
    ```
    after user updated `.env` to a valid key (suffix **8889** on live test).
*   **Root cause:** (1) Old failed generation persisted raw API error text in `aircraft.ai_summary` before §18 hardening. (2) Flask dev server had not restarted — in-memory env still held the old key (`****0749` in error vs new key in `.env`).
*   **Fix / prevention:**
    *   **Restart Flask** after any `.env` change to `DEEPSEEK_API_KEY`.
    *   Regenerate summary or `UPDATE aircraft SET ai_summary=NULL` for affected rows.
    *   Render path: `display_ai_summary()` / `is_legacy_error_summary()` in `app/services/deepseek.py` + `summary_card.html` — hides legacy error-shaped blobs even if DB not cleared yet.
    *   See also §6, §18, §40.

## 55. Interrupted FAA audit JSONL leaves corrupt lines — gap-fill before overlay merge

*   **Error message:** (symptom) retry4 output JSONL missing **5** `source_record_id` rows vs input; merge under-counted brief gate until gap pass.
*   **Root cause:** Long ASIAS audit runs can leave truncated/empty lines or invalid JSON objects in output JSONL (interrupted write or partial flush). Naive `json.loads` loops fail or silently drop rows; blind merge of retry1 file also introduced bad lines (documented in `audit-urls/references/faa-asias.md`).
*   **Fix / prevention:**
    *   `merge_faa_aids_audit_overlay.py --build-gap-input` → re-audit missing IDs → gap JSONL → merge overlays with `tolerant=True` (skips corrupt lines, logs count).
    *   Compare valid `source_record_id` count in retry **input vs output** before trusting gate %.
    *   Complements §24 (`#` comment lines) — this is mid-file corrupt/truncated JSON, not header comments.

## 56. Railway Postgres TRUNCATE deadlock during v3 SQLite push

*   **Date & Error:** [2026-06-14] — `psycopg2.errors.DeadlockDetected: deadlock detected` on `TRUNCATE TABLE` during `push_v3_sqlite_to_postgres.py --apply`.
*   **Root Cause:** Portfolio-v5 gunicorn (or a stray query session) held `AccessShareLock` while the push script tried `AccessExclusiveLock` on truncate — circular wait with another backend.
*   **The Resolution:** Before truncate, run `pg_terminate_backend(pid)` on all other sessions for the database; switched row-by-row inserts to `psycopg2.extras.execute_batch` (500-row pages) — full load ~27s vs 15–30+ min.

## 57. Railway mise build — Python 3.13.1 attestation failure

*   **Date & Error:** [2026-06-14] — `mise ERROR Failed to install core:python@3.13.1: No GitHub artifact attestations found`.
*   **Root Cause:** Railway's Metal builder runs `mise install` using `runtime.txt` (`python-3.13.1`); mise 2026.6+ verifies GitHub attestations and 3.13.1 has none yet.
*   **The Resolution:** Add `Aircraft Safety Tracker/mise.toml` with `[settings] python.github_attestations = false`, commit, and redeploy.
