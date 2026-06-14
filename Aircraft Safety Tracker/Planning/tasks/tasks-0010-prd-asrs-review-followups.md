# PRD 0010 — Multi-Model Review Follow-ups

**Source:** `/multi-model-review` on commit `494546d` (ASRS crew reports layer)  
**Reviewers:** GPT-5.3 Codex, Claude 4.6 Sonnet  
**Created:** 2026-06-18  
**PRD:** `0010-prd-asrs-contributing-factors-layer.md`

---

## Context

Both reviewers flagged the **aircraft make/model matcher** as the primary trust issue. Coverage data shows the fingerprint: **Boeing 40 (n=881)** and **Boeing 80 (n=570)** — likely false positives from substring matching on short `series_key` values (e.g. `"40" in "737400"`).

Until matcher fixes land, treat `n=` counts and contributing-factor percentages on affected aircraft pages as **unreliable**.

---

## Act on (before calling production-ready)

### 1. Fix matcher false positives

**File:** `app/ingestion/asrs_aircraft_match.py`  
**Severity:** Critical (data integrity)

- Enforce minimum `series_key` length (≥4) before substring matching
- Prefer longest exact / variant match over family-only match
- Return `None` on ambiguous ties (don't default to lowest `aircraft_id`)
- Add adversarial tests with **full catalog index** (not single-aircraft fixtures):
  - Assert `B737-400`-style strings do **not** match Boeing 40 / Boeing 80
  - Assert generic `B737` resolves predictably (rollup vs variant — document choice)

**Acceptance:** Re-run import (or remap existing rows); Boeing 40/80 `n` drops to plausible levels in `asrs_coverage_summary.json`.

---

### 2. Fix Alembic multiple heads

**File:** `migrations/versions/d4e5f6a7b8c9_add_asrs_report.py`  
**Severity:** Critical (deploy)

- `d4e5f6a7b8c9` revises `c8f1a2b3d4e5`; sibling head `be4e7bb8751a` also descends from `18bd2eb49ebb`
- Add merge migration or rebase so `flask db upgrade head` has a single path

**Acceptance:** `alembic heads` shows one head; upgrade from clean DB succeeds.

---

### 3. Remove `db.create_all()` from import script

**File:** `scripts/import_asrs.py`  
**Severity:** Critical (deploy)

- Import currently calls `db.create_all()` — can mask missing migrations in prod
- Document prerequisite: run Alembic migrate before `--apply`
- Fail fast with clear error if `asrs_report` table missing

**Acceptance:** Import on DB without table fails with actionable message; schema only via migrations.

---

### 4. Clarify UI copy for factor percentages

**File:** `app/templates/components/asrs_profile_card.html`  
**Severity:** Warning (correctness / UX)

- Multiple buckets can increment per report → displayed percentages may **sum >100%**
- Relabel as **"% of reports mentioning this factor"** (not a partition of 100%)

**Acceptance:** Disclaimer visible; no user expectation that bars sum to 100%.

---

### 5. Re-import or remap after matcher fix

**Files:** `scripts/import_asrs.py`, `data/logs/asrs_coverage_summary.json`  
**Severity:** Required follow-up to #1

- Option A: Truncate `asrs_report`, re-run HF import with fixed matcher
- Option B: Script to recompute `aircraft_id` from stored `aircraft_make_model_raw` without re-downloading HF

**Acceptance:** Updated `asrs_coverage_summary.json`; spot-check Boeing 737-800 / A320 pages in browser.

---

## Consider (next iteration)

| Item | File | Notes |
|------|------|-------|
| Tie-break by lowest `aircraft_id` | `asrs_aircraft_match.py` | Same-family variants (737-700 vs 737-800) may still collide |
| `parse_report_year` date parsing | `asrs_import.py` | Verify HF `Time_Date` format; field unused in UI today |
| `get_asrs_profile()` per-request `.all()` | `app/services/asrs.py` | Cache or SQL `GROUP BY` if page load slows |
| Dry-run stats count unmatched as `imported` | `asrs_import.py` | Misleading metrics only in dry-run |

---

## Noted (acceptable for portfolio v1)

- 30k unmatched rows (`aircraft_id` NULL) — intentional per PRD; storage only
- Full HF dataset in memory during import — OK at ~47k rows
- Single commit / ACN set in memory — OK at current scale
- HF dataset provenance — document in README; no runtime license check needed
- Synopsis unbounded `Text` — HF rows bounded

---

## Suggested task order

1. Matcher fix + tests (#1)  
2. Alembic merge (#2) + remove `create_all()` (#3)  
3. UI copy (#4)  
4. Re-import / remap (#5)  
5. Spot-check top-10 aircraft pages in browser  

---

## Related

- `Planning/tasks/tasks-0010-prd-asrs-contributing-factors-layer.md` — parent task list (complete; follow-ups above)
- `Planning/tasks/0010-prd-asrs-contributing-factors-layer.md` — PRD
- `data/logs/asrs_coverage_summary.json` — baseline coverage (pre-matcher-fix)
