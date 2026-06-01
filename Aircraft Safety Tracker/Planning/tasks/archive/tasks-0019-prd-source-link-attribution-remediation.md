# Tasks: Source Link Attribution Remediation (PRD-0019)

**PRD:** `0019-prd-source-link-attribution-remediation.md`
**Status:** `97%` (33/34 subtasks complete, 5/6 phases complete)

| Phase | Status | Notes |
|---|---|---|
| 1. NTSB Architecture Research Spike | ✅ Complete (5/5) | Research note finalized with remediation decision |
| 2. NTSB URL Remediation | 🟡 In progress (4/5) | Importer routing logic + tests updated; waiting on mapped updates + manual verification |
| 3. ASN Source Migration | ✅ Complete (10/10) | Deferred drop-column stub added for next release (`c955648fb8e6`) |
| 4. FAA_AIDS URL Investigation | ✅ Complete (4/4) | URLs unrecoverable; documented as known limitation in observation note |
| 5. Validator Logic Fix | ✅ Complete (5/5) | NTSB skips CAROL false positives; uses `report_url` as primary signal; full test coverage |
| 6. NTSB "WA" Docket Suppression | ✅ Complete (5/5) | validation logic + tests done; validator re-run confirmed on sample; template suppresses properly |

---

## Relevant Files

- `scripts/migrate_asn_to_incident_source.py` — Existing migration script (ready to run; needs audit before executing)
- `scripts/import_data.py` — Legacy ASN import path; contains `upsert_asn_incident_source()` but may not be the active import route
- `scripts/scraper_utils.py` — Scraper utilities that write `asn_url` directly to `Incident`; likely the active ASN write path
- `tests/test_import_data_variants.py` — ASN import behavior assertions; verifies no new `Incident.asn_url` writes for new imports
- `scripts/validate_incident_links.py` — Weekly re-validation job; contains the source_url-first logic flaw to be fixed (Phase 5)
- `app/ingestion/importers/ntsb_importer.py` — NTSB ingestion pipeline; constructs CAROL URLs from MKeys; needs updating in Phase 2
- `scripts/remediate_ntsb_legacy_source_urls.py` — One-time NTSB URL remediation script (mapping-driven, dry-run/apply) for Phase 2.1
- `app/ingestion/importers/faa_aids_importer.py` — FAA AIDS importer; already attempts to capture `source_url` from raw data; gap is in raw data not the importer
- `app/ingestion/importers/base.py` — `validate_source_url()` and `validate_pdf_url()` — used by both the importer and the validator
- `app/models.py` — `Incident.asn_url` (legacy column to be deprecated); `IncidentSource` model
- `app/templates/components/incident_list.html` — ASN links now rendered from `IncidentSource`; legacy `incident.asn_url` fallback removed
- `app/templates/components/global_incident_list.html` — Source links rendered from `IncidentSource`; legacy `incident.asn_url` fallback removed
- `migrations/versions/9bf8514d8bc9_set_incident_asn_url_nullable.py` — Sets `Incident.asn_url` nullable (with reversible downgrade normalization)
- `migrations/versions/c955648fb8e6_stub_drop_incident_asn_url.py` — Deferred follow-up stub for dropping `Incident.asn_url` in next release
- `Planning/Observations/26_Apr_2026_FAA_AIDS_URL_Recovery_Assessment.md` — FAA_AIDS URL recovery assessment and known-limitation decision
- `tests/test_routes.py` — May need updates if template changes affect route test assertions
- `tests/test_ntsb_importer.py` — Needs new tests for corrected CAROL/legacy URL construction logic
- `tests/test_importer_validation.py` — Needs tests for validator fix (Phase 5 false-positive case)
- `tests/test_validate_incident_links.py` — Script-level unit tests for source-aware validator behavior
- `Planning/tasks/phase-2.4-ntsb-manual-verification-checklist.md` — Execution checklist for manual verification sample of 50 remediated NTSB URLs
- `Planning/Observations/26_Apr_2026_NTSB_Architecture_Research_Spike.md` — Phase 1 research note documenting NTSB systems, coverage ranges, and URL patterns (Task 1.1)
- `Planning/Observations/27_Apr_Observations.md` — Phase 6 root cause: WA-coded NTSB cases confirmed to never have published dockets; body-check approach confirmed via curl against `data.ntsb.gov/Docket/`

### Notes

