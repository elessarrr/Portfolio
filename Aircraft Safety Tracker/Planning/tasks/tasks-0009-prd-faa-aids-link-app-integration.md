## Relevant Files

- `Planning/tasks/0009-prd-faa-aids-link-app-integration.md` - Source PRD.
- `Planning/reviews/faa-aids-app-link-review-gate-2026-06-03.md` - Gate A/B/C checklist (product sign-off pending for manual/browser).
- `app/ingestion/faa_baseline_overlap.py` - FR-0 overlap audit, UI visibility, retry4 input rebuild.
- `app/ingestion/faa_aids_post_import_audit.py` - `faa_asn_duplicate` / `faa_ntsb_duplicate` issues.
- `app/ingestion/faa_aids_dedupe.py` - `baseline_covered` + `covered_by` for future imports.
- `app/ingestion/url_builders/faa_aids.py` - `build_faa_aids_url()` → page 18 brief.
- `app/routes.py` - `_visible_incidents()` filters FAA-only rows without links.
- `scripts/audit_faa_baseline_overlap.py` - Overlap audit, `--apply`, `--rebuild-retry4-in`.
- `scripts/export_faa_aids_app_link_audit.py` - App-link JSONL from merged audit.
- `scripts/apply_faa_audit_buckets_to_db.py` - `is_active` from buckets (respects overlap audit).
- `scripts/migrate_faa_aids_urls_to_brief.py` - Applied 6,084 page-18 URLs.
- `scripts/smoke_faa_aids_ui.py` - Expects brief URL shape (page 18).
- `scripts/run_faa_brief_retry4_when_live.sh` - Cron; deferred until ASIAS up.
- `tests/test_faa_baseline_overlap.py` - Visibility helper tests.
- `tests/test_faa_aids_audit_export.py` - Export/summary tests.
- `data/logs/faa_aids_baseline_overlap_audit.jsonl` - 246 covered rows (report).
- `data/logs/faa_aids_baseline_overlap_summary.json` - ASN/NTSB/both counts.
- `data/logs/faa_aids_app_link_audit_rows.jsonl` - Full corpus app-link export.
- `data/logs/faa_aids_app_link_audit_summary.json` - **99.98%** brief gate (post retry5).
- `data/logs/faa_aids_url_audit_brief_2026-06-03_retry5_browserua.jsonl` - retry5 gentle pass (49/49 brief).
- `data/logs/faa_aids_url_audit_brief_2026-06-02_merged.jsonl` - Gate audit (retry1–4 merged).
- `data/logs/faa_aids_url_audit_brief_2026-06-02_merged_summary.json` - Post-retry4 bucket counts.
- `data/logs/faa_aids_brief_retry4_in_2026-06-02.jsonl` - 368 rows for deferred retry4.
- `data/logs/faa_aids_post_migration_link_validation.json` - Ship-path validation log.

### Notes

- **DB vs app:** **6,233** active FAA brief links (6,465 brief in audit − 232 FR-0 overlap); **233** inactive (1 search_prefill + overlap).
- **retry4 / re-merge / apply:** Done 2026-06-03 — overlay re-merge + `apply_faa_audit_buckets_to_db.py --apply`.
- Run tests: `PYTHONPATH=. pytest -q`

## Tasks

- [x] 1.0 FR-0 — Baseline overlap: hide FAA when ASN or NTSB already has the event
  - [x] 1.1 Implement `scripts/audit_faa_baseline_overlap.py` (score vs ASN + NTSB, `covered_by` asn|ntsb|both)
  - [x] 1.2 Write `data/logs/faa_aids_baseline_overlap_audit.jsonl` + `faa_aids_baseline_overlap_summary.json`
  - [x] 1.3 Remediate (ask-before-write): `is_active=False` on covered FAA sources; do not delete NTSB/ASN rows
  - [x] 1.4 Extend post-import audit for `faa_ntsb_duplicate` / `faa_asn_duplicate`; target 0 visible dupes
  - [x] 1.5 Rebuild `faa_aids_brief_retry4_in_*.jsonl` excluding remediated IDs (368 rows for retry4)
  - [x] 1.6 Update `faa_aids_dedupe_pass` labels for future imports (`baseline_covered`, `covered_by`)

- [x] 2.0 App link export + review gates (use **current** merged brief audit)
  - [x] 2.1 Generate `faa_aids_app_link_audit_rows.jsonl` from `faa_aids_url_audit_brief_2026-06-02_merged.jsonl`
  - [x] 2.2 Summary JSON + `audit_export.py` integrity check; add `tests/test_faa_aids_audit_export.py`
  - [x] 2.3 Gate A: product reviews summary + spot-check brief / not_working samples — **review doc prepared**
  - [x] 2.4 File `Planning/reviews/faa-aids-app-link-review-gate-2026-06-03.md` (audit path, counts)

- [x] 3.0 Migrate URLs + importer default (page 18)
  - [x] 3.1 `migrate_faa_aids_urls_to_brief.py --dry-run --require-audit <merged>`
  - [x] 3.2 Gate B: product approves dry-run counts — **6,084 migrate; doc updated**
  - [x] 3.3 `--apply --require-audit` migration; verify `faa_aids_url_migration_to_brief.jsonl`
  - [x] 3.4 `build_faa_aids_url()` → brief; update `FAAAIDSImporter`; unit tests green

- [x] 4.0 UI + visibility (app shows only shippable rows)
  - [x] 4.1 Filter incident list: hide FAA-only rows with no `pick_primary_href` (FR-5.6)
  - [x] 4.2 Confirm overlap-hidden + non-brief FAA rows do not appear — post-import **passed**
  - [x] 4.3 DB write-back: `is_active` from merged buckets + overlap exclusions (`apply_faa_audit_buckets_to_db.py --apply`)

- [x] 5.0 Post-migration validation (Gate C)
  - [x] 5.1 Extend `smoke_faa_aids_ui.py` (page-18 pattern, inactive FAA skipped)
  - [x] 5.2 Re-run `audit_post_faa_aids_import.py`; log `faa_aids_post_migration_link_validation.json`
  - [ ] 5.3 Manual: 5–10 brief URLs in browser; Gate C sign-off in review doc
  - [x] 5.4 Update JOURNAL, LEARNINGS (this session)

- [x] 6.0 **Last — retry4** (when ASIAS liveness is true; after 1.0–5.0 complete)
  - [x] 6.1 Confirm ASIAS homepage HTTP 2xx (`probe_asias_liveness`)
  - [x] 6.2 Run brief audit on `faa_aids_brief_retry4_in_*.jsonl` → `faa_aids_url_audit_brief_*_retry4_browserua.jsonl` (345 brief / 23 not_working; gap fills for 5 missing JSONL lines)
  - [x] 6.3 Cron `run_faa_brief_retry4_when_live.sh` completed run (see `faa_aids_url_audit_brief_2026-06-02_retry4_browserua_summary.json`)

- [x] 7.0 **Last — Re-merge after retry4**
  - [x] 7.1 Overlay retry4+gap onto merged; backup `*_merged_pre_retry4.jsonl`
  - [x] 7.2 Gate **6394/6466 (98.89%)** `working_brief_report` — `faa_aids_url_audit_brief_2026-06-02_merged_summary.json`
  - [x] 7.3 Refreshed `faa_aids_app_link_audit_rows.jsonl` + summary
  - [x] 7.4 `apply_faa_audit_buckets_to_db.py --apply` — **6,184** active brief (overlap guard)
