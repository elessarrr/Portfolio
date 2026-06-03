# Product Requirements Document: 0009 — FAA AIDS Link App Integration (NTSB-Parity)

**Project ID:** 0009  
**Created:** 02 June 2026  
**Author:** Product (with CTO)  
**Status:** Draft — ready for implementation after PRD 0007.2 gate  
**Branch policy:** Work on `v3-boeing-airbus-links`; keep `main` stable  

**Depends on:**
- PRD **0007** — 6,466 FAA AIDS rows imported; mapping gate; dedupe; post-import audit (**complete**)
- PRD **0007.1** — `faa_aids_viability.py`, `audit_faa_aids_urls.py`, liveness probe, three-tier buckets (**complete**)
- PRD **0007.2** — page-12 → page-18 brief URL migration; full-corpus brief audit; gated `migrate_faa_aids_urls_to_brief.py` (**in progress** — merged audit ~94% `working_brief_report`; retry4 pending)

**Follows pattern of:** PRD **0006.1** / **0006.2** / **0006.3** (NTSB enrichment: audit → export → review gates → app-ready links)

**Related files:**
- `Planning/tasks/0006-prd-0006.1-ntsb-enrichment-v3.md`
- `Planning/tasks/0006-prd-0006.2-ntsb-enrichment-v3-audit-export.md`
- `Planning/tasks/0007.2-prd-faa-aids-brief-report-url-migration.md`
- `app/link_picker.py` — `pick_primary_href`, `display_make_model`, `is_active` gate
- `app/ingestion/url_builders/faa_aids.py` — brief vs search URL builders
- `app/ingestion/url_builders/faa_aids_viability.py` — product-tier classification
- `scripts/audit_faa_aids_urls.py`, `scripts/migrate_faa_aids_urls_to_brief.py`
- `scripts/smoke_faa_aids_ui.py`
- `.cursor/skills/audit-urls/` — generic workflow + `references/faa-asias.md`
- `data/logs/faa_aids_url_audit_brief_2026-06-02_merged.jsonl` — current best brief audit overlay

---

## 1. Introduction / Overview

### Problem statement

PRD **0007** successfully imported **6,466 FAA AIDS** incidents into v3 with URLs stored on `IncidentSource.source_url` and surfaced through `link_picker.pick_primary_href()`. That matched the **NTSB data contract** (single resolved URL per source, no `links[]` blob, same incident list UI).

Three gaps remain before FAA is **fully shippable in the app**:

0. **Duplicate incidents:** Pre-import dedupe skipped **382** FAA rows vs ASN (`asn_covered`), but **did not** run a named FAA↔NTSB pass; ~**64+** FAA rows in the DB today likely duplicate an existing ASN or NTSB row (same event, two list entries). Product rule: **if ASN or NTSB already has the event, do not show a separate FAA row.**

1. **Product-ready URLs (not just HTTP OK):** Imported URLs use ASIAS **page 12** (search prefill). Users must click **Search AIDS** again — unacceptable UX (PRD 0007.2). A page-12 audit showing 6,466/6,466 “working” is **not** product sign-off (LEARNINGS: three-tier buckets; `working_search_prefill` ≠ brief).

2. **Reviewable link-quality pipeline:** NTSB reached app confidence through **full-corpus audit → JSONL row export → product review gates → import only `viable_with_working_link` → post-import audit → smoke**. FAA has import and audit tooling, but lacks a **single, documented “app link readiness” checklist** tying brief audit exports, DB migration, `is_active` policy, UI smoke, and skill/runbook into one shippable definition of done.

### Goal

Deliver **NTSB-parity link incorporation** for FAA AIDS: every active FAA row in the app opens a **direct brief report** (page 18) when the user clicks **Details ↗**, broken links are **hidden** (not dead clicks), and product has **reviewable artifacts** before and after URL migration — without re-importing incidents or changing incident-list layout.

---

## 2. Goals