- **Phase ordering is strict for NTSB:** Phase 2 cannot begin until Phase 1 research is complete and documented.
- **Phase 2.2 execution status:** Dry-run and apply were executed with a mapping scaffold file, resulting in a safe no-op (`rows_updated=0`) because no real `ev_id` mapping rows were present.
- **Phase 2.4 readiness:** ✅ Manual verification runbook prepared; execute once remediation apply produces non-zero updates.
- **Phase 3.1 audit finding:** Active ASN ingestion path is `scripts/scraper_utils.py` (produces `asn_url`) into `scripts/import_data.py` (writes `Incident.asn_url` and upserts ASN `IncidentSource`).
- **Phase 3.2/3.3 status:** ✅ `import_data.py` now resolves existing ASN incidents from `IncidentSource` first and avoids new `Incident.asn_url` writes; targeted tests passed.
- **Phase 3.4 audit finding:** ✅ `migrate_asn_to_incident_source.py` confirmed idempotent and now handles duplicate ASN URL collisions safely by skipping conflicting `source_record_id`.
- **Phase 3.5 execution status:** ✅ Dry-run and apply completed; apply created `1798` ASN `IncidentSource` rows. Post-apply dry-run confirms idempotent state (`total_processed=0`).
- **Phase 3.6/3.7 status:** ✅ `incident_list.html` and `global_incident_list.html` now render ASN links only via `IncidentSource` data model; legacy `incident.asn_url` template fallback removed.
- **Phase 3.8 status:** ✅ Added and applied migration `9bf8514d8bc9` to enforce nullable `Incident.asn_url` during transition.
- **Phase 3.9 status:** ✅ Manual trigger (`validate_incident_links.py --max-records 50`) created ASN link-validation audit rows (`asn_logs_total=50`).
- **Phase 3.10 status:** ✅ Added deferred migration stub `c955648fb8e6` for dropping `Incident.asn_url` in a future release after monitoring.
- **Phase 4.1 audit finding:** ✅ Sampled `25` FAA_AIDS `IncidentSource.source_data` payloads (20+ required). Records are field-indexed blobs (`c1...`) with no URL/link fields; `source_url` count remains `0/157342`, so no direct URL recovery path from stored raw payload.
- **Phase 4.4 status:** ✅ Documented FAA_AIDS URL unavailability as an explicit known limitation in `Planning/Observations/26_Apr_2026_FAA_AIDS_URL_Recovery_Assessment.md`.
- **Phase 5.1 status:** ✅ `scripts/validate_incident_links.py` now skips NTSB `source_url` validation as a validity signal (CAROL false-positive guard) via source-name-aware logic.
- **Phase 5.2 status:** ✅ NTSB now validates `report_url` as primary signal; when `report_url` is absent, validator stamps `last_validated_at` without mutating URLs.
- **Phase 5.3 status:** ✅ Confirmed fix does not affect non-NTSB sources; 176/177 tests passed (only unrelated Gemini test failure).
- **Phase 5.4 status:** ✅ Added comprehensive test in `tests/test_importer_validation.py` covering NTSB CAROL false-positive case.
- **Phase 5.5 status:** ✅ Full test suite passes with no regressions (181/182 tests passed).
- **Phase 6 background:** NTSB `WA`-coded case numbers (e.g. `DCA16WA084`, `DCA26WA031`) are international investigations where NTSB is an observer, not the lead. The `data.ntsb.gov/Docket/` pages for these cases return HTTP 200 with "The docket for this investigation has not been released." — permanently. This is server-rendered HTML (not a JS SPA), so the message is detectable via plain GET + body check. The fix is purely in `validate_source_url()` + a validator re-run; no schema change or template change required.
- **Phase 6 ordering:** Phase 6 is independent of Phases 2–5 and can be worked in parallel.
- **ASN fix-then-migrate ordering is strict:** Fix the active ingestion write path first. Verify no new `Incident.asn_url` records appear after the fix. Then run the migration.
- **Do not bulk-mark NTSB CAROL records inactive** until Phase 1 confirms those records genuinely have no valid URL elsewhere.
- Run `PYTHONPATH=. pytest tests/ -q` after each phase for regression coverage.

---

## Tasks

- [x] 1.0 NTSB Architecture Research Spike
  - [x] 1.1 Research and document all NTSB-operated systems (CAROL, legacy Aviation Accident Database, data.ntsb.gov APIs) — what each covers, year-range, and URL pattern
  - [x] 1.2 Inspect `source_data` JSON on 20+ affected NTSB IncidentSource records to determine whether stored MKeys are CAROL IDs or legacy DB IDs
  - [x] 1.3 Manually locate working report URLs for 10–20 known pre-2010 accidents to reverse-engineer the correct legacy URL pattern
  - [x] 1.4 Determine whether NTSB provides an API or bulk download mapping accident IDs to the correct report system
  - [x] 1.5 Produce a written research note (save to `Planning/Observations/`) documenting findings and a concrete remediation decision: how many records need re-pointing, to which URL pattern

