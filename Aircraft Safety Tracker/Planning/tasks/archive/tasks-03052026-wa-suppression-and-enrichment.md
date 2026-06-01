# Tasks: WA NTSB Suppression Fix & Press Enrichment Run

**Related PRDs:** `0019-prd-source-link-attribution-remediation.md` (Phase 6), `0020-prd-wa-incident-press-enrichment-and-faq.md`
**Status:** `56%` (10/18 subtasks complete, 1/4 phases complete)

**Context:** PRD-0019 Phase 6 was implemented as a body-check against `data.ntsb.gov/Docket/` URLs, but the DB contains no such URLs — all NTSB `IncidentSource` records use `carol.ntsb.gov/investigations/detail/…`, which is a React SPA (not server-rendered). The body-check is dead code that never triggers. As a result, all 6,968 WA-coded NTSB incidents remain `is_active=True`, the enrichment job has been targeting the wrong 197 incidents (old domestic MA records), and no press articles have been stored for the intended WA targets.

| Phase | Status | Notes |
|---|---|---|
| 1. Fix Phase 6 — WA NTSB Suppression | ✅ Complete (8/8) | Event-ID approach; replaces non-functional body-check |
| 2. Run WA Press Enrichment | 2/4 | Requires Phase 1 complete + Google CSE quota reset + **Blocked by PRD-0021** |
| 3. UAT | 0/3 | Manual browser verification on Boeing 747 page |
| 4. Documentation Cleanup | 0/3 | PRD-0019 tasks, PRD-0020 spec, session journal |

---

## Relevant Files

- `app/ingestion/cli.py` — Add `mark-wa-ntsb-inactive` Flask CLI command (new sub-command of `import-data`).
- `app/ingestion/importers/base.py` — Contains the Phase 6 body-check code for `data.ntsb.gov/Docket/` (dead code — leave in place but note it never triggers; no removal required).
- `tests/test_ntsb_importer.py` — Add unit test for event-ID-based WA detection logic.
- `scripts/enrich_wa_incidents.sh` — Daily enrichment runner; run once Phase 1 is complete and CSE quota resets.
- `Planning/Observations/03_May_2026_WA_Phase6_BodyCheck_DeadCode.md` — Observation note documenting why Phase 6 body-check never triggered.
- `Planning/tasks/tasks-0019-prd-source-link-attribution-remediation.md` — Update Phase 6 task statuses to reflect the corrected event-ID approach.
- `Planning/tasks/0020-prd-wa-incident-press-enrichment-and-faq.md` — Correct `source_record_id` spec in requirement 3 (currently wrong: "domain name only").

### Notes

- Run `PYTHONPATH=. pytest tests/ -q` after Phase 1 for regression coverage.
- Google CSE free tier resets at midnight Pacific (~8 am UTC+8). Do not run enrichment until quota resets.
- The `--dry-run` flag on the new CLI command must print count + 5 sample records without writing to DB.
- WA event ID pattern: characters 5–6 (0-indexed) of the NTSB event ID are `WA` for international cases (e.g., `DCA26WA031`, `LAX88WA237`). SQLite LIKE pattern: `'_____WA%'` (5 underscores + `WA` + wildcard).

---

## Tasks

- [x] 1.0 Fix Phase 6 — WA NTSB Suppression via Event-ID Pattern
  - [x] 1.1 Write a short observation note in `Planning/Observations/` documenting why the Phase 6 body-check never triggered: CAROL is a React SPA (JavaScript-rendered), all NTSB `IncidentSource` records use `carol.ntsb.gov` URLs, and there are zero `data.ntsb.gov/Docket/` URLs in the DB.
  - [x] 1.2 Add a `mark-wa-ntsb-inactive` sub-command to `app/ingestion/cli.py` under the existing `import-data` group. The command must: accept `--dry-run` (default) and `--apply` flags; query all `IncidentSource` records where `source_name='NTSB'`, `is_active=True`, and `source_record_id LIKE '_____WA%'`; in dry-run mode print the count and up to 5 sample `source_record_id` values; in apply mode set `is_active=False` on all matched records and commit.
  - [x] 1.3 Run `PYTHONPATH=. flask import-data mark-wa-ntsb-inactive --dry-run` and confirm the reported count is approximately 6,968 and all sample event IDs contain `WA` at position 5–6.
  - [x] 1.4 Run `PYTHONPATH=. flask import-data mark-wa-ntsb-inactive --apply` to mark WA NTSB sources inactive.
  - [x] 1.5 Verify in the DB that the update took effect: query `SELECT COUNT(*) FROM incident_source WHERE source_name='NTSB' AND source_record_id LIKE '_____WA%' AND is_active=1` should return 0.
  - [x] 1.6 Verify the enrichment target set has grown: run `PYTHONPATH=. flask import-data enrich-wa-incidents --dry-run` and confirm the reported target count is substantially larger than the old 197 (expect thousands of WA incidents, minus those that already have another active source).
  - [x] 1.7 Add a unit test to `tests/test_ntsb_importer.py` (or a suitable existing test file) that: creates mock `IncidentSource` rows with WA and non-WA event IDs; calls the suppression logic; asserts only WA rows are marked inactive.
  - [x] 1.8 Run full test suite (`PYTHONPATH=. pytest tests/ -q`) and confirm no regressions.

