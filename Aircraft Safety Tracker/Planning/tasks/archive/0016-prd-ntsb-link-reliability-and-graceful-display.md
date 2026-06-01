# PRD-0016: NTSB Link Reliability and Graceful Display

## 0. Document Tracking

**Overall Progress:** `100%` (`4/4` steps complete)

| Step | Status | Notes |
|---|---|---|
| Observation-to-PRD gap analysis | ✅ Complete | Compared Section 1 and Section 2 of `25_Apr_Observations.md` against PRD requirements |
| Misalignment corrections | ✅ Complete | Corrected validation semantics and suppression behavior wording |
| Requirement traceability hardening | ✅ Complete | Added direct requirements for model/link integrity checks tied to observed mismatch |
| Version control notes | ✅ Complete | Added revision log with reasons and source references |

---

## 1. Introduction/Overview

Two distinct but related bugs were observed on 25 April 2025:

1. **Wrong model variant linked** — Clicking an NTSB link for a "Boeing 707-321B" incident navigated to the wrong aircraft detail (Boeing 707-300), suggesting the aircraft linkage logic is too loose or the wrong variant is being stored/selected.

2. **Broken NTSB PDF links throw errors** — Incident "NTSB Docs" links using the PDF report API return `{ "Error": "The case with MKey 0 does not exist." }` (e.g. DCA90MA019), surfacing an error to the user instead of graceful empty-state.

Both problems share a root cause: the system defers validation and precision decisions to runtime instead of committing clean, verified data at ingestion time. This PRD fixes both by hardening ingestion logic and ensuring the display layer never surfaces errors.

---

## 2. Goals

- Aircraft model variants from NTSB are stored at full precision (e.g., `Boeing 707-321B`) and correctly linked at display time — not collapsed to a generic parent model.
- External document links (NTSB PDF/docket) are validated before storage; links confirmed broken are stored as `null` rather than a live URL.
- The incident detail page never throws a render error for any combination of missing/broken data.
- Graceful degradation means: missing/broken data → empty display or fallback link, never a 500 or error page.
- Extend outage/fallback handling to FAA_AIDS, FAA_SDR, and ASN sources.
- Prioritize the two observed NTSB defects as P0 scope (wrong-model incident linkage and broken PDF link handling); treat broader multi-source outage hardening as P1 follow-on scope.

---

## 3. User Stories

- **As a researcher**, I want clicking "NTSB Docs" on a specific Boeing 707-321B incident to either show me the correct PDF or show a fallback link — not throw an error — so my investigation is not interrupted.
- **As a researcher**, I want the aircraft detail page for "Boeing 707-321B" to show incidents for that exact variant, not for a generic "Boeing 707" parent model.
- **As a power user**, I want a visible status indicator showing which data sources (NTSB, FAA_AIDS, FAA_SDR, ASN) are currently available, so I know when data may be stale.
- **As a developer**, I want a test suite that verifies the system renders without errors under partial-data and no-data conditions, so regressions are caught automatically.

---

## 4. Functional Requirements

### 4.1 — NTSB Variant Precision at Ingestion

- FR-1: The NTSB importer MUST store the raw model string from NTSB payload fields (`cm_acftmodel` or equivalent) into a new `raw_model_variant` column on `Incident` before any normalization.
- FR-2: If the NTSB importer encounters an aircraft model that is a known variant (e.g., `707-321B`) but no exact `Aircraft` record exists, the system MUST attempt to create or link to the most precise matching variant (e.g., `Boeing 707-321B`) using existing resolution logic before falling back to a parent model.
- FR-3: The `Incident` table MUST retain both `aircraft_id` (primary link) and `raw_model_variant` (original precision string) for display/debugging purposes.
- FR-4: Incident list and aircraft detail views MUST display the `raw_model_variant` string where available instead of the normalized `Aircraft.model_name`.

### 4.2 — NTSB PDF/Docket Link Validation at Ingestion

- FR-5: During NTSB ingestion, before writing `IncidentSource.source_url`, the importer MUST validate that the generated docket/details URL is syntactically valid and returns a reachable HTTP response (HEAD or GET).
- FR-6: If the HTTP HEAD returns a status in the range `[200, 299]`, store the URL as-is.
- FR-7: If the HTTP HEAD returns `[404, 410]` or the request fails (timeout, DNS error, connection refused), store `null` for that URL field and log a warning including `source_name`, `source_record_id`, and the failing URL.
- FR-8: For NTSB PDF links (`report_url`), the importer MUST perform a response-body validation check (GET) and treat JSON error payloads (including `{"Error": ...}` / `MKey 0`) as broken links even when HTTP status is `200`.
- FR-9: Validation timeout MUST be capped (recommended: 10 seconds) to prevent ingestion stalls.