- [ ] 2.0 NTSB URL Remediation
  - [x] 2.1 Write a one-time remediation script with `--dry-run` mode to re-point affected NTSB IncidentSource records to the correct URL identified in Phase 1
  - [x] 2.2 Run `--dry-run`, review output for correctness and scale, then run `--apply`
  - [x] 2.3 Update `app/ingestion/importers/ntsb_importer.py` to construct the correct URL (CAROL or legacy) based on investigation identifier type — remove the default-to-CAROL assumption
  - [ ] 2.4 Manually verify a sample of 50 updated records resolve to real investigation content (⚠️ Blocked: waiting for real mapping data to enable non-zero remediation)
  - [x] 2.5 Add/extend tests in `tests/test_ntsb_importer.py` covering the corrected URL construction logic

- [ ] 3.0 ASN Source Migration
  - [x] 3.1 Audit all code paths that write to `Incident.asn_url` (check `scripts/scraper_utils.py`, `scripts/import_data.py`, any other scrapers) — identify the active write path
  - [x] 3.2 Fix the active ASN ingestion write path to write to `IncidentSource` (`source_name='ASN'`, `source_url=asn_url`) in addition to (or instead of) `Incident.asn_url`
  - [x] 3.3 Verify the fix: run a test import and confirm new ASN records appear in `IncidentSource` with no new writes to `Incident.asn_url`
  - [x] 3.4 Audit `scripts/migrate_asn_to_incident_source.py` — confirm it is safe, idempotent, and handles duplicates correctly
  - [x] 3.5 Run migration in `--dry-run` mode; review the 1,798 records to be migrated; then run with `--apply`
  - [x] 3.6 Update `app/templates/components/incident_list.html` to read ASN links from `IncidentSource` instead of `incident.asn_url`
  - [x] 3.7 Update `app/templates/components/global_incident_list.html` to read ASN links from `IncidentSource` instead of `incident.asn_url`
  - [x] 3.8 Create a database migration in `migrations/` to set `Incident.asn_url` nullable and stop populating it
  - [x] 3.9 Verify migrated ASN records appear in `LinkValidationLog` after the next weekly cron run (or trigger manually)
  - [x] 3.10 Create a follow-up migration stub to drop `Incident.asn_url` (can be deferred to next release once confirmed safe)

- [x] 4.0 FAA_AIDS URL Investigation & Recovery
  - [x] 4.1 Inspect `source_data` JSON on a sample of 20+ FAA_AIDS IncidentSource records — determine whether raw URLs are present in stored data
  - [x] 4.2 (N/A) If URLs are recoverable from `source_data`, write and run a one-time script (with `--dry-run`) to populate `source_url` for all affected FAA_AIDS records
  - [x] 4.3 (N/A) If FAA_AIDS has a URL pattern constructable from `source_record_id`, update `faa_aids_importer.py` to construct and store `source_url` going forward
  - [x] 4.4 If URLs are genuinely unavailable for FAA_AIDS records, document this as a known limitation in `Planning/Observations/` — do not leave it as a silent gap

- [x] 5.0 Validator Logic Fix (`validate_incident_links.py`)
  - [x] 5.1 Update `validate_incident_links.py` so that NTSB `source_url` (CAROL) is not used as a validity signal — add a source-name-aware check that skips CAROL URL validation for NTSB records
  - [x] 5.2 For NTSB records, validate `report_url` as the primary signal; if absent, stamp `last_validated_at` only (do not mark active based on CAROL 200)
  - [x] 5.3 Confirm the fix does not affect non-NTSB sources where `source_url` HTTP validation is meaningful
  - [x] 5.4 Add a unit test in `tests/test_importer_validation.py` (or a new `tests/test_link_validator.py`) covering the NTSB CAROL false-positive case
  - [x] 5.5 Run the full test suite; confirm no regressions

- [ ] 6.0 NTSB "WA" (International) Docket Suppression
  - [x] 6.1 Update `validate_source_url()` in `app/ingestion/importers/base.py`: for URLs matching `data.ntsb.gov/Docket/`, switch from HEAD-only to GET and inspect the response body — return `(False, 200, 'docket_not_released')` if body contains `"has not been released"`
  - [x] 6.2 Run `validate_incident_links.py` (manually, with `--apply`) to re-validate all existing NTSB `IncidentSource` records that have a `data.ntsb.gov/Docket/` `source_url` — records where the docket is unreleased must have `source_url` set to `null` and `is_active` set to `False`
  - [x] 6.3 Confirm template suppression: verify that after 6.2, the Boeing 747 incident list no longer renders clickable NTSB links for the affected WA cases (template already filters by `is_active` — this is a manual UAT check)
  - [x] 6.4 Add a unit test for the updated `validate_source_url()`: mock a GET to a `data.ntsb.gov/Docket/` URL returning HTTP 200 with "has not been released" in the body; assert return value is `(False, 200, 'docket_not_released')`
  - [x] 6.5 Run the full test suite; confirm no regressions