0. **No duplicate events in the UI:** FAA AIDS rows that match an existing ASN or NTSB incident (same score-based rule as import) are **removed from the app** (`is_active=False` + hide per FR-5.6) **before** brief URL migration work.
1. **Product-ready ASIAS links:** ≥90% of corpus in `working_brief_report` before DB URL migration; remainder handled explicitly (`is_active` or documented exceptions).
2. **Gated DB migration:** `source_url` updated only from approved brief audit JSONL (`--require-audit`); importer default switched to page 18 so new rows cannot regress.
3. **Honest UI:** `pick_primary_href` never surfaces FAA URLs that failed brief audit (`is_active=False` or missing `source_url`).
4. **Reviewable exports:** One JSONL row per FAA AIDS record with bucket, URL, HTTP status, `link_reason`, and fields needed for `jq` review (mirror NTSB `ntsb_enrichment_audit_rows.jsonl` workflow).
5. **Signed-off validation package:** Automated smoke + documented manual browser spot-check + post-migration audit log — same bar as NTSB Task 7.0.
6. **Operational runbook:** `/audit-urls` skill + scripts document WAF mitigations (browser UA, concurrency 6, jitter), liveness abort, and retry merge — so future re-audits do not rediscover 403 storms.
7. **No UI redesign:** FAA rows remain indistinguishable from ASN/NTSB in `incident_list.html` (Details + Make/Model only).

---

## 3. User Stories

1. **As a** portfolio visitor,  
   **I want** **Details ↗** on a FAA AIDS incident to open the official brief report immediately,  
   **so that** I never interact with the ASIAS search form.

2. **As a** portfolio visitor,  
   **I want** incidents with broken ASIAS links to show **no** Details button (not a 403/503 dead click),  
   **so that** I trust outbound links on the site.

3. **As a** product owner,  
   **I want** a filterable JSONL export of all 6,466 FAA URLs with brief-mode buckets,  
   **so that** I can approve migration the same way we approved NTSB working links (`jq 'select(.bucket=="working_brief_report")'`).

4. **As a** developer,  
   **I want** a single PRD checklist from “audit complete” → “app verified”,  
   **so that** I do not conflate page-12 HTTP success with product readiness.

5. **As a** developer,  
   **I want** re-audit and migration steps documented in the audit-urls skill,  
   **so that** ASIAS outages and Akamai 403s are handled consistently on retry.

---

## 4. Functional Requirements

### FR-0: Baseline dedupe — hide FAA when ASN or NTSB already has the event (**Phase 0 — before retry4**)

**Product rule:** One event → one row in the incident list. If ASN **or** NTSB already represents the event, the **FAA AIDS row** must not appear. We **remove/hide FAA duplicates**, not NTSB rows (NTSB was already deduped vs ASN at NTSB import in 0006.x).

#### When to run (ordering)

| Order | What | Why |
|-------|------|-----|
| **1. FR-0 overlap audit + remediate** | Hide FAA rows that duplicate ASN/NTSB | Overlap does **not** depend on URL quality — same date/aircraft/score. |
| **2. retry4 + brief URL audit** | Only on FAA rows **still active** after FR-0 | Avoids ASIAS calls on rows we will delete anyway. |
| **3. Optional verify-only** | Re-count overlaps in UI after migration | **Not** a full re-dedupe — confirm 0 visible FAA dupes. |

**You do not run FR-0 twice** because retry4 changed anything about duplicates — retry4 only re-checks HTTP URLs on existing rows; it does not add ASN/NTSB rows or new FAA incidents.

**Why not wait until after retry4?** If we dedupe *after* URL work, we still spend retry4/merge time on FAA rows that will never ship (e.g. ~64+ NTSB overlaps + ASN overlaps). Dedupe first shrinks the URL audit set once.

#### Pre-import dedupe (0007) — which database?

**It was v3 (`aircraft_safety_v3.db`), not v2.** `scripts/faa_aids_dedupe_pass.py` uses `DATABASE_URL` → `Incident.query` on whatever DB is connected. At import time that was **v3 with ASN + NTSB already loaded**; FAA rows were **not** in the DB yet, so candidates were ASN and NTSB incidents on the mapped `aircraft_id`.