### 4.3 — Fallback Display for Broken/Null Links

- FR-10: Incident template rendering MUST omit broken link elements when `source_url` and/or `report_url` are `null`; if a valid fallback exists, render only the fallback link.
- FR-11: A fallback link to the NTSB docket search (`https://data.ntsb.gov/Docket/?NTSBNumber=<case>`) MUST be displayed in place of a broken `report_url` when the PDF link is invalid but the docket number is known.
- FR-12: The NTSB importer MUST always store a valid `source_url` (the docket search URL) even when the `report_url` (PDF) is invalidated.

### 4.4 — Multi-Source Outage Handling

- FR-13: Each importer (NTSB, FAA_AIDS, FAA_SDR, ASN) MUST catch network exceptions and log a structured warning before propagating a clean failure rather than crashing.
- FR-14: The `ImportState` model MUST record `last_attempted_at` and `last_error` for every import run, regardless of outcome.
- FR-15: A status endpoint (`GET /api/data-source-status`) MUST return real-time availability (last successful import timestamp, error status) for all configured sources.
- FR-16: The homepage footer or a dedicated status page MUST display source availability derived from the endpoint in FR-15.
- FR-17: When a primary source is unavailable, the incident list MUST fall back to rendering the next-best source (following the existing NTSB > FAA_AIDS > FAA_SDR > ASN priority order) without displaying an error.

### 4.5 — Error-Free Display for Partial/No Data

- FR-18: All template renders involving `aircraft.*` fields MUST use Jinja2's `|default` filter or equivalent guards to prevent `UndefinedError` when fields are `None`.
- FR-19: The aircraft detail route (`/aircraft/<id>`) MUST handle the case where `aircraft` is `None` (or `404`) without raising an unhandled exception, returning a meaningful 404 page.
- FR-20: Comprehensive test cases MUST be added covering:
  - Incident with `null` `aircraft_id` renders without error
  - Incident with `null` `date` renders without error
  - Incident with `null` `source_url` renders without error
  - Incident with no matching `Aircraft` record renders the raw variant string
  - Aircraft with `null` `ai_summary` renders the "no summary" empty state
  - All four data sources independently unavailable during import

---

## 5. Non-Goals (Out of Scope)

- NG-1: This PRD does NOT include a full multi-source deduplication engine.
- NG-2: This PRD does NOT retroactively validate or backfill historical link URLs already stored in the database (beyond the re-validation job below).
- NG-3: This PRD does NOT modify the existing incident filtering or sorting logic.
- NG-4: This PRD does NOT implement a full outage SLA or alerting system (e.g., PagerDuty integration).

---

## 6. Design Considerations

- The existing source priority order (`NTSB > FAA_AIDS > FAA_SDR > ASN`) is preserved as the fallback ordering mechanism.
- Dropdown/autocomplete and HTMX rendering paths must also be hardened for null data (not just server-side rendered views).
- The `raw_model_variant` column should be indexed for debugging purposes but not used in primary search paths.

---

## 7. Technical Considerations

- HTTP HEAD validation at ingestion time adds latency; recommend running validation concurrently with parsing to minimize overall ingestion time impact.
- The PDF API check should parse the JSON response body (not just HTTP status) to distinguish `{ "Error": ... }` from a real PDF.
- For FAA_AIDS and FAA_SDR, reuse existing network-exception handling patterns rather than introducing new error types.
- Consider adding a `last_validated_at` field to `IncidentSource` to track when link validation last succeeded.

---

## 8. Success Metrics

- SM-1: Zero runtime errors (`500`) on the `/aircraft/<id>` page for incidents with `null` `aircraft_id`, `null` `date`, or `null` `source_url`.
- SM-2: Zero "NTSB Docs" link errors visible to end users for newly ingested incidents (pre-validated before storage).
- SM-3: `GET /api/data-source-status` returns valid JSON for all sources and reflects the correct availability state within 60 seconds of a source failure.
- SM-4: All new test cases (FR-20) pass in the CI pipeline.

---

## 9. Open Questions

- ~~OQ-1: Should the re-validation scheduled job run daily, weekly, or on-demand?~~ **RESOLVED — see Section 9.1**
- ~~OQ-2: For FAA_AIDS and FAA_SDR links, suppress or fallback?~~ **RESOLVED — see Section 9.2**
- ~~OQ-3: Should raw_model_variant auto-create Aircraft records?~~ **RESOLVED — see Section 9.3**

---

## 9.1 Re-Validation Process (OQ-1 — RESOLVED)

