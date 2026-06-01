# Task List: Link Enrichment v1 — Ship on v2

**PRD Reference:** `Planning/tasks/0002-prd-link-enrichment-v1-ship.md`  
**Parent spike:** `Planning/tasks/0001-prd-faa-aids-per-record-url-spike.md` (GO)  
**Created:** 24 May 2026  
**Completed:** 24 May 2026  
**Branch:** `v2-(first-round-of-feedback-from-RJ)` only — **`main` is frozen (portfolio)**  
**Decision owner:** Product lead

---

## Relevant Files

### Committed (Phase 0 baseline — `9342bd8`)

- `app/link_helpers.py` — Central URL resolution; foreign-led NTSB helpers.
- `app/ingestion/url_builders/ntsb.py` — `carol_detail_has_public_content()`; foreign-led skip.
- `app/templates/components/incident_list.html` — Link helpers + FAQ copy.
- `app/__init__.py` — Jinja globals for link helpers.
- `tests/test_link_helpers.py` — 8 tests (foreign-led, CAROL heuristics).
- `scripts/spikes/*.py` — Spike research scripts.
- `JOURNAL.md`, `context/context-2026-05-24.md` — Session docs.

### Committed (Phase 1 FAA — `82abece`)

- ⭐ `app/ingestion/url_builders/faa_aids.py` — ASIAS direct URL (`P12_AIDS_RPRT_NBR`).
- ⭐ `app/ingestion/importers/faa_aids_importer.py` — Derives `source_url` on parse.
- ⭐ `app/ingestion/backfill_urls.py` — FAA builder in `_resolved_url_for_row`; merges `links[]`.
- `tests/test_faa_aids_url_builder.py` — URL builder unit tests (6 tests).

### Backfill run (local DB, not in git)

- `data/aircraft_safety.db` — 157,342/157,342 FAA_AIDS rows updated; ~97% incident URL coverage.

### Explicitly out of scope (deferred)

- `app/templates/components/global_incident_list.html` — still raw `source_url`.
- `main` branch — untouched.

### Notes

- Full backfill took **~25 min** (`attach_source_to_incident` commits per row). DB was locked during run — expected.
- One legacy test row `FAA-999` kept non-ASIAS URL (`http://faa.gov/test`); 157,341 ASIAS URLs.
- 747 page (`/aircraft/70`) is NTSB-heavy in top 50; FAA ASIAS link verified on `/aircraft/55` and via `resolve_source_href`.

---

## Tasks

- [x] **0.0 Prerequisites & branch safety**
  - [x] 0.1 Confirm current branch is `v2-(first-round-of-feedback-from-RJ)`.
  - [x] 0.2 Confirm **not** on `main`.
  - [x] 0.3 Baseline: FAA 157,342 active / 1 with URL; incidents 241,802 / 77,322 with URL (~32%).
  - [x] 0.4 Stopped Flask on port 5001.

- [x] **1.0 Phase 0 — v2 checkpoint commit (FR-0)**
  - [x] 1.1 Reviewed git status; no `.env` staged.
  - [x] 1.2 Staged link-helper work.
  - [x] 1.3 Staged spike scripts + docs.
  - [x] 1.4 Commit `9342bd8` — link enrichment v1 baseline (PRD 0002).
  - [x] 1.5 Push deferred to end of run.
  - [x] 1.6 PRD 0001 task 6.6 signed off via PRD 0002 execution.

- [x] **2.0 Phase 1 — FAA URL builder & importer (FR-1)**
  - [x] 2.1 `build_faa_aids_primary_url()` implemented.
  - [x] 2.2 `build_faa_aids_links()` — primary ASIAS + catalog secondary.
  - [x] 2.3 `build_faa_aids_source_url()` returns ASIAS primary.
  - [x] 2.4 `FAAAIDSImporter.parse()` derives URL from builder.
  - [x] 2.5 `backfill_urls._resolved_url_for_row` uses FAA builder.
  - [x] 2.6 `refresh_source_links` merges `links[]` via `merge_links_into_source_data`.
  - [x] 2.7 Unit tests in `tests/test_faa_aids_url_builder.py`.
  - [x] 2.8 17 tests pass (link_helpers + faa_aids_importer + url_builder).
  - [x] Commit `82abece`.

