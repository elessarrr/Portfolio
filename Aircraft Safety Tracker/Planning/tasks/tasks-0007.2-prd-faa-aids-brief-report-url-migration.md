## Relevant Files

- `Planning/tasks/0007.2-prd-faa-aids-brief-report-url-migration.md` - Source PRD for this task list.
- `Planning/reviews/faa-aids-brief-migration-gate-0007.2-2026-06-03.md` - Gate review (metric, spot-check, migration counts).
- `app/ingestion/url_builders/faa_aids.py` - `build_faa_aids_url()` → brief report (page 18).
- `app/ingestion/url_builders/faa_aids_viability.py` - Three-tier bucket classification + liveness probe.
- `scripts/audit_faa_aids_urls.py` - Full-corpus audit with `--url-mode brief|search`, retry + merge.
- `scripts/merge_faa_aids_audit_overlay.py` - Overlay merge + gap-fill (retry4/5).
- `scripts/migrate_faa_aids_urls_to_brief.py` - DB migration page 12 → page 18.
- `scripts/apply_faa_audit_buckets_to_db.py` - `is_active` from merged buckets (`--overlap-audit`).
- `app/ingestion/importers/faa_aids_importer.py` - Imports use brief URLs.
- `tests/test_faa_aids_viability.py` - Bucket + mode unit tests.
- `tests/test_faa_aids_url_builder.py` - URL builder tests.
- `tests/test_merge_faa_aids_overlay.py` - Overlay merge tests.
- `data/logs/faa_aids_url_audit_brief_2026-06-02_merged.jsonl` - Final merged brief audit (**6465/6466**, 99.98%).
- `data/logs/faa_aids_url_audit_brief_2026-06-02_merged_summary.json` - Gate summary JSON.
- `data/logs/faa_aids_url_audit_brief_2026-06-03_retry5_browserua.jsonl` - Gentle retry5 (49/49 brief).
- `data/logs/faa_aids_url_migration_to_brief.jsonl` - Migration report (6084 + 381 applied).
- `data/logs/faa_aids_gate_spotcheck_urls_2026-06-03.jsonl` - 10 URL spot-check sample.
- `data/logs/faa_aids_gate_spotcheck_results_2026-06-03.json` - Spot-check validation (10/10 brief).
- `data/logs/faa_aids_post_migration_link_validation.json` - Post-import audit (passed).
- `.cursor/skills/audit-urls/SKILL.md` - Operational runbook v1.2 (retry4/5, overlay merge).

### Notes

- Run tests with: `PYTHONPATH=. pytest -q`
- **Gate met:** 99.98% `working_brief_report`; retry5 recovered last 49 infra flakes.
- **DB:** 6,465 page-18 URLs; 6,233 active FAA brief (minus overlap); 1 search_prefill inactive.

## Tasks

- [x] 1.0 Full-corpus brief-mode audit (dry-run) + summary export
  - [x] 1.1 Confirm ASIAS is up (liveness probe)
  - [x] 1.2 Run full brief audit in dry-run mode (page 18 URLs)
  - [x] 1.3 Confirm JSONL schema includes `bucket`, `product_viable`, `url_mode`, `faa_aids_url`
  - [x] 1.4 Save/attach the dated audit export path and summary JSON path for review

- [x] 2.0 Retry transient failures + merge to a safe `{stem}_merged.jsonl` output
  - [x] 2.1 Filter/export `bucket=not_working` counts + reason breakdown from the first brief audit
  - [x] 2.2a Mitigate WAF/403 blocks: browser UA + concurrency 8 + adaptive 403 backoff; validate with a 403 canary (200/200 recovered)
  - [x] 2.2 Run `--retry-failures-from` on the brief audit export (keep `--dry-run`, use browser UA mitigations) — retry1/2/3 batches completed
  - [x] 2.3 Merge retry results into `{stem}_merged.jsonl` — `data/logs/faa_aids_url_audit_brief_2026-06-02_merged.jsonl`
  - [x] 2.4 Deferred retry4/5 (0009 §6–7): retry4 + gap + **retry5 gentle** → overlay merge; see merged summary

- [x] 3.0 Review gate: confirm ≥90% `working_brief_report` + manual 5–10 browser spot-checks
  - [x] 3.1 Compute gate metric: **6465/6466 (99.98%)** from merged export
  - [x] 3.2 Gate ≥90% — no pause required
  - [x] 3.3 Select 10 representative brief URLs — `faa_aids_gate_spotcheck_urls_2026-06-03.jsonl`
  - [x] 3.4 Spot-check validation: **10/10** brief (`faa_aids_gate_spotcheck_results_2026-06-03.json`)
  - [x] 3.5 Failure patterns: 0 `not_working`; 1 `working_search_prefill` (search form on page-18 URL)

- [x] 4.0 Migrate `IncidentSource.source_url` from page 12 → page 18 (gated by audit export)
  - [x] 4.1 Dry-run confirmed counts (6084 already page 18 + 381 would migrate)
  - [x] 4.2 `--apply --require-audit` — 6084 (initial) + **381** (tail, post-retry5)
  - [x] 4.3 Migration report: `data/logs/faa_aids_url_migration_to_brief.jsonl`
  - [x] 4.4 DB spot-check: 10/10 active FAA rows use `p=100:18` + `AP_BRIEF_RPT_VAR`

- [x] 5.0 Update importer + default builder to generate brief report URLs going forward
  - [x] 5.1 `build_faa_aids_url()` → `build_faa_aids_brief_report_url()`
  - [x] 5.2 `FAAAIDSImporter` uses brief builder
  - [x] 5.3 Unit tests present and passing
  - [x] 5.4 `pytest` FAA URL tests green (23 tests)

- [x] 6.0 Post-migration validation (audit sample + UI smoke + optional `is_active` write-back decision)
  - [x] 6.1 Spot-check + merged audit stable (0 not_working post-retry5)
  - [x] 6.2 `smoke_faa_aids_ui.py` — all checks passed (page-18 hrefs)
  - [x] 6.3 Post-import audit passed after overlap re-apply (`faa_aids_post_migration_link_validation.json`)
  - [x] 6.4 `is_active` write-back: brief-only + `--overlap-audit` applied; overlap re-run deactivated 13 ASN dupes
  - [x] 6.5 JOURNAL, LEARNINGS, `/audit-urls` v1.2 updated; gate review doc filed
