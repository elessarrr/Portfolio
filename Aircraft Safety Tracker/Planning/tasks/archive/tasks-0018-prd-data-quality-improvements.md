# Tasks: Data Quality Improvements (PRD 0018)

**PRD:** `0018-prd-data-quality-improvements.md`  
**Status:** `100%` (4/4 phases complete)

| Phase | Status | Notes |
|---|---|---|
| 1. Model Sorting Logic | ✅ Complete | Shared sorting logic added, route/autocomplete tests added, targeted + full suite passed |
| 2. Capitalization Standardization | ✅ Complete | Script added in Planning/scripts, ingestion title-casing added, tests + dry-run validation complete |
| 3. Data Integrity in Series List | ✅ Complete | Regex validation added, ingestion rejection enabled, cleanup script + tests + dry-run completed |
| 4. Dead Link Detection and Removal | ✅ Complete | is_active soft-flag + migration, validator script, UI suppression, tests + UAT completed |

---

## Relevant Files

- `app/routes.py` - Contains the `/search` logic and other endpoints where aircraft lists are retrieved; needs updating for custom sorting logic (Phase 1).
- `app/models.py` - Add a soft-delete/health flag on `IncidentSource` (recommended: `is_active`) for dead link handling (Phase 4).
- `app/ingestion/importers/base.py` - Enforce Title Case normalization for new ingestion input (Phase 2) and add model validation rules (Phase 3).
- `Planning/scripts/standardize_capitalization.py` - New one-time script to standardize historical capitalization (Phase 2).
- `Planning/scripts/clean_series_anomalies.py` - New one-time script to identify/fix existing malformed series data (Phase 3).
- `Planning/scripts/link_validator.py` - New script for weekly cron execution and manual CLI execution (Phase 4).
- `app/templates/components/incident_list.html` - Hide/disable dead links in rendered incident sources (Phase 4).
- `tests/test_routes.py` - Add/extend route-level assertions for search ordering and series behavior.
- `tests/test_ingestion.py` - Add/extend tests for capitalization normalization and malformed model rejection.
- `tests/test_link_validator.py` - New focused tests for link validation behavior and batching/rate-limit handling.

### Notes

- **Strict Sequence:** Implement one phase at a time, complete tests + UAT, then proceed to the next phase.
- **Single Variable Change:** No cross-phase mixing in the same PR/commit cycle.
- **Manual + Scheduled Execution:** Place operational scripts in `Planning/scripts` and ensure `link_validator.py` is callable manually and by weekly cron.
- **Phase 4 Ops Command (manual):** `PYTHONPATH=. python Planning/scripts/link_validator.py --max-records 50` (dry-run default), then `--apply` for persistence.
- **Phase 4 Ops Command (cron):** `0 2 * * 0 cd /path/to/project && PYTHONPATH=. /path/to/venv/bin/python Planning/scripts/link_validator.py --apply`.
- Use `PYTHONPATH=. pytest tests/ -q` for final regression after each phase.

## Tasks

- [x] 1.0 Phase 1: Model Sorting Logic
  - [x] 1.1 Audit all UI entry points that render model/series ordering and confirm source query paths.
  - [x] 1.2 Update ordering logic so base model names sort before variants while preserving alphabetical behavior.
  - [x] 1.3 Add/extend tests verifying representative cases (e.g., `Boeing 747` before `Boeing 747-400`).
  - [x] 1.4 Run targeted tests and complete UAT for sorting pages before Phase 2.

- [x] 2.0 Phase 2: Capitalization Standardization
  - [x] 2.1 Create `Planning/scripts/standardize_capitalization.py` for one-time historical data normalization.
  - [x] 2.2 Update ingestion normalization so all new manufacturer/model values are title-cased before persistence.
  - [x] 2.3 Add/extend tests covering script transformation and ingestion-time normalization.
  - [x] 2.4 Execute script in a safe environment, verify results with SQL checks, and complete UAT before Phase 3.

- [x] 3.0 Phase 3: Data Integrity in Series List
  - [x] 3.1 Define explicit valid-series/model rules (regex + canonical manufacturer list) based on current data realities.
  - [x] 3.2 Apply validation in ingestion and define handling for invalid rows (reject or flag with traceability).
  - [x] 3.3 Create `Planning/scripts/clean_series_anomalies.py` for one-time historical cleanup.
  - [x] 3.4 Add/extend tests for malformed values (`BOEING`, `BOEING 75N1`, etc.) and valid-pass cases.
  - [x] 3.5 Run cleanup + UAT to confirm the Series UI no longer surfaces anomalies.

- [x] 4.0 Phase 4: Dead Link Detection and Removal
  - [x] 4.1 Add `IncidentSource` link health state (`is_active` recommended) and include schema migration.
  - [x] 4.2 Build `Planning/scripts/link_validator.py` with timeout, content checks, and per-domain rate limiting.
  - [x] 4.3 Ensure script performs soft-flag updates in batches and is idempotent for repeated runs.
  - [x] 4.4 Update UI rendering to hide/disable dead links safely.
  - [x] 4.5 Add automated tests for validator decisions (HTTP error, timeout, invalid docket content, valid link).
  - [x] 4.6 Document weekly cron setup and verify manual CLI execution path from `Planning/scripts`.
  - [x] 4.7 Run final UAT + full test suite and mark PRD implementation complete.

