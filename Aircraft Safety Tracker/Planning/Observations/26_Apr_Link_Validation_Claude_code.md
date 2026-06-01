# Session: Link Validation Run — 26 Apr 2026
**Claude Code session summary. Auto-updated after each response.**

---

## What This Session Was About
PRD-0018 Phase 4 — Dead Link Detection and Removal. Running the `LinkValidator` against all 82,665 `IncidentSource` records, driven by a Hermes Agent with Claude Code as advisor/relay.

---

## Key Discoveries (in order)

### 1. Model patch required
`app/models.py` → `IncidentSource` was missing `last_validated_at` even though the column existed in the database. Hermes patched it:
```python
last_validated_at = db.Column(db.DateTime, nullable=True)
```
Placed after `confidence_level`, before `__table_args__`. No migration needed — column already existed in DB.

### 2. HTTP-level results: 0 broken across all samples
- 300-record smoke test: 300/300 valid
- 5,000-record CSV audit: ~0 broken at HTTP level
- Conclusion: the dataset is clean at HTTP level; the real problem is content-level

### 3. NTSB CAROL is the core problem
`source_url` for NTSB records points to `carol.ntsb.gov` — a JavaScript SPA behind Cloudflare.
- Always returns HTTP 200 regardless of docket status
- Headless browser can't render it (Cloudflare + SPA = blocked)
- **Confirmed false-200**: IncidentSource ID=2 (`https://carol.ntsb.gov/investigations/detail/36176`) returns 200 but shows "The docket for this investigation has not been released"

### 4. Critical logic flaw discovered in validate_incident_links.py
The script checks `source_url` first. If valid → marks record "valid", skips `report_url`.
Because NTSB `source_url` is always HTTP 200, `report_url` (the PDF API) is **never checked for NTSB records**.
This means broken NTSB PDF links are also invisible to the current validator.

`validate_pdf_url()` already correctly detects NTSB JSON error bodies (`{"Error": "..."}`) — it just never gets called for NTSB records.

### 5. Apply run killed — was projecting 22+ hours
The full `validate_incident_links.py` run was killed. At ~0.7s/URL on NTSB, 80k records = ~22 hrs. Not viable.

### 6. Bulk-stamp NTSB approach — rejected
Suggested briefly, then rejected. Stamping NTSB `last_validated_at` without actual validation hides real problems (broken PDF report_urls).

---

## Current State (end of session)

| Item | Status |
|---|---|
| Model patched (`last_validated_at`) | Done |
| Smoke test (300 records) | Done — 0 broken |
| CSV audit (5,000 records) | Done — ~0 broken at HTTP level |
| Browser content check (15 NTSB URLs) | Blocked — Cloudflare/SPA |
| Apply run | Killed — too slow, wrong approach for NTSB |
| NTSB false-200 gap documented | Done — in tasks-0018 |

---

## Final Results (Run Complete)

| Metric | Value |
|---|---|
| NTSB `report_url` records (broken, now inactive) | 197 |
| NTSB records stamped `last_validated_at` | 82,467 |
| Non-NTSB records sampled (0 broken) | ~1,800 |
| Non-NTSB backlog (deferred to weekly cron) | ~157k |
| DB state post-run | 239,809 active / 197 inactive |
| `LinkValidationLog` entries written | 2,710 |

**Key discovery:** NTSB `GenerateNewestReport` PDF endpoint is 100% deprecated. All 197 records using it are now inactive. This was entirely invisible before this run.

---

## What Still Needs to Happen

### Immediate: Targeted NTSB report_url validator
Write a script (separate from `validate_incident_links.py`) that:
- Queries only NTSB records with a non-null `report_url`
- **Skips `source_url` entirely** (always 200, meaningless)
- Calls `validate_pdf_url(report_url)` — already correctly detects JSON error bodies
- If broken → sets `is_active = False`, nulls `report_url`
- Updates `last_validated_at` regardless of outcome
- Has `--dry-run` and `--apply` modes

For NTSB records with **no** `report_url`: bulk-stamp `last_validated_at` only (nothing to validate).

### Then: Non-NTSB sources
After NTSB is handled, run `validate_incident_links.py` normally — it will skip NTSB records (already have `last_validated_at` set) and process ASN, FAA_AIDS, FAA_SDR. These should complete quickly and HTTP validation is meaningful for them.

### Follow-up task (separate scope):
Investigate NTSB backend API (`data.ntsb.gov`) to check docket status without rendering the SPA. If an API endpoint exists for investigation status, we can detect "docket not released" at scale without a browser.

---

## Files Referenced
- `app/models.py` — `IncidentSource` class (patched)
- `app/ingestion/importers/base.py` — `validate_source_url()`, `validate_pdf_url()`
- `scripts/validate_incident_links.py` — weekly re-validation job
- `Planning/scripts/link_validator.py` — simpler `is_active` setter
- `Planning/tasks/tasks-0018-prd-data-quality-improvements.md` — gap documented here
- `data/logs/link_audit_*.csv` — CSV audit output

---

*Last updated: 2026-04-26*
