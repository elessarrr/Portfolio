## Status

- Overall Progress: ✅ `100%` (25/25 subtasks complete)
- Current Phase: ✅ Complete

## Relevant Files

- `app/services/web_search.py` - Primary changes: backend priority order, SerpAPI health warnings, subdomain-aware blocklist fix, Tier 3 query prefix.
- `app/ingestion/cli.py` - New `validate-ntsb-links` command; shared deactivation function called by the weekly script.
- `app/ingestion/importers/base.py` - Source of `validate_source_url` and `validate_pdf_url` imported by the new CLI command.
- `scripts/validate_incident_links.py` - Updated to call the new NTSB deactivation pass after its existing validation loop.
- `scripts/com.aircraftsafetytracker.linkvalidation.weekly.plist` - New launchd plist scheduling the link validation script on Sundays at 02:00.
- `scripts/list_scheduled_jobs.py` - New inventory script listing all project-level scheduled jobs.
- `tests/test_web_search_service.py` - Tests for backend priority, health warning messages, and subdomain blocklist fix.

### Notes

- Run tests with `python -m pytest tests/test_web_search_service.py`.
- `engine=duckduckgo` is already set in `_serpapi_search` (line 348) — sub-task 1.3 is a verify-and-comment, not a code change.
- Site-restriction prefixes for Tier 1 (`site:avherald.com`) and Tier 2 (news wire sites) are already applied in `_search_aviation_herald` and `_search_news_wires` — sub-tasks 2.2 and 2.3 are verification only.
- The existing `_SEARCH_ENGINE_DOMAINS` set uses exact-string lookup; `r.bing.com` escapes it. Sub-task 3.1 fixes this with subdomain-aware matching in `_is_candidate_allowed`. Sub-task 3.3 adds `r.bing.com` explicitly as belt-and-suspenders — both changes are required together.
- **Exact-match quote status (task 2.4):** PRD-0021 specifies wrapping `event_id`/`registration` in exact-match quotes, and its tasks file is marked complete — but verify the current working tree before assuming this is done (`git diff HEAD -- app/services/web_search.py` or inspect `_build_aviation_herald_query`). If quotes are absent, task 2.4 applies them; if already present, task 2.4 is a verify-only pass.
- The new plist must be manually loaded via `launchctl load` after creation — this is documented in task 5.6 and is not automated.

## Tasks

- [x] 1.0 Configure SerpAPI as primary backend
  - [x] 1.1 In `_try_all_backends` (`web_search.py` line 456), swap the backend list order so `_serpapi_search` runs before `_google_cse_search`.
  - [x] 1.2 In `_google_cse_search`, add `logger.debug("Google CSE not configured, skipping")` immediately before the silent `return []` on line 288 so missing credentials are visible at debug level.
  - [x] 1.3 Verify `engine=duckduckgo` is already set in `_serpapi_search` params (line 348); add an inline comment: `# switch to engine=google for higher-quality results if needed`.
  - [x] 1.4 Update the `_try_all_backends` docstring to reflect the new priority order: SerpAPI first, Google CSE second.

- [x] 2.0 Tighten SerpAPI query construction per tier
  - [x] 2.1 In `_build_general_query`, prepend `"aviation incident"` to the assembled query string before returning it, so Tier 3 results are biased toward incident coverage.
  - [x] 2.2 Verify `_search_aviation_herald` (line 475) already prefixes `(site:avherald.com OR site:aviation-herald.com)` — no code change needed; confirm with a test assertion.
  - [x] 2.3 Verify `_search_news_wires` (line 487) already includes `(site:reuters.com OR site:apnews.com OR site:bloomberg.com)` — no code change needed; confirm with a test assertion.
  - [x] 2.4 Inspect `_build_aviation_herald_query`, `_build_news_wire_query`, and `_build_general_query` in the current working tree. If `event_id` and `registration` are not already wrapped in double-quotes (e.g. `f'"{event_id}"'`), apply the quoting to all three functions. If quotes are already present, verify and move on — this task is a verify-then-apply step, not a guaranteed code change.

