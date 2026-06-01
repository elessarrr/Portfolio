# Tasks: WA Incident Press Enrichment & Investigation FAQ (PRD-0020)

**PRD:** `0020-prd-wa-incident-press-enrichment-and-faq.md`
**Status:** `100%` (29/29 subtasks complete, 5/5 phases complete)

| Phase | Status | Notes |
|---|---|---|
| 1. Press Article Enrichment Job | ✅ Complete (13/13) | Full-suite gate passed (`PYTHONPATH=. pytest tests/ -q`: 222 passed) |
| 2. Template: MEDIA Link Display | ✅ Complete (2/2) | Full-suite gate passed (`PYTHONPATH=. pytest tests/ -q`: 222 passed) |
| 3. Template: FAQ Link on WA Incidents | ✅ Complete (5/5) | Full-suite gate passed (`PYTHONPATH=. pytest tests/ -q`: 222 passed) |
| 4. FAQ Page (`/faq`) | ✅ Complete (6/6) | Route tests added (`tests/test_routes.py`) and full-suite gate passed |
| 5. Site Navigation | ✅ Complete (3/3) | FAQ link integrated in nav + footer with integration coverage and full-suite gate pass |

---

## Relevant Files

- `app/models.py` — `IncidentSource` model (`source_name='MEDIA'`, `is_active`, `confidence_level`, `source_data`).
- `app/routes.py` — Add new `GET /faq` route; no changes needed for enrichment display.
- `app/ingestion/cli.py` — ✅ Contains `flask import-data enrich-wa-incidents` CLI command (already built).
- `app/services/web_search.py` — ✅ `WebSearchService` now supports Google CSE as primary backend (before SerpAPI).
- `scripts/enrich_wa_incidents.sh` — Daily WA enrichment runner script (`--max-queries 90`) with logging.
- `scripts/com.aircraftsafetytracker.wa-enrichment.daily.plist` — launchd schedule config (daily 02:00) for WA enrichment runner.
- `app/templates/components/incident_list.html` — Add FAQ link note for WA incidents with inactive NTSB source.
- `app/templates/components/global_incident_list.html` — Same FAQ link note as above.
- `app/templates/faq.html` — New template for the FAQ page.
- `app/templates/base.html` — Add FAQ link to site navigation.
- `tests/test_web_search_service.py` — ✅ Existing WebSearchService tests passing; extend for Google CSE backend in 1.12.
- `tests/test_routes.py` — Add test for `/faq` route response.
- `tests/test_source_links.py` — Add tests for FAQ link rendering in templates.

### Notes

- **197 target incidents**, up to **3 searches each** = **591 searches worst-case**. Google CSE free tier is 100 queries/day → fully enriched in ~6 days at 100/day (realistically 3–4 days if ~50% are found in Tier 1).
- **Aviation Herald's own site search is broken** — it returns the same static homepage content regardless of query. Tier 1 must use `site:avherald.com` via Google CSE, not a direct query to AH's search endpoint.
- **Search backend priority:** Google CSE (primary, 100/day free) → SerpAPI (secondary, 100/month free) → DuckDuckGo HTML (tertiary, works from home IPs, Cloudflare-blocked from servers).
- **Enrichment job is already built and idempotent** — re-running skips incidents that already have a `MEDIA` source.
- **Scheduler config (Phase 1.13):** Added `scripts/enrich_wa_incidents.sh` + `scripts/com.aircraftsafetytracker.wa-enrichment.daily.plist` (daily 02:00). After backlog reaches zero, switch plist `StartCalendarInterval` to weekly.
- Run `PYTHONPATH=. pytest tests/ -q` after each phase for regression coverage.
- Use `PYTHONPATH=. .venv/bin/flask import-data enrich-wa-incidents --dry-run` to preview targets without writing to DB.

## Tasks

