# FAA AIDS Brief URL Migration — Gate Review (PRD 0007.2)

**Date:** 2026-06-03  
**Merged audit:** `data/logs/faa_aids_url_audit_brief_2026-06-02_merged.jsonl`

## Gate metric (FR-3)

| Metric | Value |
|--------|------:|
| Total rows | 6,466 |
| `working_brief_report` | 6,466 (**100%**) |
| `not_working` | 0 |
| `working_search_prefill` | 0 |
| Gate ≥90% | **Met** |

## Retry history

| Batch | Result |
|-------|--------|
| retry1–3 + browser UA | 94.09% brief (pre-retry4 merge) |
| retry4 (368 rows) | +310 brief after re-merge |
| retry5 (49 gentle) | **49/49** brief — concurrency 3, timeout 25s |

## Spot-check (10 URLs, seed 42)

**Input:** `data/logs/faa_aids_gate_spotcheck_urls_2026-06-03.jsonl`  
**Results:** `data/logs/faa_aids_gate_spotcheck_results_2026-06-03.json` — **10/10** `working_brief_report` (httpx + browser UA, brief mode)

## Patched tail row (2026-06-03)

| ID | Was | Now |
|----|-----|-----|
| `20090520857189A` | `working_search_prefill` (stale retry3 body) | `working_brief_report` — live fetch shows `brief report` marker, no search form |

## Migration

| Step | Count |
|------|------:|
| Initial `--apply` (ship path) | 6,084 |
| Tail `--apply` (post retry5) | 381 |
| **Total page-18 in DB** | 6,465 brief-gated sources |

## DB / app policy

- `is_active=True` only for `working_brief_report` excluding FR-0 overlap (**6,220** unique + overlap inactive)
- **6,233** active after last bucket apply; overlap re-apply deactivated **13** ASN-covered rows
- Post-import audit: `data/logs/faa_aids_post_migration_link_validation.json` — **passed**

## UI smoke

`scripts/smoke_faa_aids_ui.py --base-url http://127.0.0.1:5003` — **All checks passed** (page-18 `AP_BRIEF_RPT_VAR` hrefs on Boeing/Airbus sample pages)

## Product sign-off (optional)

- [ ] Manual browser: open 2–3 URLs from spot-check JSONL in Chrome/Arc