- [x] 3.0 Harden fallback backends: subdomain-aware blocklist and specific health-warning logs
  - [x] 3.1 In `_is_candidate_allowed`, replace the exact-dict-lookup `domain in _SEARCH_ENGINE_DOMAINS` check (line 183) with a subdomain-aware call: `any(_domain_matches(domain, (root,)) for root in _SEARCH_ENGINE_DOMAINS)`. This ensures `r.bing.com`, `m.bing.com`, and similar subdomains are rejected alongside their root. Do NOT add separate filtering inside `_bing_lite_search` or `_duckduckgo_search` — `_is_candidate_allowed` is the single URL-quality gate for all backends.
  - [x] 3.2 In `_serpapi_search`, replace the generic `logger.warning("SerpAPI returned %s: %s", resp.status_code, query)` with status-specific messages: HTTP 401 → `"SerpAPI auth failure (401) — check SERPAPI_API_KEY env var"`; HTTP 429 → `"SerpAPI quota exhausted (429) — daily limit reached, search skipped"`. All other non-200 codes keep the existing generic warning.
  - [x] 3.3 Add `"r.bing.com"` to the `_SEARCH_ENGINE_DOMAINS` set as a belt-and-suspenders complement to 3.1 — both changes are needed together; 3.1 alone covers subdomains via pattern matching, 3.3 makes the common offender explicit in the set for readability.

- [x] 4.0 Implement `validate-ntsb-links` CLI command
  - [x] 4.1 Add a module-level constant `_WA_INCIDENT_RE = re.compile(r'[A-Z]{2,3}\d{2}WA\d{3}', re.IGNORECASE)` near the top of `app/ingestion/cli.py`.
  - [x] 4.2 Add a standalone function `deactivate_broken_ntsb_sources(session, dry_run=False, batch_size=500) -> dict` in `app/ingestion/cli.py` that encapsulates the deactivation logic (query, WA-skip, validate, deactivate, summarize). Returns a summary dict `{skipped_wa, validated, deactivated, report_url_cleared}`. This function is called by both the CLI command and `validate_incident_links.py`.
  - [x] 4.3 Inside `deactivate_broken_ntsb_sources`: query `IncidentSource` where `source_name='NTSB'` and `is_active=True`; for each row, skip if `source_record_id` matches `_WA_INCIDENT_RE` (increment `skipped_wa`).
  - [x] 4.4 For non-WA rows: call `validate_source_url(source.source_url)`; if result is `docket_not_released` or `http_404`, set `source.is_active = False` (increment `deactivated`). Do not deactivate for other error types.
  - [x] 4.5 For non-WA rows with a non-null `report_url`: call `validate_pdf_url(source.report_url)`; if HTTP 404 or error body contains `"MKey 0"`, set `source.report_url = None` (increment `report_url_cleared`). Do not deactivate the source record.
  - [x] 4.6 Commit in batches of `batch_size`; skip writes entirely when `dry_run=True`.
  - [x] 4.7 Register the new CLI command: `@import_data.command('validate-ntsb-links')` with a `--dry-run` flag and `--batch-size` option (default 500). Call `deactivate_broken_ntsb_sources` and print the returned summary dict.
  - [x] 4.8 In `scripts/validate_incident_links.py`, after the existing `validate_and_update` loop completes, import and call `deactivate_broken_ntsb_sources(db.session, dry_run=args.dry_run)` and log its summary.

- [x] 5.0 Wire up weekly scheduled job plist and create `list_scheduled_jobs.py` inventory script
  - [x] 5.1 Create `scripts/com.aircraftsafetytracker.linkvalidation.weekly.plist` modelled on the existing `com.aircraftsafetytracker.weeklyupdate.plist`; set `Label` to `com.aircraftsafetytracker.linkvalidation.weekly`; set `ProgramArguments` to run `scripts/validate_incident_links.py` via the project venv Python; schedule for Sunday (Weekday=0) at 02:00.
  - [x] 5.2 Create `scripts/list_scheduled_jobs.py`; define a `IMPACT_REGISTRY` dict keyed by plist label and/or script basename describing what each job does (e.g. `"com.aircraftsafetytracker.weeklyupdate": "Runs Boeing/Airbus scrapers and data import"`).
  - [x] 5.3 In `list_scheduled_jobs.py`: use `plistlib` to parse every `*.plist` in the `scripts/` directory; extract `Label`, `StartCalendarInterval` (convert to human-readable string e.g. `"Every Monday at 09:00"`), and the first entry of `ProgramArguments`.
  - [x] 5.4 In `list_scheduled_jobs.py`: run `crontab -l` via `subprocess`; filter output lines that reference the project directory path; parse each cron expression into a human-readable string.
  - [x] 5.5 Print a formatted table with columns: `Job Name | Schedule | Script / Command | Impact Description`; use `IMPACT_REGISTRY` for the Impact column, falling back to `"(no description)"` for unlisted jobs.
  - [x] 5.6 Document in the script's docstring that loading a new plist requires: `launchctl load ~/Library/LaunchAgents/<label>.plist` (or the scripts directory path if run from there), and that the plist must be copied to `~/Library/LaunchAgents/` to be active at login.