The audit label `asn_covered` is **misleading** — it means “skip import” for any baseline match, not “matched ASN only.” We did **not** emit separate counts for NTSB vs ASN in `faa_aids_dedupe_audit.jsonl`. FR-0 adds that reporting and fixes **post-import** FAA rows that still slipped through (often `aircraft_id`/mapping mismatch so FAA and NTSB landed on different catalog pages).

#### Requirements

1. **FR-0.1** `scripts/audit_faa_baseline_overlap.py` — score each **active** `FAA_AIDS` incident vs baseline on same `aircraft_id`, date ±2 days:
   - **ASN:** `Incident.asn_url` present
   - **NTSB:** `IncidentSource.source_name=NTSB`, `is_active` not false  
   Use `score_ntsb_vs_asn` (≥2 strong signals = **covered**). Tag **NTSB matches explicitly** (`covered_by: ntsb`), not only ASN.

2. **FR-0.2** **Standing report** (keep for product + regression):
   - `data/logs/faa_aids_baseline_overlap_audit.jsonl` — one line per **covered** FAA row: `source_record_id`, `faa_incident_id`, `covered_by` (`asn` | `ntsb` | `both`), `baseline_incident_id`, `baseline_source` (`asn_url` / `ntsb` Details URL), `score_detail`
   - `data/logs/faa_aids_baseline_overlap_summary.json` — counts: `covered_by_asn`, `covered_by_ntsb`, `covered_by_both`, `faa_still_active_after_remediate`, `faa_unique_events`

3. **FR-0.3** **Remediation (ask-before-write):** For covered rows, `IncidentSource.is_active=False`; FR-5.6 hides FAA-only incidents from the list. **Do not** delete NTSB or ASN rows.

4. **FR-0.4** Rebuild `faa_aids_brief_retry4_in_*.jsonl` from merged brief audit **excluding** remediated `source_record_id`s before retry4 cron/CLI runs.

5. **FR-0.5** Re-run `audit_post_faa_aids_import.py`; extend to flag `faa_ntsb_duplicate` / `faa_asn_duplicate` (not only `asn_url` candidates). Target **0** covered FAA rows still visible.

6. **FR-0.6** **Future imports:** `faa_aids_dedupe_pass` writes `covered_by` (`asn`|`ntsb`|`both`) and `dedupe_status=baseline_covered` instead of only `asn_covered`.

---

### FR-1: NTSB ↔ FAA link pipeline mapping (documentation)

The implementation **must** follow this parity table (status as of 2026-06-02):

| NTSB (0006.x) | FAA equivalent | Status |
|---------------|----------------|--------|
| `resolve_ntsb_source_url()` + `validate_ntsb_url()` | `build_faa_aids_brief_report_url()` + `validate_faa_aids_url_extended()` | **Done** (0007.1) |
| Full-corpus link audit before trust | `audit_faa_aids_urls.py --url-mode brief` | **In progress** (0007.2; ~94% merged) |
| `--export-rows` JSONL for product review | Audit JSONL outputs (see FR-3) | **Partial** — standardize schema |
| Review gate before DB URL/import change | Brief audit ≥90% + manual spot-check | **Pending** (0007.2 §3) |
| Import only working-link rows | FAA already imported; **migrate** URLs + `is_active` | **Pending** (0007.2 §4) |
| `link_picker` + `is_active` | Same — `FAA_AIDS` priority 2 | **Done** |
| `display_make_model` in incident list | `faa_aids_make_model` in `source_data` | **Done** (0007 FR-13) |
| Post-import duplicate audit | `audit_post_faa_aids_import.py` | **Done** (0007) |
| UI smoke script | `smoke_faa_aids_ui.py` | **Exists** — extend post-migration (FR-8) |
| Dedupe vs ASN before insert | `faa_aids_dedupe.py` | **Done** (0007) |
| Mapping gate (no catalog bloat) | `faa_aids_make_model_to_aircraft.jsonl` | **Done** (0007) |

**FR-1.1** This PRD does **not** re-run bulk incident import; it completes **link productization** on existing rows.

---

### FR-2: Complete PRD 0007.2 (prerequisite — do not skip)

All items from `0007.2-prd-faa-aids-brief-report-url-migration.md` through migration and importer switch are **prerequisites** for marking 0009 complete:

