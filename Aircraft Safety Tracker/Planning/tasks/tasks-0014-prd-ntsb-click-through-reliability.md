## Relevant Files

- `app/ingestion/importers/ntsb_importer.py` - Constructs and stores NTSB `source_url` and `report_url` values during ingestion.
- `app/ingestion/clients/ntsb.py` - NTSB client payload format; confirms which identifiers are available (e.g., `cm_mkey`, `cm_ntsbNum`, `cm_reportNum`).
- `app/ingestion/canonical.py` - Source attachment helpers (`attach_source_to_incident`) and any existing source-field conventions.
- `app/models.py` - `IncidentSource` schema (`source_url`, `report_url`, `source_record_id`, `source_data`) used by templates.
- `app/templates/components/incident_list.html` - Aircraft detail incident table; currently prefers `report_url` over `source_url` and lacks `rel="noopener noreferrer"`.
- `app/templates/components/global_incident_list.html` - Global incident cards; currently prefers `source_url` over `report_url` and already includes `rel="noopener noreferrer"`.
- `tests/test_ntsb_importer.py` - Unit tests for NTSB importer parsing/upsert behavior; likely place to validate URL selection and persistence.
- `tests/test_routes.py` - Template rendering checks for incident lists; useful for asserting link rendering behavior.
- `tests/test_source_links.py` - If present/used, validates source URL integrity and link behavior.
- `scripts/` (new) - Place for an idempotent backfill/migration script if historical NTSB URLs need rewriting to a canonical format.

### Notes

- Manual verification is required because the acceptance criterion depends on external-site navigation, which cannot be fully asserted in unit tests.
- The codebase search index is not currently available in this environment, so file discovery used grep-based scanning.
- Current template behavior differs between lists:
  - `incident_list.html` prefers `report_url` first, which can bias clicks toward PDFs.
  - `global_incident_list.html` prefers `source_url` first.
- PRD requires showing both NTSB links when both exist and keeping the primary “Details” destination as a web page (not PDF).
- `1.1` identifier inventory (from importer + model code):
  - `IncidentSource.source_record_id` is set from `cm_ntsbNum` (fallbacks: `ntsb_id`, `source_record_id`).
  - `IncidentSource.source_data` stores full raw payload (`dict(raw_record)`), so keys such as `cm_mkey`, `cm_ntsbNum`, `cm_reportNum`, `cm_eventDate`, and `cm_vehicles[*]` are persisted when present.
  - `source_url` is currently built from `cm_mkey` as `https://carol.ntsb.gov/investigations/detail/{cm_mkey}`.
  - `report_url` is currently built from `cm_reportNum` + `ntsb_num` as `https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/{ntsb_num}/pdf`.
- `1.2` reproduction summary:
  - Reproduced/confirmed failure mode from prior observation: `net::ERR_ABORTED` on `https://carol.ntsb.gov/investigations/detail/{cm_mkey}` (example `91271`).
  - Context scope is confirmed as both normal browser and embedded preview (product input = `C`).
  - Direct URL reachability is not a hard 404 signal (observed `200 text/html` SPA shell), so the issue appears to be click-through runtime reliability, not simple malformed URL syntax.
- `1.3` official non-PDF destination research (using persisted identifiers):
  - Current destination (uses persisted `cm_mkey`): `https://carol.ntsb.gov/investigations/detail/{cm_mkey}`.
  - Viable alternative destination (uses persisted `cm_ntsbNum` / `source_record_id`): `https://data.ntsb.gov/Docket/?NTSBNumber={ntsb_number}`.
  - Validation check: `https://data.ntsb.gov/Docket/?NTSBNumber=CEN23FA019` resolves to a full NTSB Docket web page with incident metadata and docket items (non-PDF).
  - Conclusion: we can support a browser-native non-PDF fallback/details path using only identifiers already persisted in our DB.
- `1.4` canonical URL decision (locked for implementation):
  - Canonical **NTSB Details** URL pattern: `https://data.ntsb.gov/Docket/?NTSBNumber={source_record_id}` (non-PDF web page).
  - Secondary **NTSB Docs** URL: keep existing report/doc URL in `report_url` when present.
  - Fallback order for details rendering/building:
    1. `https://data.ntsb.gov/Docket/?NTSBNumber={source_record_id}` when `source_record_id` exists.
    2. `https://carol.ntsb.gov/investigations/detail/{cm_mkey}` when `source_record_id` is missing but `cm_mkey` exists.
    3. Existing stored `source_url` when neither identifier is available.
  - This aligns with product constraint: primary click-through must be browser-native (not PDF).
- `1.5` manual acceptance test matrix (cross-year, minimum 5 incidents):
  - Case A (2024): `DCA24MA063` → open Details URL; expected: docket page loads with project summary + docket items.
  - Case B (2023): `CEN23FA125` → open Details URL; expected: docket page loads; no navigation abort.
  - Case C (2022): `CEN23FA019` → open Details URL; expected: docket page loads; NTSB Number visible.
  - Case D (2005): `NYC05FA069` → open Details URL; expected: historical docket page loads.
  - Case E (legacy CAROL mkey sample): `cm_mkey=91271` → open fallback CAROL detail URL; expected: page shell loads and is navigable in normal browser (capture preview behavior separately).
  - Pass criteria for each case:
    1. Click opens a new tab.
    2. Destination is an NTSB web page (not forced PDF for Details).
    3. User can access additional incident context from landing page.