---

## Known Gap: NTSB Link Architecture — Requires Full Investigation

**Scale: 82,467 records affected. This is not a minor cleanup task.**

### What We Know

**Confirmed during link validation run (26 Apr 2026):**

1. **CAROL false-200s are real but the cause is misunderstood.** CAROL docket pages (`carol.ntsb.gov`) return HTTP 200 even when showing "The docket for this investigation has not been released." We initially assumed this was a timing issue (investigation not yet complete). It is not. At least one incident **over 10 years old** shows this message — meaning the investigation is long closed. The problem is almost certainly that **we are pointing at the wrong system entirely.**

2. **CAROL does not cover all NTSB records.** CAROL is NTSB's newer system. Older investigations live in NTSB's legacy Aviation Accident Database. The MKey IDs used to construct our CAROL URLs (`carol.ntsb.gov/investigations/detail/{MKey}`) likely originate from the legacy database and were never migrated to CAROL. The CAROL page loads (HTTP 200) but has no docket because that record simply doesn't exist in CAROL — it exists elsewhere.

3. **The `GenerateNewestReport` PDF endpoint is 100% deprecated.** All 197 `report_url` records using `data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/{acc}/pdf` return HTTP 404. These are now marked inactive.

### What This Means

For the 82,467 CAROL `source_url` records: a significant but unknown proportion are pointing at the wrong door. The actual NTSB report data for those incidents likely exists — in a legacy system, at a different URL. We are not linking to dead data; we are linking to the wrong place.

### Investigation Required

This needs a proper research spike before any fix is attempted. The following must be answered:

1. **What NTSB systems exist and what records does each cover?**
   - CAROL (`carol.ntsb.gov`) — newer investigations
   - Legacy Aviation Accident Database — older investigations (what is the URL pattern?)
   - Are there other NTSB portals/APIs (e.g., `data.ntsb.gov`, `ntsb.gov/investigations`)?

2. **How are our MKeys sourced?** Inspect `source_data` JSON on a sample of affected `IncidentSource` records. Determine whether the MKey is a CAROL ID or a legacy DB ID, and whether NTSB provides a mapping between the two.

3. **Is there an NTSB API that maps an accident identifier to the correct report URL?**
   - Does `data.ntsb.gov` expose an endpoint like `/query/getCaseInfo?MKey={id}` or similar?
   - Does the NTSB provide a bulk data download that includes correct report URLs?

4. **What is the correct URL pattern for legacy investigations?**
   - Sample 10–20 old accidents known to have NTSB reports and manually find their working URLs
   - Reverse-engineer the URL scheme from those examples

5. **What proportion of our 82,467 CAROL records are genuinely in CAROL vs. legacy-only?**
   - Once the correct legacy URL pattern is known, test a sample of our affected records against both systems
   - Estimate how many need to be re-pointed vs. how many are genuinely in CAROL

### Outcome Expected from Investigation

A concrete remediation plan that specifies:
- The correct URL(s) for legacy NTSB records
- Whether a one-time re-link script is feasible (update `source_url` to the correct system)
- Whether this requires a new ingestion pipeline change to avoid re-introducing bad URLs
- Scale of records that can be fixed vs. records with no accessible report anywhere

### Do Not Proceed With

- Bulk-marking CAROL records as inactive (they may have valid data elsewhere)
- Any further NTSB URL construction using the current MKey → CAROL pattern until the mapping is understood
- Treating this as resolved — 82,467 records with potentially wrong links is a significant data quality issue for a safety-critical application

---

## Known Gap: ASN Legacy Column — 1,798 Stranded Records

Discovered 26 Apr 2026 during diagnostic run.

**Problem:**
- `Incident.asn_url` (legacy column on `Incident` table) has **1,798 Incidents** with
  ASN URLs set directly — none are in `IncidentSource`
- `IncidentSource` has **zero ASN records** — the migration has never been run
- ASN ingestion is **actively writing** to the legacy column: recent entries from
  March 2026 confirm new incidents still get `asn_url` populated
- ASN URLs are therefore **outside the link validation system entirely** — they never
  get validated, flagged as broken, or stamped with `last_validated_at`

**Impact:**
- 1,798 ASN-sourced incidents cannot be validated or soft-deleted by the
  `validate_incident_links.py` workflow
- No `LinkValidationLog` entries exist for any ASN URL

**Steps required before migration:**
1. Locate the ASN migration script (referenced in historical notes) and audit it
2. Confirm whether ASN ingestion writes to `Incident.asn_url` AND/OR to `IncidentSource`
   — if it writes to both, migration is safe; if it only writes to the legacy column,
   ingestion must be updated first to write to `IncidentSource`
3. Determine if `Incident.asn_url` should be deprecated after migration, or kept as
   a redundant read source

**After migration:**
- Incident.asn_url should be nullable/deprecated
- Eventually drop the column in a follow-up migration
- ASN records in IncidentSource should be subject to same validation + `last_validated_at` workflow

**Related files (to be confirmed):**
- `Planning/scripts/` — expected migration script location
- `app/ingestion/` — ASN importer, needs audit for which table it writes to