1. **FR-2.1** Finish brief audit retries (retry4+ on **all non-`working_brief_report` rows** — `not_working` + `working_search_prefill`; **382** IDs in `faa_aids_brief_retry4_in_2026-06-02.jsonl`); merge into `faa_aids_url_audit_brief_{date}_merged.jsonl`.
2. **FR-2.2** **Review gate:** ≥90% `working_brief_report` / 6,466 + product manual check of 5–10 random brief URLs in a real browser.
3. **FR-2.3** Run `migrate_faa_aids_urls_to_brief.py --apply --require-audit <merged.jsonl>` (dry-run first).
4. **FR-2.4** Update `build_faa_aids_url()` → `build_faa_aids_brief_report_url()` in `faa_aids.py` and `FAAAIDSImporter`.
5. **FR-2.5** `audit_faa_aids_urls.py` without `--dry-run` sets `is_active=False` for **both** `not_working` and `working_search_prefill` — **only with explicit product approval** (ask-before-write). Only `working_brief_report` may remain active for FAA Details.

---

### FR-3: App link review export (NTSB 0006.2 parity + PRD 0008)

**Files:** `scripts/audit_faa_aids_urls.py`, `app/ingestion/audit_export.py` (`count_export_buckets`, `validate_export_against_report`), optional `scripts/audit_urls.py` / `audit_urls.yaml` (0008 portable engine)

1. **FR-3.1** Produce **`data/logs/faa_aids_app_link_audit_rows.jsonl`** (committed path convention; gitignore large runs if needed) with **one line per FAA AIDS `source_record_id`** after final merged brief audit.
2. **FR-3.2** Required fields per row (stable for `jq` / spreadsheets):

   | Field | Description |
   |-------|-------------|
   | `bucket` | `working_brief_report` \| `working_search_prefill` \| `not_working` |
   | `source_record_id` | FAA c5 id |
   | `faa_aids_url` | URL audited (page 18 in brief mode) |
   | `imported_incident_id` | v3 `Incident.id` if joined |
   | `http_status` | Last fetch status |
   | `link_viable` | HTTP/classifier bool |
   | `product_viable` | Brief product bool |
   | `link_reason` | e.g. `http_403`, `asias_cdn_error` |
   | `checked_at` | ISO timestamp |

3. **FR-3.3** Header comment lines (`# ...`) allowed; audit tools must skip them (LEARNINGS: NTSB JSONL pattern).
4. **FR-3.4** Summary JSON sibling: `faa_aids_app_link_audit_summary.json` with `bucket_counts`, `product_viable_count`, audit metadata (mode, UA, concurrency).
5. **FR-3.5** **Integrity check:** use `app/ingestion/audit_export.py` helpers (same as NTSB + 0008); add `tests/test_faa_aids_audit_export.py` with FAA bucket field map.
6. **FR-3.6** Re-export from final merged brief JSONL after retry4+; do not hand-maintain a separate export schema.

**Review workflow (document in PRD + skill):**

```bash
grep -v '^#' data/logs/faa_aids_app_link_audit_rows.jsonl \
  | jq 'select(.bucket=="working_brief_report")' | wc -l
```

---

### FR-4: App link review gates (NTSB 0006.2 §5.10 / 0006.3 §5.19 parity)

1. **FR-4.1** **Gate A — Audit approval:** Product reviews `faa_aids_app_link_audit_summary.json` and spot-checks ≥10 rows from `working_brief_report` and ≥3 from `not_working` (confirm classifier matches browser).
2. **FR-4.2** **Gate B — Migration approval:** Product signs off on `migrate_faa_aids_urls_to_brief.py --dry-run` diff stats (rows updated vs skipped).
3. **FR-4.3** **Gate C — Post-migration approval:** After `--apply`, Gate C checklist (FR-8) signed off.
4. **FR-4.4** Record sign-off in `Planning/reviews/faa-aids-app-link-review-gate-{date}.md` (short markdown: counts, approver, date, merged audit path).

**Hard stop:** Do not mark PRD 0009 complete until Gate C passes.

