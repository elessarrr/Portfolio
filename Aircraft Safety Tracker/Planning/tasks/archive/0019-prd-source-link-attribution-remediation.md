# Product Requirements Document: Source Link Attribution Remediation

## 1. Introduction/Overview

Following the link validation run completed on 26 Apr 2026 (PRD-0018 Phase 4), three systemic source link problems were discovered affecting the large majority of the application's external links. The problems span three of four data sources (NTSB, ASN, FAA_AIDS) and affect 84,000+ records.

The problems are distinct and require different remediation strategies:

- **NTSB (82,467 records):** Source URLs point to CAROL (`carol.ntsb.gov`), a JavaScript SPA that always returns HTTP 200 — including for investigations that don't exist in CAROL. Evidence strongly suggests we are pointing at the wrong system for legacy records: at least one 10-year-old incident still shows "docket not released," which cannot be a timing issue. The actual report data likely exists in NTSB's legacy Aviation Accident Database at a different URL. The `GenerateNewestReport` PDF endpoint was also found to be 100% deprecated (all 197 affected records have been fixed).
- **ASN (1,798 records):** ASN URLs are stranded on `Incident.asn_url`, a legacy column that predates the `IncidentSource` table. Zero ASN records exist in `IncidentSource`. Critically, ASN ingestion is **still actively writing to the legacy column** as of March 2026 — this is a live bug, not a historical one. ASN links are entirely outside the link validation system.
- **FAA_AIDS (unknown count):** FAA_AIDS records exist in `IncidentSource` but have no `source_url` or `report_url` — URLs were apparently never stored.

This PRD scopes the research and remediation needed to ensure all external source links point to the correct destination, are subject to validation, and that ingestion does not continue routing data incorrectly.

---

## 2. Goals

- Stop the live ASN ingestion bug (new records still going to `Incident.asn_url`)
- Migrate 1,798 stranded ASN records into `IncidentSource` so they enter the validation workflow
- Determine the correct URL architecture for NTSB records and re-point legacy records to the right system
- Investigate and resolve why FAA_AIDS records have no URLs
- Ensure all source types are fully covered by the validation workflow (`is_active`, `last_validated_at`, `LinkValidationLog`)
- Fix the `validate_incident_links.py` logic flaw that makes NTSB `report_url` invisible to validation

---

## 3. User Stories

- **As a user**, I want NTSB incident links to take me to the actual investigation report, not a page saying "docket not released" for a closed 10-year-old investigation.
- **As a user**, I want ASN incident links to be visible and validated the same way NTSB links are, so I can trust they work.
- **As a user**, I want clicking any external source link to have a high probability of reaching real content rather than an error page.
- **As an administrator**, I want link validation to cover all four source types — not just NTSB — so broken links from any source are caught automatically.
- **As an administrator**, I want confidence that new data imports are going to the right place, so the problems fixed in this PRD don't silently recur.

---

## 4. Functional Requirements

Implementation must follow the phase order below. Phase 1 is a prerequisite for Phase 2. Phase 3 can run concurrently with Phase 1. Phase 4 can begin after Phase 3 is confirmed complete.

---

### Phase 1 — NTSB Architecture Research Spike *(prerequisite to all NTSB URL fixes)*

1. The team must produce a written research note documenting: which NTSB systems exist (CAROL, legacy Aviation Accident Database, `data.ntsb.gov` APIs, any others), what year-range or investigation types each system covers, and the correct URL pattern for each system.
2. The team must inspect the `source_data` JSON field on a sample of at least 20 affected NTSB `IncidentSource` records to determine whether MKey values originate from CAROL or the legacy database.
3. The team must manually locate working report URLs for 10–20 known old accidents (pre-2010) to reverse-engineer the correct URL pattern for legacy investigations.
4. The team must determine whether NTSB provides an API or bulk data download that maps accident identifiers to the correct report system and URL.
5. The research spike must conclude with a written remediation decision: how many NTSB records need re-pointing, to what URL pattern, and whether a one-time script or ingestion pipeline change (or both) is required.
6. The team must **not** bulk-mark CAROL `source_url` records as `is_active=False` until Phase 1 confirms those records have no valid URL anywhere — the data may exist in a different system.

---

### Phase 2 — NTSB URL Remediation *(after Phase 1 completes)*

