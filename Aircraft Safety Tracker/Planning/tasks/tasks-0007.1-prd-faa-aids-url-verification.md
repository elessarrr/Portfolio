# Task Checklist: PRD 0007.1 — FAA AIDS URL Verification & DB Cleanup

**PRD:** `Planning/tasks/0007.1-prd-faa-aids-url-verification.md`  
**Branch:** `v3-boeing-airbus-links`  
**DB:** `data/aircraft_safety_v3.db`

---

## Phase 1: Viability Module (FR-1, FR-2)

- [x] **1.0** `app/ingestion/url_builders/faa_aids_viability.py` — `validate_faa_aids_url()` + `probe_asias_liveness()`

## Phase 2: Unit Tests (FR-8)

- [x] **2.0** `tests/test_faa_aids_viability.py` — 9 tests (503→cdn_error, 200+cdn_body, 404, empty_apex, session_expired, content_markers, liveness_false, liveness_true, no_url) — **9/9 PASSED**

## Phase 3: Audit CLI (FR-3, FR-4)

- [x] **3.0** `scripts/audit_faa_aids_urls.py` — ThreadPoolExecutor, liveness guard, JSONL export, `--dry-run`, `--only-active`, `--concurrency`

## Phase 4: UI Gate Verification (FR-6)

- [x] **4.0** `app/link_picker.py` line 22 — `_active_sources` filters `is_active is not False` ✓  
       `app/routes.py` line 17–20 — `filter(is_active True OR None)` ✓ — **no changes needed**

## Phase 5: Dry Run → Review Gate → Write-Back

- [ ] **5.0** **DRY RUN:** `PYTHONPATH=. python scripts/audit_faa_aids_urls.py --dry-run`
  - ASIAS must be reachable (probe passes)
  - Inspect `data/logs/faa_aids_url_audit_{date}.jsonl` — working + not_working rows
  - `data/logs/faa_aids_url_audit_summary.json` — counts

- [ ] **6.0** **REVIEW GATE:** Product reviews export:
  ```bash
  jq 'select(.bucket=="not_working")' data/logs/faa_aids_url_audit_{date}.jsonl | head -20
  jq -r '.link_reason' data/logs/faa_aids_url_audit_{date}.jsonl | sort | uniq -c | sort -rn
  ```
  Approve DB write-back when satisfied.

- [ ] **7.0** **DB WRITE-BACK:** Run without `--dry-run`; verify post-audit counts:
  ```bash
  DATABASE_URL="sqlite:///$(pwd)/data/aircraft_safety_v3.db" \
  PYTHONPATH=. python scripts/audit_faa_aids_urls.py --concurrency 8
  ```
  Expected: `is_active=True` count == working count in export.

## Phase 6: Post-Audit Verification

- [ ] **8.0** Smoke UI: `PYTHONPATH=. python scripts/smoke_faa_aids_ui.py --base-url http://127.0.0.1:5003`
  - FAA hrefs count on 727 page should drop from 1907 to only working URLs
  
- [ ] **9.0** Run full pytest: `PYTHONPATH=. pytest -q` — expect ≥ 110 tests green

- [ ] **10.0** Update `data/logs/faa_aids_enrichment_final_import_01Jun2026.jsonl` header comment with verification date + counts (manual edit or re-export)

- [ ] **11.0** JOURNAL + LEARNINGS updates

---

## Commands Reference

```bash
cd "Aircraft Safety Tracker"

# Dry run (safe, no DB changes)
DATABASE_URL="sqlite:///$(pwd)/data/aircraft_safety_v3.db" \
PYTHONPATH=. python scripts/audit_faa_aids_urls.py --dry-run

# Full audit (writes DB)
DATABASE_URL="sqlite:///$(pwd)/data/aircraft_safety_v3.db" \
PYTHONPATH=. python scripts/audit_faa_aids_urls.py --concurrency 8 --timeout 30

# Review export
jq 'select(.bucket=="not_working")' data/logs/faa_aids_url_audit_$(date +%Y-%m-%d).jsonl | jq -r '.link_reason' | sort | uniq -c | sort -rn

# Post-audit smoke
PYTHONPATH=. python scripts/smoke_faa_aids_ui.py --base-url http://127.0.0.1:5003

# Pytest
PYTHONPATH=. pytest -q
```
