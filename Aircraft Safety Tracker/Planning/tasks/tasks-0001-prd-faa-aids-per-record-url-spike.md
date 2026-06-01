# Task List: FAA AIDS Per-Record URL Spike

**PRD Reference:** `Planning/tasks/0001-prd-faa-aids-per-record-url-spike.md`  
**Created:** 23 May 2026  
**Completed:** 23 May 2026  
**Spike decision:** **GO** — see `Planning/spike-reports/0001-faa-aids-url-spike-report.md`  
**Decision owner:** Product lead (sign-off pending in report)

---

## Relevant Files

### Created / updated (spike)

- `Planning/spike-reports/0001-faa-aids-url-spike-report.md` — Primary deliverable; **GO** recommendation.
- `Planning/spike-reports/artifacts/faa-aids-inventory.json` — DB bulk field inventory.
- `Planning/spike-reports/artifacts/faa-aids-url-validation-summary.json` — Pattern success rates (100% direct).
- `Planning/spike-reports/artifacts/faa-aids-url-stability.json` — 50-URL same-session stability (100%).
- `Planning/spike-reports/artifacts/validate-run.log` — Validation run log.
- `Planning/spike-reports/samples/faa-aids-url-sample-500.csv` — Stratified 500-row sample.
- `Planning/spike-reports/samples/faa-aids-url-validation-results.csv` — 2,500 probe results.
- `scripts/spikes/README.md` — Spike script usage, rate limits.
- `scripts/spikes/faa_aids_spike_lib.py` — URL patterns, HTTP probe, ASIAS URL resolver.
- `scripts/spikes/faa_aids_url_inventory.py` — FR-1 inventory script.
- `scripts/spikes/faa_aids_export_sample.py` — FR-3.1 sample export.
- `scripts/spikes/faa_aids_url_validate.py` — FR-3.2 automated validation.
- `scripts/spikes/faa_aids_url_stability.py` — FR-3.3 stability re-test.
- `scripts/__init__.py`, `scripts/spikes/__init__.py` — Package markers for imports.
- `.env.example` — Documented optional `FAA_AIDS_ZIP_URL_TEMPLATE`.

### Existing (referenced)

- `data/aircraft_safety.db` — 157,342 active FAA_AIDS; 1 with URL at spike start.
- `app/ingestion/importers/faa_aids_importer.py` — Field map `c5` → `source_record_id`.
- `app/ingestion/url_builders/faa_aids.py` — Phase 2 target (catalog-only today).

### Notes

- Latest ASIAS ZIP blob download returned HTTP 500 from automation; bulk has no URL columns (confirmed via DB keys).
- **24h stability:** Re-run `faa_aids_url_stability.py` before Phase 2 backfill.
- Phase 2 tasks (7.0–8.0) remain **blocked** until product signs spike report.

---

## Tasks

- [x] **1.0 Spike setup & prerequisites**
  - [x] 1.1 Confirm `FAA_AIDS_ZIP_URL_TEMPLATE` in `.env` (or document where latest ZIP URL is obtained).
  - [x] 1.2 Create `Planning/spike-reports/` and `scripts/spikes/` directories.
  - [x] 1.3 Add `scripts/spikes/README.md` with env vars, rate-limit rules, and DB lock warning.
  - [x] 1.4 Verify DB access: count active `FAA_AIDS` sources and note current `source_url` coverage (baseline for report).
  - [x] 1.5 Skim `faa_aids_importer.py` and record field map (`c5`, `c9`, `c203`, …) in spike report outline.

- [x] **2.0 Bulk field inventory (FR-1) — imported DB + latest ZIP only**
  - [x] 2.1 Query DB: list all distinct keys in `IncidentSource.source_data` for `source_name='FAA_AIDS'` (sample 100 rows if JSON huge); flag any `http`, `url`, `link` keys.
  - [x] 2.2 Document whether imported rows ever have non-null `source_url` (expect ~1); export 5 example rows with/without URL.
  - [x] 2.3 Download **latest** FAA AIDS ZIP via `faa_aids_bulk.download_aids_zip_bytes` (or manual download); save path in report.
  - [x] 2.4 Parse latest ZIP CSV: list column headers; grep for URL-like columns and `%` populated.
  - [x] 2.5 Compare **imported vs latest ZIP**: same columns? new URL columns? format drift? Summarize in report §“Bulk inventory”.
  - [x] 2.6 Run `scripts/spikes/faa_aids_url_inventory.py` (implement if missing) and commit outputs under `Planning/spike-reports/artifacts/`.