7. The system must update `source_url` for NTSB `IncidentSource` records that are incorrectly pointing to CAROL, replacing them with the correct legacy URL identified in Phase 1.
8. A one-time remediation script must be written with a `--dry-run` mode; the dry-run output must be reviewed before `--apply` is run.
9. The NTSB ingestion pipeline must be updated to construct the correct URL (CAROL or legacy) based on the investigation identifier type — it must not default to CAROL for all records.
10. After remediation, a sample of at least 50 updated URLs must be manually verified to confirm they resolve to real investigation content.

---

### Phase 3 — ASN Migration *(can run concurrently with Phase 1)*

11. The ASN ingestion pipeline must be updated to write new ASN records to `IncidentSource` (`source_name='ASN'`, `source_url=asn_url`) instead of `Incident.asn_url`. This fix must be deployed **before** the migration runs, so no new records accumulate in the legacy column.
12. The existing migration script `scripts/migrate_asn_to_incident_source.py` must be audited: confirm it is safe to run, handles duplicates correctly, and maps `asn_url` to `IncidentSource.source_url` accurately.
13. All 1,798 records currently on `Incident.asn_url` must be migrated to `IncidentSource`. The migration must run with dry-run validation before applying.
14. After migration is confirmed complete and ingestion no longer writes to `Incident.asn_url`, the column must be set nullable and stop being populated (deprecation).
15. A follow-up database migration to **drop** `Incident.asn_url` must be created and merged in a subsequent release once the team is confident no code reads from it.
16. Migrated ASN records must appear in `LinkValidationLog` and receive `last_validated_at` on the next weekly cron run.

---

### Phase 4 — FAA_AIDS URL Investigation

17. The team must determine why FAA_AIDS `IncidentSource` records have no `source_url` or `report_url` — either the ingestion never captured them, or they were lost in a prior migration.
18. The team must inspect `source_data` JSON on a sample of FAA_AIDS records to determine whether URLs are recoverable from stored raw data.
19. If URLs are recoverable from `source_data`, a one-time script must extract and populate `source_url` for all affected FAA_AIDS records.
20. If FAA_AIDS has a known URL pattern based on `source_record_id`, the ingestion pipeline must be updated to construct and store URLs going forward.
21. If URLs are genuinely unavailable for FAA_AIDS (e.g., FAA does not publish public-facing URLs for SDR/AIDS records), this must be documented as a known limitation rather than left as a silent gap.

---

### Phase 5 — validate_incident_links.py Logic Fix

22. The script must be updated so that NTSB `source_url` (CAROL) is not used as a validity signal — CAROL always returns HTTP 200 regardless of whether the investigation exists in CAROL.
23. For NTSB records, the script must validate `report_url` as the primary validity signal. If `report_url` is broken or absent, the record should be evaluated by other signals (e.g., result of Phase 1 research) rather than defaulting to "valid."
24. The fix must not break validation behaviour for non-NTSB sources where `source_url` HTTP checks are meaningful (ASN, FAA).
25. Updated script logic must include a unit test covering the NTSB CAROL false-positive case.

---

### Phase 6 — NTSB "WA" (International) Docket Suppression

**Background:** NTSB case numbers containing `WA` (e.g., `DCA16WA084`, `DCA26WA031`) represent international investigations where NTSB participates as an observer under ICAO Annex 13 but is not the lead authority. The lead investigation is conducted by the foreign state's aviation authority. NTSB's docket for these cases is **structurally never published** on `data.ntsb.gov/Docket/` — this is permanent, not a timing delay. Confirmed: a 2016 `WA` case still shows "The docket for this investigation has not been released." The `data.ntsb.gov/Docket/` pages are server-rendered HTML (not a JS SPA), so the message is detectable via a plain GET request.

26. `validate_source_url()` in `app/ingestion/importers/base.py` must be updated so that for URLs matching `data.ntsb.gov/Docket/`, it issues a GET request (not HEAD-only) and inspects the response body. If the body contains the string `"has not been released"`, it must return `(False, 200, 'docket_not_released')`.
27. At ingestion time, `ntsb_importer.py` already nullifies `source_url` when validation returns `False` — this requires no change to the importer. The updated `validate_source_url()` alone is sufficient to stop new `WA` dockets from being stored.
28. `validate_incident_links.py` must be triggered (manually or via cron) to re-validate all existing NTSB `IncidentSource` records with a `data.ntsb.gov/Docket/` `source_url`. Records where the docket is unreleased must have `source_url` set to `null` and `is_active` set to `False`.
29. The template (`incident_list.html`, `global_incident_list.html`) must not render any clickable NTSB link when the source's `is_active` is `False` — this is already handled by the `active_sources` filter. No template change is required unless a non-clickable "NTSB (no public docket)" badge is desired for UX clarity.
30. A unit test must be added covering the `validate_source_url()` body-check path: mock a GET to a `data.ntsb.gov/Docket/` URL returning HTTP 200 with "has not been released" in the body, assert the function returns `(False, 200, 'docket_not_released')`.

