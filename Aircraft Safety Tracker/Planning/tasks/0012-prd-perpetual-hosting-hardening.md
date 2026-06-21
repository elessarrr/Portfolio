# Product Requirements Document: 0012 — Perpetual Hosting Hardening

**Project ID:** 0012  
**Created:** 21 June 2026  
**Author:** Product (with CTO)  
**Status:** Draft  
**Branch policy:** Cut new branch from `v5-incorporating-asn-ntsb-faa-links`

---

## 1. Introduction / Overview

### Problem Statement

The app is now live on Railway (Portfolio-v5) with enriched v3 data (ASN + NTSB + FAA, ~12,500 incidents). However two gaps prevent it from being left running indefinitely without attention:

1. **Data goes stale.** There is no automated ingestion — all data is static. NTSB and ASN publish new incident records continuously; without a pipeline the app diverges from reality over time.
2. **AI credits burn on every page load.** The AI Safety Summary is regenerated fresh on each page view, even though the underlying incident data for a given aircraft changes at most once per week. This wastes API credits and adds latency for every visitor.

### Goal

Close out the app so it can be left running for the long term with minimal maintenance cost and minimal cloud spend, while staying reasonably up-to-date with new incident data.

---

## 2. Goals

1. **Automated weekly data refresh** — a scheduled job incrementally fetches new incidents from all three active sources (ASN, NTSB, FAA AIDS) and writes them to the Postgres DB, with automatic retry on transient failures.
2. **Cached AI summaries** — AI Safety Summaries are generated at most once per 7-day window per aircraft, stored in the DB, and served from cache on all subsequent page loads within that window.
3. **Zero-touch operations** — both features work without manual intervention; failures are logged and retried rather than causing noisy alerts.
4. **Minimal Railway cost** — the cron service uses Railway's built-in cron scheduler (no extra paid worker); cached summaries eliminate the majority of DeepSeek API calls.

---

## 3. User Stories

- **As a visitor**, when I load a Boeing 737-800 page, I want to see an AI summary instantly rather than waiting for a fresh API call on every load.
- **As a visitor** returning a month later, I want to see up-to-date incident counts, not data frozen at the deployment date.
- **As the developer/owner**, I want the app to keep itself updated and the AI cost to be near-zero, so I can leave it running indefinitely without touching it.
- **As the developer/owner**, if data ingestion fails one week (e.g. a source is down), I want the app to silently retry and carry on — not crash or require manual intervention.

---

## 4. Functional Requirements

### FR-1: Weekly Ingestion Cron Service

**FR-1.1** — A new Railway Cron Service is added to the Portfolio-v5 Railway project with schedule `0 2 * * 1` (every Monday at 02:00 UTC).

**FR-1.2** — The cron job runs a single Python entrypoint script (`scripts/weekly_ingest.py`) with `PYTHONPATH=.` and `DATABASE_URL` available as environment variables.

**FR-1.3** — The script persists the timestamp of its last successful run in the DB (a new single-row table `ingestion_state`, columns: `id`, `last_run_at` DateTime, `last_run_status` string). On each run it reads `last_run_at` and passes it as the `since` date to each source importer.

**FR-1.4 — NTSB incremental:** Fetch new NTSB Boeing/Airbus records published since `last_run_at` and pass them to the existing `NTSBImporter`. **Note:** The current codebase has no live NTSB API client — `data/raw/ntsb_records_full.json` was a one-time bulk export from the v2 database, not a live API pull. The CAROL web app (`carol.ntsb.gov`) is a JS SPA that rejects static fetches (LEARNINGS §25). Before implementation, confirm whether `data.ntsb.gov` exposes a queryable REST endpoint with a `dateFrom` filter; if not, fall back to NTSB's public bulk data download (Aviation Data Systems page) and diff against existing `source_record_id` values in the DB. Implementation approach to be confirmed during Task 3.0 research phase.

**FR-1.5 — ASN incremental:** Run the existing ASN scrapers (`scrape_boeing.py`, `scrape_airbus.py`) and pass results through `import_data.py`. The importer deduplicates on `asn_url` — only new URLs will create rows. **Note:** The scrapers currently re-scrape all model pages with a 2-second pause between requests; for 100+ Boeing and Airbus models this is a 5–10 minute wall-clock run. This is acceptable for a weekly cron. Do not reduce the inter-request sleep — ASN has blocked scrapers that hit too fast.

**FR-1.6 — FAA AIDS:** FAA AIDS (ASIAS) does not support a reliable incremental API. FAA ingestion is **skipped** from the weekly cron. A comment in `weekly_ingest.py` documents why (ASIAS has no date-range bulk export; manual re-import remains the procedure for FAA refreshes, expected to be very infrequent).