**Schedule:** Weekly, triggered every Sunday at 02:00 UTC via `cron` or a scheduler library (`APScheduler`).

**Scope:** The job validates all `IncidentSource` records where `source_url` or `report_url` is non-null and was last validated more than 7 days ago OR has never been validated (`last_validated_at` is null).

**Pipeline:**
1. Query all `IncidentSource` records matching the scope above, batched in groups of 100.
2. For each record, issue an HTTP HEAD request to `source_url`.
3. If `source_url` is broken (`[404, 410]`) and a `report_url` exists, validate `report_url` as a secondary fallback. If `report_url` is valid, set `source_url = report_url` and clear `report_url` to promote the working URL.
4. If both links are broken, set both to `null`.
5. Update `last_validated_at` to the current timestamp regardless of result.
6. Log a structured record to a dedicated `LinkValidationLog` table for audit trail.

**LinkValidationLog schema:**
| Field | Type | Description |
|---|---|---|
| `id` | int (PK) | |
| `incident_source_id` | int (FK) | Link to IncidentSource |
| `validated_at` | datetime | When validation ran |
| `old_source_url` | str | URL before update (nullable) |
| `old_report_url` | str | URL before update (nullable) |
| `new_source_url` | str | URL after update (nullable) |
| `new_report_url` | str | URL after update (nullable) |
| `result` | str | `valid`, `broken`, `updated`, `unchanged` |
| `http_status` | int | HTTP status received (nullable) |
| `error_detail` | str | Error message (timeout, DNS, etc.) |

**Discrepancy handling:**
- If a link was previously valid and is now broken, the system logs an `incident_source_updated` event and sends an optional notification (configurable via env var `LINK_BREAK_ALERT_ENABLED`).
- If the source URL changed to report URL (promotion), log with `result=updated`.
- No incidents are deleted; only URL fields are updated.

---

## 9.2 Suppress Functionality Specification (OQ-2 — RESOLVED)

**Definition of "suppress":** When a data source link is confirmed broken and no fallback URL exists, the system MUST **completely hide the link element from the user interface** (not render a disabled or "broken" link).