---

## 5. Non-Goals (Out of Scope)

- Browser-based or JavaScript-rendered content validation for NTSB CAROL pages (requires Playwright in headed mode; separate future task if needed)
- Showing a non-clickable "NTSB (no public docket)" badge in the UI for suppressed WA cases (deferred; current behaviour silently omits the link, which is acceptable)
- Resolving data quality issues outside source link attribution — sorting, capitalisation, series integrity are covered in PRD-0018
- Investigating FAA_SDR URL availability (scoped separately if FAA_AIDS investigation reveals a pattern applicable to SDR)
- Bulk-marking any records `is_active=False` without first confirming the record has no valid URL anywhere
- Automated link monitoring beyond what the existing weekly cron already provides

---

## 6. Technical Considerations

- **Phase ordering is strict for NTSB:** Phase 1 research must complete before any Phase 2 URL updates. Writing a re-link script before understanding the correct URL pattern risks replacing one wrong URL with another.
- **ASN fix-then-migrate ordering is strict:** If ASN ingestion continues writing to `Incident.asn_url` during migration, the migration is a moving target. Fix ingestion first, verify with a 24-hour window that no new legacy records appear, then migrate.
- **validate_incident_links.py cron is live:** Changes to the script must be backward-compatible or the cron must be paused during the changeover. Coordinate with the weekly Sunday 02:00 UTC schedule.
- **MKey ambiguity:** The same numeric MKey value may mean different things in CAROL vs. the legacy NTSB database. Do not assume the existing MKey → CAROL URL mapping is correct until Phase 1 confirms it.
- **ASN column deprecation:** Setting `Incident.asn_url` nullable is safe once migration is confirmed and no application code reads from it. Dropping the column requires a proper `migrations/` file. Search the entire codebase for references to `asn_url` before deprecating.
- **FAA_AIDS source_data inspection:** The `source_data` JSON column on `IncidentSource` may contain the original raw import data including URLs. This is the first place to look in Phase 4.

---

## 7. Success Metrics

- **NTSB:** 0 `IncidentSource` records pointing to a CAROL URL for an investigation that does not exist in CAROL (verified by sampling post-remediation)
- **ASN:** 0 records on `Incident.asn_url`; all 1,798 migrated records exist in `IncidentSource` with `source_name='ASN'`; ASN ingestion writes zero new records to the legacy column after the fix
- **ASN validation:** All migrated ASN records appear in `LinkValidationLog` within one weekly cron cycle
- **FAA_AIDS:** Either `source_url` is populated for FAA_AIDS records, or a documented decision explains why it cannot be
- **Validator:** `validate_incident_links.py` correctly detects broken NTSB `report_url` links without false-positives from CAROL `source_url`; covered by a unit test
- **WA docket suppression:** 0 active NTSB `IncidentSource` records with a `data.ntsb.gov/Docket/` `source_url` that returns "has not been released"; all such records have `is_active=False` and `source_url=null`; no clickable NTSB docket link is rendered in the UI for these records

---

## 8. Open Questions

- What is the correct URL pattern for NTSB legacy investigations? *(To be answered by Phase 1 research spike)*
- Does NTSB provide a bulk export or API mapping accident IDs to the correct report system and URL?
- Does the MKey in our `IncidentSource.source_record_id` correspond to a CAROL ID or a legacy database ID — or are they the same?
- Are FAA_AIDS source URLs genuinely unavailable, or were they simply never scraped during ingestion?
- Should `Incident.asn_url` be zeroed out immediately after migration, or kept populated as a read-redundancy fallback until the column drop migration runs?
- Is there a URL pattern for FAA_SDR records that should be addressed in a Phase 5 of this PRD, or as a separate PRD-0020?