---

### FR-5: UI link contract (app incorporation)

**Files:** `app/link_picker.py`, `app/routes.py`, `app/templates/components/incident_list.html`

1. **FR-5.1** `pick_primary_href` continues to prefer `Incident.asn_url`, then NTSB, then **active** `FAA_AIDS` `source_url` (unchanged priority).
2. **FR-5.2** `is_active is not False` filter **must** remain on all FAA sources used for Details (already implemented — verify in tests).
3. **FR-5.3** After migration, spot-check that **no** active FAA `source_url` contains `p=100:12` (page 12) except deliberately retained legacy rows documented in review gate.
4. **FR-5.4** `display_make_model` shows `faa_aids_make_model` for FAA rows; catalog page title remains rolled-up name (no change to aircraft page headings).
5. **FR-5.5** **No new templates**, badges, or “FAA” labels in the incident table.
6. **FR-5.6** **Hide linkless FAA rows (product decision):** Do not render an incident in `incident_list.html` when `pick_primary_href()` is `None` **and** the incident’s only active source is `FAA_AIDS` (FAA-only enrichment row with no viable brief link). ASN and NTSB-primary rows are unchanged.
7. **FR-5.7** Implement filtering in `app/routes.py` (or query layer) before passing `incidents` to the template — not template-only `{% if href %}` hiding of the button alone.

---

### FR-6: `is_active` + visibility policy (product decisions locked)

1. **FR-6.1** After approved brief audit, DB write-back sets `IncidentSource.is_active=False` for **`not_working` and `working_search_prefill`** (neither is product-ready; only `working_brief_report` stays active).
2. **FR-6.2** **Must ask before any DB write:** script prints row counts; requires explicit `--apply` (no silent writes).
3. **FR-6.3** Inactive rows **remain** in DB for provenance and re-audit; they are **excluded from the UI** per FR-5.6 (no row, no Details).
4. **FR-6.4** Document inactive + hidden counts in review gate markdown and `faa_aids_app_link_audit_summary.json`.
5. **FR-6.5** Retry scope: any ID not in `working_brief_report` after merge is eligible for retry batches (retry4 input = all 382 non-brief rows as of 2026-06-02).

---

### FR-7: Operational runbook (`/audit-urls` skill alignment)

**Files:** `.claude/gstack/audit-urls/SKILL.md.tmpl`, `references/faa-asias.md`

1. **FR-7.1** Document **full app-link pipeline** (liveness → brief audit → merge retries → review JSONL → migrate → optional `is_active` → smoke).
2. **FR-7.2** Document **WAF mitigations** proven on retry3: `--user-agent browser`, `--concurrency 6`, `--jitter-min-ms 200 --jitter-max-ms 700`, 403 backoff; warn against concurrency 8 on large retry batches.
3. **FR-7.3** Document **liveness abort:** homepage must be HTTP 2xx before audit; 503 site-wide → do not run (false mass `not_working`).
4. **FR-7.4** Reference `scripts/run_faa_brief_retry4_when_live.sh` for scheduled retry when ASIAS recovers (optional cron).
5. **FR-7.5** Regenerate skill docs: `bun run gen:skill-docs` in gstack after tmpl edits.

---

### FR-8: Post-migration validation package (NTSB Task 7.0 parity)

1. **FR-8.1** **Automated:** Extend `scripts/smoke_faa_aids_ui.py` to assert:
   - Sample of FAA incidents return Details href matching page-18 pattern (`AP_BRIEF_RPT_VAR` or `p=100:18`).
   - No Details href for `is_active=False` FAA sources in sample.
   - HTTP HEAD/GET against ASIAS optional (skip when portal down; do not fail smoke on global 503).
2. **FR-8.2** **pytest:** `PYTHONPATH=. pytest -q` green after all changes.
3. **FR-8.3** **Manual:** Product opens 5–10 random `working_brief_report` URLs from merged audit in Chrome/Arc; confirms brief narrative visible without extra clicks.
4. **FR-8.4** Re-run `scripts/audit_post_faa_aids_import.py`; confirm no new duplicate or invalid-URL critical issues.
5. **FR-8.5** Log results in `data/logs/faa_aids_post_migration_link_validation.json` (counts, sample ids, smoke exit code, date).

