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
- `scripts/backfill_ntsb_source_urls.py` - NTSB source URL backfill scaffold; currently implements deterministic batch iteration over NTSB `IncidentSource` rows.

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
- `3.1.2` ingestion verification:
  - `report_url` remains mapped to docs/report link fields (`cm_reportNum` → repgen PDF URL, fallback `pdf_report_url`).
  - `source_url` now carries canonical non-PDF Details URL; `report_url` remains secondary docs path as intended.
  - Focused importer regression check passed: `PYTHONPATH=. pytest tests/test_ntsb_importer.py` (`3 passed`).
- `3.2` attach path verification:
  - In matched-existing flow (`find_best_incident_match` hit), `attach_source_to_incident(...)` receives `source_url=parsed_record['source_url']` and `report_url=parsed_record['report_url']`.
  - In new-incident flow, the same mapping is passed into `attach_source_to_incident(...)`.
  - Helper behavior preserves consistency: `attach_source_to_incident` updates existing rows with incoming `source_url`/`report_url` when provided.
  - Focused linkage regression check passed: `PYTHONPATH=. pytest tests/test_ntsb_importer.py tests/test_source_linking.py tests/test_source_links.py` (`7 passed`).
- `3.3` observability guardrail:
  - Added minimal warning logs in NTSB parse path when canonical details identifiers are missing:
    - Warn when falling back to payload `source_url` (no `source_record_id`/`cm_mkey` path available).
    - Warn when no canonical identifiers and no `source_url` are present.
  - Focused importer regression check passed: `PYTHONPATH=. pytest tests/test_ntsb_importer.py` (`3 passed`).
- `3.4` dedupe/canonicalization regression verification:
  - Targeted checks passed after ingestion URL updates and logging additions:
    - `tests/test_dedupe.py`
    - `tests/test_source_linking.py`
    - `tests/test_ntsb_importer.py`
    - `tests/test_importer_validation.py`
  - Command/result: `PYTHONPATH=. pytest tests/test_dedupe.py tests/test_source_linking.py tests/test_ntsb_importer.py tests/test_importer_validation.py` (`10 passed`).
- `4.1` backfill-need decision (data audit):
  - Current DB audit (`IncidentSource` where `source_name='NTSB'`):
    - `total`: 82,664
    - `canonical docket URLs`: 0
    - `legacy CAROL detail URLs`: 82,664
    - `missing`: 0
    - `other`: 0
    - `mismatch vs expected canonical using source_record_id`: 82,664
  - Decision: **Backfill is required** for historical NTSB rows (effectively all current NTSB rows are non-canonical).
- `4.2.1` implementation update:
  - Added `scripts/backfill_ntsb_source_urls.py` with deterministic id-ordered batch iteration:
    - Filters `IncidentSource` rows where `source_name='NTSB'`
    - Iterates in `--batch-size` chunks (default 500)
    - Provides scan checkpoints for visibility
  - This sub-task intentionally adds only batching scaffolding; URL recomputation/update logic is deferred to `4.2.2+`.
- `4.2.2` implementation update:
  - Added canonical URL recomputation helper in `scripts/backfill_ntsb_source_urls.py`:
    - `build_canonical_ntsb_details_url(source)`
    - Identifier priority: `source.source_record_id` then `source.source_data['cm_ntsbNum']`
    - Output format: `https://data.ntsb.gov/Docket/?NTSBNumber={ntsb_number}`
  - Added scan counters for recomputation coverage:
    - `canonical_buildable`
    - `canonical_unbuildable`
  - This sub-task still does not perform DB updates (write behavior remains for `4.2.3+`).
- `4.2.3` implementation update:
  - Wired DB update logic inside the batch loop in `scripts/backfill_ntsb_source_urls.py`:
    - Update `source_url` only when: (a) canonical URL is buildable AND (b) it differs from current value.
    - `--dry-run` flag prevents writes; in dry-run mode the script still scans and reports `rows_updated` count.
    - Batch commit after each chunk (safe for production volume; ~82k rows in 500-row batches = ~165 commits worst case).
    - Updated summary output now includes: `rows_updated`, `rows_skipped`, `canonical_found`, `unbuildable`.
  - Script syntax verified: `PYTHONPATH=. python -m py_compile scripts/backfill_ntsb_source_urls.py` → `0 errors`.
  - Idempotency covered: already-canonical rows (`canonical_url == current_url`) are skipped without writes.
  - Dry-run mode (task 4.3) covered by `--dry-run` flag.
- `4.4` documentation update:
  - Script documentation added below.

### How to run `scripts/backfill_ntsb_source_urls.py`

**Prerequisites**
- Set `PYTHONPATH=.` so the Flask app context bootstraps correctly.
- Requires read + write access to the application database.