**FR-1.7 — Retry logic:** If any source importer raises an exception, the script catches it, logs the error with traceback, and retries that source up to **3 times** with a 60-second delay between attempts. If all 3 retries fail, the source is skipped for this run (other sources still proceed). The overall run is marked `partial` in `ingestion_state`.

**FR-1.8 — Success state:** After all sources complete (or are skipped after retries), `ingestion_state.last_run_at` is updated to `NOW()` and `last_run_status` is set to `ok` or `partial`.

**FR-1.9 — Logging:** All output goes to stdout (Railway logs). Each run logs: start time, source being processed, records fetched, records inserted (new), records skipped (duplicate), records skipped due to unmapped make/model (NTSB), errors, and total wall-clock time. The count of NTSB unmapped skips must be logged prominently — new NTSB records may use make/model strings not in `data/config/ntsb_make_model_to_aircraft.jsonl` (built once during PRD 0006) and will be silently dropped by the importer without this log signal.

---

### FR-2: AI Summary Caching

**FR-2.1** — Add a new nullable `summary_generated_at` column (DateTime) to the `aircraft` table via an Alembic migration.

**FR-2.2** — When an aircraft detail page is loaded, the app checks: is `ai_summary` non-null **and** `summary_generated_at` is within the past **7 days**? If yes → serve the cached `ai_summary` directly, skip the AI API call.

**FR-2.3** — If the cache is stale (older than 7 days) or absent (`ai_summary` is null), the app generates a fresh AI summary, saves it to `aircraft.ai_summary`, and sets `summary_generated_at = NOW()`.

**FR-2.4** — The existing **"Regenerate"** button on the aircraft page bypasses the cache unconditionally — it always triggers a fresh API call and updates both `ai_summary` and `summary_generated_at`.

**FR-2.5** — If the AI API call fails (timeout, 401, network error), the app falls back gracefully: if a cached summary already exists (even if stale) it is displayed with no error shown to the user. If no cached summary exists, the existing "unavailable" placeholder behaviour applies.

**FR-2.6** — The 7-day TTL is configurable via an environment variable `AI_SUMMARY_TTL_DAYS` (default: `7`). No UI is needed for this setting.

---

### FR-3: Smoke Validation

**FR-3.1** — After the ingestion cron completes, the script logs the updated row counts for `aircraft`, `incident`, and `incident_source` tables so diffs are visible in Railway logs.

**FR-3.2** — A manual smoke check is documented (not automated): after first cron run, confirm `last_run_at` is set in DB and at least one new incident was inserted.

---

## 5. Non-Goals (Out of Scope)

- **FAA AIDS incremental ingestion** — ASIAS has no viable date-range API; excluded from weekly cron.
- **Backfilling historical gaps** — the cron only fetches records newer than `last_run_at`; it will not retroactively fill gaps from before deployment.
- **AI batch pre-generation** — we do not proactively regenerate all 153 aircraft summaries on a schedule; summaries are lazily refreshed on first page visit after TTL expires.
- **Airline-level views** — see Optional Enhancements.
- **Additional manufacturers (Embraer, COMAC)** — see Optional Enhancements.
- **Email/webhook failure alerts** — failures are logged only; no external notification channel.
- **Dashboard for ingestion health** — no UI for monitoring cron status.

---

## 6. Design Considerations

No UI changes required for the ingestion pipeline.

For AI caching, the aircraft detail page (`app/templates/aircraft.html`) already has the AI summary card. No template changes are needed — the route simply passes the cached `ai_summary` string as before. The "Regenerate" button already posts to a route; that route should set `bypass_cache=True` when calling the summary service.

---

## 7. Technical Considerations

### Ingestion cron

- **Railway Cron Service:** Add a new service in the Railway project. Set **Source** to the same GitHub repo/branch as Portfolio-v5, **Root Directory** to `Aircraft Safety Tracker`, and **Start Command** to `PYTHONPATH=. python scripts/weekly_ingest.py`. Set **Schedule** to `0 2 * * 1`.
- **Shared DB:** The cron service and the web service share `DATABASE_URL` pointing to Postgres-cYEh. Railway injects this automatically if you use the `${{Postgres-cYEh.DATABASE_URL}}` reference.
- **`ingestion_state` table:** Created via an Alembic migration (one row, upserted on each run). Alternatively a simple JSON file persisted to a Railway volume works, but DB is simpler and already available.
- **Existing importers:** `app/ingestion/importers/ntsb_importer.py` (NTSB), `scripts/import_data.py` (ASN) — call these directly from `weekly_ingest.py`; no changes to their core logic.
- **NTSB data source — requires research (Task 3.0):** There is currently no live NTSB API client in the codebase. The existing `ntsb_records_full.json` was a one-time bulk export. Task 3.0 must first confirm whether `data.ntsb.gov` provides a REST endpoint with date-range filtering, or whether a different incremental approach is needed (e.g. periodic bulk download + diff on `cm_ntsbNum`). Do not assume CAROL web app is queryable — it is a JS SPA.
- **NTSB make/model mapping:** The mapping file `data/config/ntsb_make_model_to_aircraft.jsonl` was built once during PRD 0006. New NTSB records with unrecognised make/model strings will be skipped by `NTSBImporter` (`skipped_unmapped` list). The cron must log this count; a maintenance task to extend the mapping may be needed periodically.