---

### FR-9: Tests

1. **FR-9.1** Unit tests for export row schema + bucket count validation (mirror `test_ntsb_audit_export.py`).
2. **FR-9.2** `link_picker` tests: inactive FAA source skipped; active brief URL returned.
3. **FR-9.3** `build_faa_aids_url()` returns page-18 URL after FR-2.4.
4. **FR-9.4** Migration dry-run integration test with fixture JSONL (no live HTTP).

---

## 5. Non-Goals (Out of Scope)

1. **Re-importing 6,466 FAA incidents** from raw export (0007 complete) — FR-0 remediates duplicates already in DB, not a full re-import.
3. **FAA SDR** link incorporation (separate future PRD).
4. **Portable audit engine scaffold** (PRD 0008) — may share code later; not required for 0009 done.
5. **Family rollup / query-time aggregation** (PRD 0004 territory).
6. **Scraping ASIAS** or finding a non-ASIAS per-record URL source (confirmed none — LEARNINGS).
7. **UI redesign** (multi-link picker, source badges, separate FAA section).
8. **Merging `v3-boeing-airbus-links` → `main`** or production deploy.

---

## 6. Design Considerations

### UI (unchanged layout)

| User action | Expected behavior after 0009 |
|-------------|------------------------------|
| View aircraft incident list | FAA rows same columns as ASN/NTSB |
| Click **Details ↗** on FAA row | New tab: ASIAS **brief report** (page 18) |
| Click **Details ↗** on ASN row | ASN wikibase (unchanged) |
| FAA-only row without `working_brief_report` | **Row not shown** in incident list |
| **Make/Model** cell | Exact FAA string when row is shown |

### Source priority (unchanged)

```text
Incident.asn_url  →  NTSB  →  FAA_AIDS (active)  →  FAA_SDR  →  none
```

---

## 7. Technical Considerations

### Recommended pipeline (order)

**Ship path (ASIAS may be down):** use existing merged brief audit (`retry1+2+3`, ~94% `working_brief_report`). **retry4 + re-merge** run **after** PRD 0009 implementation (last tasks) when ASIAS is up — optional tail improvement, not a blocker.

```text
[0] FR-0: audit FAA vs ASN+NTSB baseline → remediate covered rows (hide from app)
  ↓
[1] export faa_aids_app_link_audit_rows.jsonl from current merged audit (FR-3)
  ↓
[2] REVIEW GATE A/B — approve merged `faa_aids_url_audit_brief_*_merged.jsonl` (≥90% brief)
  ↓
[3] migrate_faa_aids_urls_to_brief.py --apply --require-audit <merged>
  ↓
[4] build_faa_aids_url() / importer → page 18 default
  ↓
[5] UI: hide FAA-only rows without brief link + overlap-hidden rows (FR-5.6)
  ↓
[6] Optional: audit --apply for is_active (FR-6, product approval)
  ↓
[7] REVIEW GATE C + smoke + post_import audit (FR-8)
  ↓
[8] **Last:** retry4 when ASIAS up (active FAA rows, non-brief only)
  ↓
[9] **Last:** re-merge retry4 → `faa_aids_url_audit_brief_{date}_merged.jsonl`; refresh app-link export if counts change
```

### ASIAS / Akamai constraints (from LEARNINGS + retry experiments)

| Risk | Mitigation |
|------|------------|
| Site-wide 503 / CDN error | Liveness abort; cron retry (`run_faa_brief_retry4_when_live.sh`) |
| Per-record `http_403` | Browser UA; concurrency 6; jitter 200–700ms; smaller retry batches |
| `working_search_prefill` | Do **not** treat as app-ready; migrate to brief or hide Details |
| SQLite single-writer | No concurrent Flask + bulk audit DB writes |
| Spike 100% ≠ audit pass | PRD 0001 format proof only; 0007.1+ brief audit required |

### Key commands

