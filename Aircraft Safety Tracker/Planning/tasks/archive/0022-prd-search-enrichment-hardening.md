# PRD: Search Enrichment Hardening (SerpAPI-First)

## 1. Introduction/Overview

The `enrich-wa-incidents` pipeline enriches NTSB WA-coded incidents with press articles via paid search backends. Currently the pipeline is non-functional in two ways: the primary backends (Google CSE, SerpAPI) are auth-failing or returning quota errors, and the fallback backends (Bing Lite, DuckDuckGo) pass junk search-engine root URLs as article candidates. Separately, NTSB source records for broken dockets (`docket_not_released`) and missing report PDFs (HTTP 404) are never deactivated, so they persist as stale active records in the DB.

This PRD hardens the enrichment pipeline by making SerpAPI the primary paid backend with tighter aviation-specific queries, making Google CSE optional (skipped when unconfigured), adding operator-facing backend health warnings, filtering out search-engine root URLs from fallback results, and introducing a CLI job that validates and deactivates broken NTSB source links.

## 2. Goals

* **SerpAPI-first:** SerpAPI is the single reliable paid backend; the pipeline functions end-to-end when a valid SerpAPI key is present.
* **Better query precision:** SerpAPI queries return aviation-incident-specific articles rather than generic web results or search-engine pages.
* **Graceful CSE opt-out:** Google CSE is silently skipped when its env vars are absent; no errors, no retries.
* **Clean fallback results:** Bing Lite and DuckDuckGo never surface search-engine root/result-page URLs as article candidates.
* **Actionable operator logs:** When a paid backend returns an auth/quota error, the log message tells the operator exactly which env var to check.
* **DB hygiene for NTSB links:** Broken NTSB docket and report PDF links are detected and marked `is_active=False` by a repeatable CLI job.

## 3. User Stories

* **As the system operator**, I want to run `enrich-wa-incidents` with a valid SerpAPI key and get relevant press articles attached to incidents, without needing a separate Google CSE account.
* **As the system operator**, I want clear log output when SerpAPI returns a 401 or 429, so I know immediately whether it is a bad key or an exhausted quota.
* **As the system operator**, I want to run a single CLI command that scans all active NTSB sources, tests each link, and deactivates the broken ones — so the DB reflects current NTSB availability.
* **As a developer**, I want the fallback search backends to never return homepage or search-results-page URLs as article candidates, so the validation layer is not doing unnecessary work on junk inputs.

## 4. Functional Requirements

1. **SerpAPI as primary paid backend:** `_serpapi_search` must be invoked first in the backend priority list when `SERPAPI_API_KEY` is present. Google CSE may remain in the list but must execute after SerpAPI.
2. **SerpAPI engine:** All SerpAPI calls must use `engine=duckduckgo`. This is the default for cost efficiency; it can be switched to `engine=google` in a later pass if result quality is insufficient.
3. **Google CSE opt-out:** If `GOOGLE_CSE_API_KEY` or `GOOGLE_CSE_CX` is not set, `_google_cse_search` must log a single debug-level message (`"Google CSE not configured, skipping"`) and return an empty list immediately. No exception, no error log.
4. **SerpAPI query tightening — Tier 1 (Aviation Herald):** The query sent to SerpAPI for Tier 1 must include `site:avherald.com` or `site:aviation-herald.com` as a site restriction, plus the exact-match `event_id` (already quoted per PRD-0021).
5. **SerpAPI query tightening — Tier 2 (news wires):** The Tier 2 query must include `(site:reuters.com OR site:apnews.com OR site:bloomberg.com)` as a site restriction.
6. **SerpAPI query tightening — Tier 3 (general):** Tier 3 must prepend `aviation incident` to the query to bias results toward incident coverage rather than generic pages.
7. **Backend health warning — SerpAPI 401:** When SerpAPI returns HTTP 401, the logger must emit a `WARNING`-level message: `"SerpAPI auth failure (401) — check SERPAPI_API_KEY env var"`.
8. **Backend health warning — SerpAPI 429:** When SerpAPI returns HTTP 429, the logger must emit a `WARNING`-level message: `"SerpAPI quota exhausted (429) — daily limit reached, search skipped"`.
9. **Fallback URL filtering:** The existing `_is_candidate_allowed` function must be updated to use subdomain-aware matching for the `_SEARCH_ENGINE_DOMAINS` set (currently an exact-string dict lookup that misses subdomains like `r.bing.com`). The fix must replace the exact lookup with a `_domain_matches`-style check so that any subdomain of a blocked root (e.g. `r.bing.com`, `m.bing.com`) is also rejected. Do not add separate filtering inside `_bing_lite_search` or `_duckduckgo_search` — the `_is_candidate_allowed` gate is the single point of URL-quality control for all backends and must remain so.
10. **NTSB link validation CLI command:** A new command `flask import-data validate-ntsb-links` must iterate all `IncidentSource` rows where `source_name='NTSB'` and `is_active=True`, skipping any row whose `source_record_id` matches the WA-incident pattern (contains `WA` as a coded segment, e.g. `DCA16WA084`). For non-WA rows, it calls `validate_source_url` on each `source_url` and sets `is_active=False` for any row returning `docket_not_released` or `http_404`. It must log a summary count of records skipped (WA), validated, and deactivated.
11. **NTSB report PDF validation:** The same `validate-ntsb-links` command must also test `report_url` where non-null, using `validate_pdf_url`, and set `report_url=None` (not deactivate the source) where the PDF returns HTTP 404 or `"MKey 0"`.
12. **Dry-run mode:** `validate-ntsb-links` must support a `--dry-run` flag that logs what would be changed without writing to the DB.
13. **Weekly scheduled run:** `validate-ntsb-links` must be integrated into the existing `scripts/validate_incident_links.py` weekly job as an additional validation pass. The updated script must call the NTSB-specific checks after the existing source URL / report URL validation loop. The recommended launchd schedule (Sundays at 02:00, matching the existing plist comment in the script header) must be documented, and a new launchd plist `scripts/com.aircraftsafetytracker.linkvalidation.weekly.plist` must be created to wire it up — mirroring the structure of the existing `com.aircraftsafetytracker.weeklyupdate.plist`.
14. **Scheduled jobs inventory script:** A new script `scripts/list_scheduled_jobs.py` must be created that, when run from the project root, prints a human-readable table of all scheduled jobs configured for this project. It must cover: (a) all `.plist` files in the `scripts/` directory, parsing label, schedule (converted to plain English, e.g. "Every Monday at 09:00"), and the command/script it runs; (b) any `crontab -l` entries whose command path references this project directory. Output columns: `Job Name | Schedule | Script / Command | Impact Description`. The `Impact Description` column must be populated from a hardcoded registry dict inside the script keyed by plist label or script basename.