### AI summary caching

- **Alembic migration:** `flask db migrate -m "add summary_generated_at to aircraft"` + `flask db upgrade`.
- **Service layer change:** In `app/services/deepseek.py` (and/or `gemini.py`), wrap the `generate_summary()` call: check `aircraft.summary_generated_at` before calling the API.
- **`AI_SUMMARY_TTL_DAYS`:** Read via `os.environ.get('AI_SUMMARY_TTL_DAYS', '7')`.
- **TDD note:** Write failing tests for cache hit / cache miss / expired cache / regenerate bypass before implementing.

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| New incidents appear in app within 7 days of NTSB/ASN publication | ✅ after first successful cron run |
| AI API calls per week (steady state, no new visitors) | ~0 (all served from cache) |
| AI API calls per week (active visitors, 153 aircraft, first load after TTL) | ≤ 153 (one per aircraft per week maximum) |
| Cron job mean runtime | < 5 minutes |
| App uptime / behaviour when cron fails | Unaffected — web service has no dependency on cron |

---

## 9. Optional Enhancements (Future Scope)

These are **not** in scope for this PRD. Document here for future reference based on demo feedback.

### OE-1: Additional Manufacturer Coverage

Expand the ASN scraper and ingestion pipeline to include manufacturers beyond Boeing and Airbus. Candidates from demo feedback:

- **Embraer** (E-jets: E170, E175, E190, E195; ERJ series)
- **COMAC** (C919; ARJ21)
- **ATR** (ATR 42, ATR 72)
- **Bombardier** (CRJ series, Q400)

Technical notes:
- ASN has pages for all of these; `scrape_boeing.py`/`scrape_airbus.py` are templates that can be adapted.
- NTSB CAROL covers all US-registered aircraft regardless of manufacturer — existing importer already handles any make/model; the mapping JSONL would need extending.
- DB schema supports arbitrary manufacturers — no schema changes required.

### OE-2: Airline / Operator Filter View

Allow users to filter incidents by airline/operator (e.g. "Singapore Airlines", "Emirates") and see all incidents involving that operator across all aircraft types.

Technical notes:
- `Incident` rows already store an `operator` field (populated from ASN/NTSB source data where available).
- Requires: (a) a new `/operator/<name>` route, (b) an operator index/search page, (c) data quality pass to normalise operator name strings (many variants: "SIA", "Singapore Airlines", "Singapore Airlines Ltd").
- UI: add an "Operator" tag on the incident list that links to the operator view.
- Complexity: operator name normalisation is the hard part; a simple fuzzy-match or curated alias table would be needed before this is useful.

---

## 10. Open Questions

1. **NTSB live API availability:** Does `data.ntsb.gov` expose a REST endpoint that supports `dateFrom` filtering for incremental queries? Or is the only public option a full bulk download + local diff? This is the critical blocker for Task 3.0 and must be researched before implementation begins.
2. **NTSB make/model mapping maintenance:** New NTSB records will likely have make/model strings not in the current mapping file. Is it acceptable to silently skip them (log only), or should the cron fail loudly when unmapped count exceeds a threshold (e.g. > 10 new unknowns)?
3. **ASN scrape acceptable use:** The weekly full re-scrape of all Boeing/Airbus models takes 5–10 minutes with a 2s inter-request delay. Is this within ASN's acceptable use policy for a portfolio project? Alternative: scrape only the first (most recent) page per model and rely on `asn_url` dedupe to skip already-imported rows.
4. **Railway cron billing:** Railway Cron Services are billed like regular services. Confirm the cron process exits after completing (Railway stops billing on process exit) and is not kept alive idle between runs.
5. **`ai_summary` cold-start:** 153 aircraft with null summaries = up to 153 DeepSeek calls in the first week as pages are visited. Acceptable? Or add a one-time batch pre-generation step at deploy time?