- [x] **3.0 Phase 2 — Pre-backfill checks & dry run (FR-2.4, FR-2.5)**
  - [x] 3.1 Stability re-run: 100% (50/50) → `faa-aids-url-stability.json`.
  - [x] 3.2 Dry-run 100 rows: 100 updated.
  - [x] 3.3 Live 100 rows: ASIAS URLs verified in DB.
  - [x] 3.4 One-liner documented in JOURNAL (CLI not wired — deferred).

- [x] **4.0 Phase 2 — Full FAA backfill (FR-2.1–2.3)**
  - [x] 4.1 Flask stopped; single writer.
  - [x] 4.2 Full refresh: **157,342 scanned, 157,342 updated, 0 errors** (~1470s).
  - [x] 4.3 Stats logged in JOURNAL.
  - [x] 4.4 Post-backfill: FAA 157,342/157,342 with URL; incidents **234,663/241,802 (97.0%)** with active URL.
  - [x] 4.5 Coverage ≥90% — no further fixes needed.

- [x] **5.0 Phase 3 — UX bar verification (FR-3)**
  - [x] 5.1 `/aircraft/70` loads (200).
  - [x] 5.2 FAA ASIAS link on `/aircraft/55` (747-400, FAA-primary row); 737 NTSB-primary rows expected.
  - [x] 5.3 Bishkek DCA17RA058: `resolve_source_href=None`, foreign-led FAQ on 747 page.
  - [x] 5.4 `/aircraft/45` (737) spot-check: 50 Details links, no empty href.
  - [x] 5.5 No `example.com` or empty `href=""` on tested pages.
  - [x] 5.6 CAROL heuristics and `global_incident_list.html` not modified.

- [x] **6.0 Phase 4 — Sign-off & freeze (FR-4)**
  - [x] 6.1 Phase 1–2 committed (`82abece`).
  - [x] 6.2 JOURNAL updated with v1 ship entry.
  - [x] 6.3 PRD 0002 status → Shipped.
  - [x] 6.4 Task list marked complete.
  - [x] 6.5 Link Enrichment v1 done — freeze ≥1 week.
  - [x] 6.6 `main` untouched.

---

## Deferred (explicitly not in v1 — do not start)

- [ ] **7.0** `global_incident_list.html` link-helper parity
- [ ] **8.0** In-app `factualNarrative` for foreign-led NTSB
- [ ] **9.0** Fix 2 stale tests in `tests/test_source_links.py`
- [ ] **10.0** Full Flask CLI restore
- [ ] **11.0** v2 → `main` portfolio cutover

---

## Completion checklist

- [x] On `v2-(first-round-of-feedback-from-RJ)`; `main` not modified
- [x] Phase 0 baseline committed
- [x] `faa_aids.py` emits ASIAS primary URL
- [x] `backfill_urls._resolved_url_for_row` uses FAA builder
- [x] Full FAA_AIDS refresh complete (157,342 rows)
- [x] FAA_AIDS URL coverage 100% (157,342/157,342)
- [x] Incident-level URL coverage 97.0%
- [x] 747 foreign-led + 737 smoke QA passed
- [x] Unit tests pass
- [x] JOURNAL updated; PRD 0002 shipped
- [x] Link enrichment **frozen** ≥1 week

---

## Final coverage (24 May 2026)

| Metric | Before | After |
|--------|--------|-------|
| FAA_AIDS with URL | 1 / 157,342 | **157,342 / 157,342** |
| ASIAS URLs | 0 | **157,341** (+1 legacy test row) |
| Incident-level active URL | ~32% | **97.0%** (234,663 / 241,802) |

**Backfill command used:**
```python
refresh_source_links('FAA_AIDS', limit=5000, offset=N, commit_every=500)  # loop until done
```

---

*Autonomous session complete — PRD 0002 Link Enrichment v1 shipped on v2.*