```bash
cd "Aircraft Safety Tracker"

# Liveness
PYTHONPATH=. python -c "from app.ingestion.url_builders.faa_aids_viability import probe_asias_liveness; print(probe_asias_liveness())"

# Brief audit (dry-run)
DATABASE_URL="sqlite:///$(pwd)/data/aircraft_safety_v3.db" \
PYTHONPATH=. python scripts/audit_faa_aids_urls.py \
  --url-mode brief --user-agent browser --concurrency 6 \
  --jitter-min-ms 200 --jitter-max-ms 700 --dry-run

# Migrate URLs (after gate)
PYTHONPATH=. python scripts/migrate_faa_aids_urls_to_brief.py --dry-run \
  --require-audit data/logs/faa_aids_url_audit_brief_2026-06-02_merged.jsonl

# UI smoke
PYTHONPATH=. python scripts/smoke_faa_aids_ui.py --base-url http://127.0.0.1:5003
```

### Estimated effort (after 0007.2 audit completes)

| Step | Estimate |
|------|----------|
| FR-3 export standardization + tests | 2–4 hours |
| Review gates (product time) | 1–2 hours |
| Migration + importer switch | <1 hour |
| FR-6 `is_active` write-back (optional) | <30 min + approval |
| FR-8 smoke + manual QA | 1–2 hours |
| Skill doc update | 1 hour |

---

## 8. Success Metrics

1. **≥90%** of 6,466 FAA AIDS rows in `working_brief_report` in approved merged audit JSONL.
2. **100%** of active FAA `source_url` values use page-18 brief pattern post-migration (verified by SQL or smoke sample).
3. **0** user-facing Details links to page-12 search prefill on spot-check sample.
4. **Manual spot-check:** 5–10/10 brief URLs open correct narrative without extra clicks.
5. **`pytest -q`** green; post-import audit **passed**.
6. Review gate markdown filed under `Planning/reviews/`.

---

## 9. Product decisions (locked 2026-06-02)

| Topic | Decision |
|-------|----------|
| **Details ↗ eligibility** | Only `working_brief_report`. `working_search_prefill` and `not_working` are **not** app-ready. |
| **`is_active` write-back** | Set `is_active=False` for **both** non-brief buckets after audit apply (with ask-before-write). |
| **UI for linkless FAA** | **Hide the incident row** when there is no honest primary link and the row is FAA-only (FR-5.6). Do not show empty rows. |
| **Retry scope** | Retry4+ includes **all** non-`working_brief_report` IDs among rows **still active after FR-0**; input file updated (382 as of pre-FR-0 merge). |
| **Duplicate policy** | Hide **FAA** row if ASN **or** NTSB already has the event — FR-0 before retry4; standing overlap report; no second full dedupe after retry4 (verify-only). |
| **NTSB duplicates** | Weed out **FAA** copies of NTSB events (`covered_by: ntsb` in report); do not remove NTSB rows from DB. |
| **Export / 0008** | Use `app/ingestion/audit_export.py` + existing FAA audit CLI; portable `scripts/audit_urls.py` / `audit_urls.yaml` available — no further product questions on 0008. |
| **Periodic re-audit** | Deferred unless product requests an ops calendar later. |

---

## 10. Appendix: Lessons from NTSB incorporation (apply to FAA)

| Lesson (NTSB) | FAA application |
|---------------|-----------------|
| HTTP 200 ≠ working link | Use `validate_faa_aids_url_extended` + brief body markers; reject CDN shell / search page |
| Audit before write | Brief audit + gates **before** `--apply` migration |
| JSONL export for `jq` review | `faa_aids_app_link_audit_rows.jsonl` |
| CAROL empty SPA → docket fallback | FAA: page 12 → page 18 migration (different failure mode, same “product tier” idea) |
| Full corpus takes ~30–55 min | FAA 6,466 brief checks ~45–70 min; retries may add hours across WAF cooldown |
| Unknown aircraft blocked dedupe | FAA mapping resolved at import; not a link PRD issue |
| UI freeze until review | No template changes in 0009; only link URL + visibility |
| Pilot before bulk | FAA used pilot + bulk in 0007; 0009 is post-hoc link fix only |

---

*End of PRD 0009*
