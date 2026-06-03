# FAA AIDS App Link Review Gate — 2026-06-03

**PRD:** 0009 · **Merged audit:** `data/logs/faa_aids_url_audit_brief_2026-06-02_merged.jsonl`

## Gate A — Brief audit approval

| Metric | Value |
|--------|------:|
| Total rows | 6,466 |
| `working_brief_report` | 6,416 (**99.23%**) — post re-merge |
| `not_working` | 49 |
| `working_search_prefill` | 1 |
| App link export | `data/logs/faa_aids_app_link_audit_rows.jsonl` |

- [ ] Product spot-check ≥10 `working_brief_report` URLs in browser
- [ ] Product spot-check ≥3 `not_working` samples (classifier matches browser)
- [x] Gate ≥90% brief — **met**

## FR-0 — Baseline overlap (completed)

| Metric | Value |
|--------|------:|
| FAA covered by ASN | 182 |
| FAA covered by NTSB | 64 |
| Remediated (`is_active=False`) | 246 |
| Retry4 input rows (post-FR-0) | 368 |

Report: `data/logs/faa_aids_baseline_overlap_summary.json`

## Gate B — Migration dry-run

- [x] Dry-run: **6,084** URLs would migrate to page 18
- [ ] Product approves `--apply` (or confirm applied in implementation session)

## Gate C — Post-migration

- [ ] `smoke_faa_aids_ui.py` pass (Flask running)
- [ ] Manual 5–10 brief URLs in browser
- [ ] `audit_post_faa_aids_import.py` passed

## retry4 + re-merge (2026-06-03)

- [x] ASIAS liveness true; retry4 audit **345** brief / **23** not_working (`retry4_browserua_summary.json`)
- [x] Re-merged into `faa_aids_url_audit_brief_2026-06-02_merged.jsonl` (backup: `*_merged_pre_retry4.jsonl`)
- [x] DB apply: **6,184** active FAA brief (`apply_faa_audit_buckets_to_db.py --apply`, overlap guard)