- [ ] 1.0 Implement Press Article Enrichment Background Job
  - [x] 1.1 Create Flask CLI command `flask import-data enrich-wa-incidents` in `app/ingestion/cli.py`
  - [x] 1.2 Build `WebSearchService` in `app/services/web_search.py` with tiered search (AH → news wires → general) and multi-backend support (SerpAPI → Bing Lite → DuckDuckGo)
  - [x] 1.3 Implement target identification: incidents with `source_name='NTSB'`, `is_active=False`, no other active `IncidentSource`
  - [x] 1.4 Implement tiered search execution (Tier 1: `site:avherald.com`, Tier 2: news wire domains, Tier 3: general)
  - [x] 1.5 Validate found URLs via HTTP GET before storing
  - [x] 1.6 Store valid articles as `IncidentSource` rows with `source_name='MEDIA'`, correct `source_data` JSON
  - [x] 1.7 Implement idempotency: skip incidents already having a `MEDIA` source
  - [x] 1.8 Implement completion logging (totals by tier, skipped, not found)
  - [x] 1.9 Write unit/integration tests for `WebSearchService` (27 tests passing)
  - [x] 1.10 Add **Google Custom Search API** backend to `app/services/web_search.py` as the new primary backend — reads `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_CX` from environment; insert before SerpAPI in the `_try_all_backends()` priority list
  - [x] 1.11 Add `--max-queries` flag to the `enrich-wa-incidents` CLI command so the daily cron can cap at 90 queries to stay within the free tier (`PYTHONPATH=. .venv/bin/flask import-data enrich-wa-incidents --max-queries 90`)
  - [x] 1.12 Extend `tests/test_web_search_service.py` to cover the Google CSE backend (mock API responses for success, quota-exceeded, and missing-key cases)
  - [x] 1.13 Configure daily cron to run `flask import-data enrich-wa-incidents --max-queries 90` until all 197 incidents are enriched, then switch to weekly for new incidents

- [ ] 2.0 Update Incident List Templates to Display MEDIA Source Links
  - [x] 2.1 Verify that `incident_list.html` and `global_incident_list.html` correctly render `MEDIA` `IncidentSource` entries without special styling.
  - [x] 2.2 Ensure `MEDIA` links open in the same tab (default behavior).

- [ ] 3.0 Implement FAQ Link on WA Incidents in Templates
  - [x] 3.1 Modify `incident_list.html` to include Jinja2 logic to detect WA incidents (inactive NTSB source, no active NTSB source).
  - [x] 3.2 Render the "No official NTSB docket — [why?](/faq#international-investigations)" note for identified WA incidents.
  - [x] 3.3 Apply subtle styling to the FAQ note (e.g., small grey text).
  - [x] 3.4 Apply the same logic and rendering to `global_incident_list.html`.
  - [x] 3.5 Write unit/integration tests to verify the FAQ link appears only for appropriate WA incidents.

- [ ] 4.0 Create FAQ Page (`/faq`)
  - [x] 4.1 Add a new route `@bp.route('/faq')` in `app/routes.py` to render the FAQ page.
  - [x] 4.2 Create a new template file `app/templates/faq.html`.
  - [x] 4.3 Populate `faq.html` with the "International Investigations" section, including the ICAO Annex 13 explanation and the "docket not released" permanence.
  - [x] 4.4 Populate `faq.html` with the table of national aviation investigation authorities, ensuring all external links open in a new tab (`target="_blank" rel="noopener noreferrer"`).
  - [x] 4.5 Ensure the FAQ page matches existing site styling (Tailwind CSS).
  - [x] 4.6 Write unit tests for the new `/faq` route.

- [x] 5.0 Integrate FAQ Page into Site Navigation
  - [x] 5.1 Modify `app/templates/base.html` to add a link to the `/faq` route in the site navigation (e.g., header or footer).
  - [x] 5.2 Ensure the navigation link is discoverable and consistent with existing navigation elements.
  - [x] 5.3 Write integration tests to verify the FAQ link is present and functional in the navigation.