- `2.4` UI compactness/readability verification:
  - NTSB Details + NTSB Docs are rendered in existing `flex flex-wrap gap-2` containers, preserving wrapping behavior on narrow widths.
  - Source chips and action links retain existing typography/spacing utility classes.
  - Route/template regression smoke: `PYTHONPATH=. pytest tests/test_routes.py` passed (`27 passed`), indicating no functional rendering regressions.

## Tasks

- [x] 1.0 Identify the canonical NTSB “Details” URL pattern and required identifiers
  - [x] 1.1 Inventory what identifiers we already persist for NTSB incidents (`IncidentSource.source_record_id` and `IncidentSource.source_data` keys like `cm_mkey`, `cm_ntsbNum`, `cm_reportNum`).
  - [x] 1.2 Confirm current “Details” link format (`https://carol.ntsb.gov/investigations/detail/{cm_mkey}`) is the source of failures (reproduce in both: normal browser + embedded preview).
  - [x] 1.3 Research alternative official NTSB web destinations that are more reliable for in-browser viewing (non-PDF), using only identifiers we have.
  - [x] 1.4 Decide and document the canonical “NTSB Details” URL pattern to use going forward (must be a web page, not a PDF).
  - [x] 1.5 Define acceptance test cases (manual): at least 5 NTSB incidents across different years, all links open successfully and show additional incident detail.

- [ ] 2.0 Update incident list templates to render two explicit NTSB links (Details + Docs) and harden external-link attributes
  - [ ] 2.1 Update `app/templates/components/incident_list.html` to render two explicit NTSB links when both exist:
    - [x] 2.1.1 “NTSB Details” → always points to the canonical non-PDF “Details” URL.
    - [x] 2.1.2 “NTSB Docs” → points to the “docs/docket/report” URL when available (may be a PDF).
  - [ ] 2.2 Ensure both NTSB links open in a new tab with consistent external-link hardening:
    - [x] 2.2.1 Add `target="_blank"` and `rel="noopener noreferrer"` for both links.
    - [x] 2.2.2 Ensure the same external-link attributes are applied in `app/templates/components/global_incident_list.html` for consistency.
  - [x] 2.3 Ensure non-NTSB sources are unchanged (ASN/FAA_AIDS/FAA_SDR rendering stays the same in this PRD).
  - [x] 2.4 Verify the UI remains compact and readable when two links are present (no major layout regressions).

- [ ] 3.0 Update NTSB ingestion to store both link types consistently (Details as web page; Docs as secondary)
  - [ ] 3.1 Update `app/ingestion/importers/ntsb_importer.py` parsing so:
    - [ ] 3.1.1 `IncidentSource.source_url` stores the canonical “NTSB Details” web URL (non-PDF).
    - [ ] 3.1.2 `IncidentSource.report_url` stores the secondary “NTSB Docs” URL when available (can be PDF).
  - [ ] 3.2 Ensure `attach_source_to_incident(...)` calls receive the correct `source_url`/`report_url` assignments (verify both on new inserts and updates).
  - [ ] 3.3 Add logging/metrics (minimal) for cases where required identifiers are missing (so “Details” cannot be built and we must fall back to an existing URL).
  - [ ] 3.4 Validate behavior does not regress dedupe or canonicalization paths (existing `find_best_incident_match` linking still works).

- [ ] 4.0 Add an idempotent migration/backfill to update historical NTSB links to the canonical pattern (if needed)
  - [ ] 4.1 Decide whether a backfill is needed (based on how many existing NTSB `IncidentSource.source_url` values are non-canonical or known-bad).
  - [ ] 4.2 If needed, add a script under `scripts/` that:
    - [ ] 4.2.1 Iterates NTSB `IncidentSource` rows in batches.
    - [ ] 4.2.2 Recomputes the canonical “Details” URL from stored identifiers (`source_data` / `source_record_id`).
    - [ ] 4.2.3 Updates only when it can confidently produce a better canonical URL.
    - [ ] 4.2.4 Is idempotent (safe to re-run; does not overwrite already-canonical values).
  - [ ] 4.3 Add a dry-run mode that reports how many rows would be updated.
  - [ ] 4.4 Document how to run the backfill safely in dev and prod (commands + expected output).

- [ ] 5.0 Add/adjust tests and define a manual QA checklist for click-through validation in browser + embedded preview
  - [ ] 5.1 Add/adjust unit tests for NTSB ingestion URL building in `tests/test_ntsb_importer.py`:
    - [ ] 5.1.1 Given a payload containing required identifiers, assert `source_url` matches the canonical non-PDF format.
    - [ ] 5.1.2 If docs/report identifiers exist, assert `report_url` (docs link) is stored separately.
  - [ ] 5.2 Add/adjust template rendering tests (likely `tests/test_routes.py`) to assert:
    - [ ] 5.2.1 Both “NTSB Details” and “NTSB Docs” are rendered when both URLs exist.
    - [ ] 5.2.2 Links include `target="_blank"` and `rel="noopener noreferrer"`.
  - [ ] 5.3 Add a short manual QA checklist section to this tasks file:
    - [ ] 5.3.1 Test in normal browser: click NTSB Details for multiple incidents; confirm page loads and shows more incident info.
    - [ ] 5.3.2 Test in embedded preview: click NTSB Details; confirm new tab opens and loads successfully (or capture the exact failure mode if not).
    - [ ] 5.3.3 Confirm NTSB Docs link opens when present and is labeled correctly.
    - [ ] 5.3.4 Confirm other source links still behave as before.