## 5. Non-Goals (Out of Scope)

* **Removing Google CSE code:** The CSE backend is retained; this PRD only gates it on env var presence.
* **Aircraft card UI rendering:** Suppressing broken links in the UI is handled in PRD-0023.
* **New search backends:** No new third-party services are added in this PRD.
* **Automatic SerpAPI key rotation:** Key management is operational, not a code concern.
* **LLM-based query rewriting:** Query tightening is rule-based only.

## 6. Design Considerations

* The `validate-ntsb-links` command should batch DB writes (e.g., commit every 500 rows) to avoid long-running transactions on large datasets (82,664 NTSB records).
* Backend health warnings should include the failed HTTP status and the relevant env var name in a single log line so operators can triage without reading code.

## 7. Technical Considerations

* **Exact-match quoting dependency:** PRD-0021 specifies wrapping `event_id` and `registration` in exact-match quotes in the query builders. Verify this is applied in the current working tree before treating reqs 4–6 as complete. The current `_build_aviation_herald_query`, `_build_news_wire_query`, and `_build_general_query` functions should be inspected — if quotes are absent, applying them is in-scope for this PRD as part of the query-tightening work.
* **SerpAPI engine parameter:** Defaulting to `engine=duckduckgo` for cost efficiency. If Tier 1/2 recall is poor after initial deployment, switch to `engine=google` — this is a one-line change in `_serpapi_search` params.
* **`_is_candidate_allowed` gate:** Requirement 9's subdomain-aware fix must be applied to `_is_candidate_allowed`, not to the individual backend functions. This is the single URL-quality gate for all backends; keeping the logic centralised there avoids divergence between fallback and paid-backend filtering behaviour.
* **NTSB validation batching:** The existing `validate_source_url` function uses an HTTP client with timeouts; the CLI job must not run requests in parallel to avoid rate-limiting by NTSB servers.

## 8. Success Metrics

* **SerpAPI Tier 1 hit rate:** At least one validated Aviation Herald article returned per 10 consecutive `enrich-wa-incidents` runs (sampled over incidents with known press coverage).
* **Zero junk fallback candidates:** `_bing_lite_search` and `_duckduckgo_search` return zero URLs matching the search-engine domain blocklist, verified by unit tests.
* **NTSB validation coverage:** `validate-ntsb-links` processes all 82,664 active NTSB source rows without error; deactivated count is logged and non-zero (confirming the job runs correctly).
* **Actionable log output:** Operator running `enrich-wa-incidents` with a misconfigured SerpAPI key sees a WARNING-level message within the first enrichment attempt, not a generic exception.

## 9. Open Questions

_All original open questions resolved:_

* **SerpAPI engine:** Use `engine=duckduckgo` for now; switch to `engine=google` if recall is poor.
* **NTSB validation frequency:** Integrate into the existing `validate_incident_links.py` weekly job; create a new launchd plist (`com.aircraftsafetytracker.linkvalidation.weekly.plist`) to schedule it on Sundays at 02:00.
* **WA docket suppression:** Yes — `validate-ntsb-links` must skip WA-coded sources to avoid hammering known-unreleased dockets.