**Business rules for suppression:**
- A link is suppressed if and only if: `source_url` is `null` AND `report_url` is `null` after ingestion validation or re-validation.
- Suppression applies per incident source row, not per incident. An incident with mixed valid/broken sources shows only the valid sources.
- For FAA_AIDS and FAA_SDR, suppress broken links (no fallback pattern — these sources do not have an equivalent stable public search URL like NTSB's docket search).
- ASN source links: suppress broken links (ASN URLs are user-submitted and may expire; no canonical fallback exists).
- The suppressed state is stored in the database (`source_url = null`, `report_url = null`); templates render nothing when these fields are null.

**UI behavior:**
- NTSB: PDF link hidden if broken → show docket search link (`source_url`) instead if docket number is available.
- FAA_AIDS/FAA_SDR/ASN: when suppressed, no link element is rendered.

---

## 9.3 Aircraft Record Auto-Creation from Raw Data (OQ-3 — RESOLVED)

**Decision:** `raw_model_variant` MAY be used to automatically create new `Aircraft` records, subject to the following constraints.

**Data mapping rules:**
- The `raw_model_variant` string is parsed to extract `manufacturer` and `model_part` (e.g., `"Boeing 707-321B"` → `manufacturer="Boeing"`, `model_part="707-321B"`).
- A new `Aircraft` record is created only if ALL of the following are true:
  1. No existing `Aircraft` record matches the variant exactly (after normalization).
  2. A parent `Aircraft` record with the same base model exists (e.g., `Boeing 707` exists, so `Boeing 707-321B` can be created as a sibling).
  3. The variant string contains enough precision to be meaningfully distinct from the parent (e.g., `"321B"` ≠ `""`).
- If no parent exists (e.g., the variant is completely new like `"Comac C919"`), the incident is linked to `null` (`aircraft_id = None`) and the `raw_model_variant` is stored for later resolution.

**Validation criteria for auto-creation:**
- The variant string must not be identical to the parent's `model_name` (no duplicate records).
- The variant string must contain at least 2 characters (minimum precision threshold).
- The manufacturer must be in the allowlist (`Boeing`, `Airbus`, `Cessna`, `Lockheed`, `Douglas`, `Beechcraft`, `Bombardier`, `Embraer`, `ATR`, `Saab`, `Ilyushin`, `Antonov`, `Fokker`, `Dassault`, `Gulfstream`, `Learjet`, `Piper`, `Cirrus`, `Diamond`) — unknown manufacturers create a record with `manufacturer = null` to flag for review.

**Complete workflow (data ingestion → Aircraft record creation):**
1. **Parse** — Extract `raw_model_variant` from NTSB payload field (`cm_acftmodel`).
2. **Normalize** — Apply comparison normalization (trim, collapse whitespace, uppercase) to determine match candidates.
3. **Resolve** — Query `Aircraft` for exact match first, then prefix fallback using existing `resolve_aircraft()` logic.
4. **Auto-create decision** — If no match and variant has sufficient precision AND a parent exists: create new `Aircraft` record.
5. **Link** — Store `aircraft_id` (new or matched) and `raw_model_variant` in `Incident`.
6. **Flag** — If the manufacturer is unknown, log a warning and store `aircraft_id = None` pending manual review.
7. **Display** — At render time, show `raw_model_variant` if `aircraft_id` is None, otherwise show the linked `Aircraft.model_name`.

---

## 10. Revised Functional Requirements (Incorporating Answers)

### 10.1 — Weekly Link Re-Validation Job

- FR-21: A `LinkValidationLog` table MUST be added to the database schema with the fields specified in Section 9.1.
- FR-22: A scheduled job (`scripts/validate_incident_links.py`) MUST run weekly, batch-validating all unvalidated or stale `IncidentSource` URLs.
- FR-23: The job MUST update `last_validated_at` on each processed `IncidentSource`.
- FR-24: The job MUST log all validation outcomes to `LinkValidationLog`.
- FR-25: The job MUST promote `report_url` to `source_url` when `source_url` is broken but `report_url` is valid.
- FR-26: The job MUST set both URLs to `null` and log `result=broken` when both are invalid.
- FR-27: A `LINK_BREAK_ALERT_ENABLED` env var MUST control whether a notification is sent when a previously valid link becomes broken.

### 10.2 — Suppress Functionality

- FR-28: When `source_url` and `report_url` are both `null`, the incident template MUST NOT render any link element (no empty anchor, no disabled button — the element is omitted entirely).
- FR-29: FAA_AIDS, FAA_SDR, and ASN sources MUST NOT have a fallback URL pattern; broken links in these sources are simply suppressed (not replaced with a fallback link).
- FR-30: The suppression behavior MUST be tested via automated tests verifying the rendered HTML contains no `<a>` tag for suppressed sources.

### 10.3 — Aircraft Auto-Creation from Raw Model Variant

- FR-31: The NTSB importer MUST call a new `resolve_or_create_aircraft_variant(raw_variant)` function that extends the existing `resolve_aircraft()` to also attempt auto-creation when a parent exists but no exact match does.
- FR-32: The function MUST respect the manufacturer allowlist before attempting auto-creation.
- FR-33: Unknown-manufacturer variants MUST link to `aircraft_id = None` and store the raw string, rather than creating a record with unknown manufacturer.
- FR-34: Auto-created `Aircraft` records MUST have `model_name = raw_model_variant` and `manufacturer` extracted from the prefix.
- FR-35: A unique constraint on `Aircraft.model_name` prevents duplicate variant records.

### 10.4 — Direct Alignment to Observed NTSB Defects

- FR-36: NTSB link generation MUST use the incident's own source identifiers from the same ingested record (`source_record_id`/NTSB number) and MUST NOT reuse identifiers from loosely matched incidents.
- FR-37: If model resolution falls back to a parent aircraft record, the NTSB link identifiers remain unchanged and bound to the original source record to prevent cross-incident link drift.
- FR-38: Automated regression tests MUST include fixtures for both observed failure classes: (a) variant mismatch risk (`707-321B` vs `707-300`) and (b) PDF API `MKey 0` error payload handling.

---

## 11. Version Control Notes

**Version:** `v1.2`  
**Updated:** `2026-04-25`  
**Editor:** Codex (PRD alignment pass)

| Change | PRD Section Updated | Observation Reference | Justification |
|---|---|---|---|
| Added explicit P0/P1 prioritization | Section 2 (Goals) | Observation 1 + Observation 2 | Ensures the two user-reported defects remain the highest-priority delivery scope. |
| Corrected PDF validation semantics | Section 4.2 (FR-5, FR-8) | Observation 2 (error JSON with `MKey 0`) | A HEAD-only check cannot validate JSON error payloads; GET body validation is required to catch this observed failure mode. |
| Tightened suppression rendering language | Section 4.3 (FR-10), Section 9.2 UI behavior | Observation 2 (avoid user-facing error/broken UX) | Removes internal contradiction and enforces deterministic "no broken link element" behavior. |
| Added link-identifier integrity requirements | Section 10.4 (FR-36 to FR-38) | Observation 1 (wrong incident/model linked) | Prevents cross-incident identifier reuse and adds direct test coverage for the mismatch scenario reported by users. |