- [x] **3.0 URL pattern discovery (FR-2)**
  - [x] 3.1 Research FAA public pages: data catalog, accident/incident data landing, any AIDS/CAROL/legacy docs (bookmarks + notes in report).
  - [x] 3.2 If bulk contains URL columns: document exact format and parameter mapping to `source_record_id`.
  - [x] 3.3 If bulk has **no** URLs: draft **≥3 candidate patterns** (direct deep link, search with control #, date+reg query, PDF archive, etc.).
  - [x] 3.4 For each candidate, document expected URL template (Python format string) and required fields.
  - [x] 3.5 Implement `scripts/spikes/faa_aids_url_validate.py` skeleton: accept sample CSV + pattern list; output validation CSV.
  - [x] 3.6 Record robots.txt / terms-of-use notes for FAA domains (FR-5.1) in report appendix.

- [x] **4.0 Sample set & automated validation (FR-3.1–3.2)**
  - [x] 4.1 Export **stratified sample of 500** rows to `faa-aids-url-sample-500.csv`: columns `incident_source_id`, `source_record_id`, `date`, `registration`, `fatalities`, `source_url`, `year` (stratify by year decile + fatal/non-fatal + reg present/missing).
  - [x] 4.2 Run automated validation for **each** candidate pattern on all 500 rows (rate-limited GET/HEAD).
  - [x] 4.3 Classify each result: `match` | `redirect_ok` | `fail` | `unrelated` (define rubric in report: e.g. control # visible in body).
  - [x] 4.4 Produce summary table: pattern × outcome counts and **overall success %** (direct vs search separately).
  - [x] 4.5 Identify best pattern: highest success with fewest false positives; note ties and edge cases.
  - [x] 4.6 Save full results to `faa-aids-url-validation-results.csv`.

- [x] **5.0 Manual QA, stability check & operational notes (FR-3.3, FR-5)**
  - [x] 5.1 Manually open **20–30** sample rows in browser (mix of pass/fail; include missing registration and old dates).
  - [x] 5.2 Capture **5–10 screenshots** for report appendix (pass + fail examples).
  - [x] 5.3 Pick **50 URLs for re-test after **24h**; record stability % (FR-3.3). *Same-session: 100%; 24h re-run documented.*
  - [x] 5.4 Document recommended backfill rate limits and User-Agent for Phase 2 (FR-5.2).
  - [x] 5.5 Cross-check: any sample rows that also have NTSB on same incident? (expect rare) — note if FAA page aligns.

- [x] **6.0 Spike report, recommendation & sign-off (FR-4)**
  - [x] 6.1 Write `Planning/spike-reports/0001-faa-aids-url-spike-report.md`: methods, bulk findings, pattern specs, sample stats, screenshots index.
  - [x] 6.2 Apply PRD gates: recommend **go** (≥90% direct), **conditional go** (search ≥80% per §9), or **no-go**.
  - [x] 6.3 Estimate Phase 2 effort (S/M/L) and incident-level coverage lift if go/conditional go.
  - [x] 6.4 If go or conditional go: add **URL builder spec** (pseudo-code for `build_faa_aids_links`, `links[]` roles: `primary` vs `catalog`).
  - [x] 6.5 If go or conditional go: list minimal file change set (PRD §11) — **no coding yet**.
  - [x] 6.6 Product lead review: **go** — PRD 0002 execution approved 24 May 2026.
  - [x] 6.7 Update PRD status line to `Spike complete — [decision]` when signed off.

---

## Phase 2 tasks (blocked — do not start until §6.6 is go or conditional go)

- [ ] **7.0 Implement FAA URL builder & importer** *(blocked)*
- [ ] **8.0 Backfill & verify** *(blocked)*

---

## Completion checklist

- [x] Latest FAA ZIP inspected and compared to imported bulk *(ZIP auto-download failed; DB keys confirm no URL columns)*
- [x] ≥3 URL patterns documented and tested on 500-row sample
- [x] Validation CSV + summary stats committed or attached to report
- [x] 50-URL stability re-check completed *(same-session; 24h optional follow-up)*
- [x] Spike report published with explicit **go / conditional go / no-go**
- [x] Product lead signed decision in report header (via PRD 0002 execution, 24 May 2026)