- [ ] 2.0 Run WA Press Enrichment Against the Correct Target Set
  - [x] 2.1 Wait for Google CSE daily quota to reset (midnight Pacific ≈ 8 am UTC+8). Optionally confirm reset by running a single test query: `PYTHONPATH=. python3 -c "from app.services.web_search import _google_cse_search; print(_google_cse_search('test', tier=3, max_results=1))"` — a non-empty result or no 429 confirms quota is available.
  - [x] 2.2 Run `bash scripts/enrich_wa_incidents.sh` (capped at 90 queries). Check the log at `logs/enrich_wa_incidents.log` for `[FOUND tier=1/2/3]` entries — confirm results are from `avherald.com`, `reuters.com`, `apnews.com`, etc. rather than search engine or portal domains.
  - [ ] 2.3 Repeat daily until enrichment coverage reaches ≥ 70% of WA incidents (PRD-0020 success metric). At 90 queries/day and ~1–3 queries per incident, full coverage of the WA backlog takes approximately 1–3 weeks.
  - [ ] 2.4 After the first successful run with real results, query the DB to confirm `MEDIA` sources are being stored with correct values: `source_name='MEDIA'`, `is_active=True`, `confidence_level='Low'`, `source_record_id` in `event_id:sha1hash` format, `source_url` pointing to a real article URL (not a search engine or homepage).

- [ ] 3.0 UAT — Verify End-to-End on Boeing 747 Page
  - [ ] 3.1 Open the Boeing 747 aircraft incident list in a browser. Confirm that WA-coded incidents no longer show a clickable NTSB link (the `carol.ntsb.gov` link should be hidden because `is_active=False`). Confirm the "No official NTSB docket — why?" note with FAQ link appears for each WA incident.
  - [ ] 3.2 For incidents that received a `MEDIA` source in Phase 2, confirm the press article link (`avherald.com ↗` or `reuters.com ↗`) appears in the incident card and navigates correctly to the article.
  - [ ] 3.3 Confirm that incidents with valid active NTSB sources (domestic US incidents) are unaffected: their NTSB link still appears and the "No official NTSB docket" note does not appear.

- [ ] 4.0 Documentation Cleanup
  - [ ] 4.1 In `Planning/tasks/tasks-0019-prd-source-link-attribution-remediation.md`, update the Phase 6 section: mark tasks 6.1–6.5 as superseded (the body-check implementation is dead code); add a note that Phase 6 was re-implemented in task 1.0 of this document using event-ID pattern matching; update the overall Phase 6 status to reflect completion via the corrected approach.
  - [ ] 4.2 In `Planning/tasks/0020-prd-wa-incident-press-enrichment-and-faq.md`, correct requirement 3's `source_record_id` spec: change "The article's domain name only, e.g. `avherald.com`" to "A unique identifier in the format `event_id:sha1_prefix` (e.g., `DCA26WA031:a3f9c12e`), combining the NTSB event ID with a 16-character SHA-1 prefix of the article URL". Also note in the Phase 2 description that MEDIA links render with the article domain extracted from `source_url` (not from `source_record_id`).
  - [ ] 4.3 Update the session journal at `/Users/Bhavesh/claude_session_journals/2026-05-03_Aircraft-Safety-Tracker.md` with the root-cause finding (CAROL is a SPA, body-check was dead code), the corrected approach (event-ID pattern), and the status of the enrichment run (quota reset needed, Phase 1 must complete first).