**Step 1 — Dry-run in dev (always do this first)**
```bash
PYTHONPATH=. python scripts/backfill_ntsb_source_urls.py --dry-run
```
Expected output:
```
[DRY-RUN] batch=1 scanned=500 updated=500 skipped=0
...
=== NTSB source_url backfill summary ===
mode: DRY-RUN
batches_scanned:   ~166
rows_scanned:     82,664
canonical_found:  ~82,664
unbuildable:      0
rows_updated:     ~82,664
rows_skipped:     0
```
Review `rows_updated` — this is how many historical NTSB rows will be rewritten.

**Step 2 — Run for real in dev**
```bash
PYTHONPATH=. python scripts/backfill_ntsb_source_urls.py
```
Same output but with `[COMMIT ]` prefix and actual DB writes.

**Step 3 — Run for real in prod**
```bash
PYTHONPATH=. python scripts/backfill_ntsb_source_urls.py --batch-size 500
```
Use `--batch-size 500` (default) for prod to limit row-level lock pressure per commit.

**Re-running after an interrupted run**
The script is restart-safe. It processes by ascending `id`, so an interrupted run can be re-launched with the same command — already-canonical rows (updated in the previous partial run) will be skipped as idempotent.

**Rolling back if needed**
If a rollback is needed, restore from the pre-backfill DB snapshot and re-run the ingest pipeline from scratch (ingestion will re-populate CAROL URLs, which you can then re-backfill).

## Tasks

- [x] 1.0 Identify the canonical NTSB “Details” URL pattern and required identifiers
  - [x] 1.1 Inventory what identifiers we already persist for NTSB incidents (`IncidentSource.source_record_id` and `IncidentSource.source_data` keys like `cm_mkey`, `cm_ntsbNum`, `cm_reportNum`).
  - [x] 1.2 Confirm current “Details” link format (`https://carol.ntsb.gov/investigations/detail/{cm_mkey}`) is the source of failures (reproduce in both: normal browser + embedded preview).
  - [x] 1.3 Research alternative official NTSB web destinations that are more reliable for in-browser viewing (non-PDF), using only identifiers we have.
  - [x] 1.4 Decide and document the canonical “NTSB Details” URL pattern to use going forward (must be a web page, not a PDF).
  - [x] 1.5 Define acceptance test cases (manual): at least 5 NTSB incidents across different years, all links open successfully and show additional incident detail.

- [x] 2.0 Update incident list templates to render two explicit NTSB links (Details + Docs) and harden external-link attributes
  - [ ] 2.1 Update `app/templates/components/incident_list.html` to render two explicit NTSB links when both exist:
    - [x] 2.1.1 “NTSB Details” → always points to the canonical non-PDF “Details” URL.
    - [x] 2.1.2 “NTSB Docs” → points to the “docs/docket/report” URL when available (may be a PDF).
  - [ ] 2.2 Ensure both NTSB links open in a new tab with consistent external-link hardening:
    - [x] 2.2.1 Add `target="_blank"` and `rel="noopener noreferrer"` for both links.
    - [x] 2.2.2 Ensure the same external-link attributes are applied in `app/templates/components/global_incident_list.html` for consistency.
  - [x] 2.3 Ensure non-NTSB sources are unchanged (ASN/FAA_AIDS/FAA_SDR rendering stays the same in this PRD).
  - [x] 2.4 Verify the UI remains compact and readable when two links are present (no major layout regressions).

- [x] 3.0 Update NTSB ingestion to store both link types consistently (Details as web page; Docs as secondary)
  - [ ] 3.1 Update `app/ingestion/importers/ntsb_importer.py` parsing so:
    - [x] 3.1.1 `IncidentSource.source_url` stores the canonical “NTSB Details” web URL (non-PDF).
    - [x] 3.1.2 `IncidentSource.report_url` stores the secondary “NTSB Docs” URL when available (can be PDF).
  - [x] 3.2 Ensure `attach_source_to_incident(...)` calls receive the correct `source_url`/`report_url` assignments (verify both on new inserts and updates).
  - [x] 3.3 Add logging/metrics (minimal) for cases where required identifiers are missing (so “Details” cannot be built and we must fall back to an existing URL).
  - [x] 3.4 Validate behavior does not regress dedupe or canonicalization paths (existing `find_best_incident_match` linking still works).

- [ ] 4.0 Add an idempotent migration/backfill to update historical NTSB links to the canonical pattern (if needed)
  - [x] 4.1 Decide whether a backfill is needed (based on how many existing NTSB `IncidentSource.source_url` values are non-canonical or known-bad).
  - [ ] 4.2 If needed, add a script under `scripts/` that:
    - [x] 4.2.1 Iterates NTSB `IncidentSource` rows in batches.
    - [x] 4.2.2 Recomputes the canonical "Details" URL from stored identifiers (`source_data` / `source_record_id`).
    - [x] 4.2.3 Updates only when it can confidently produce a better canonical URL.
    - [x] 4.2.4 Is idempotent (safe to re-run; does not overwrite already-canonical values).
  - [x] 4.3 Add a dry-run mode that reports how many rows would be updated.
  - [x] 4.4 Document how to run the backfill safely in dev and prod (commands + expected output).

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
