# Product Requirements Document: Link Enrichment v1 — Ship on v2

**Project ID:** 0002  
**Created:** 24 May 2026  
**Author:** Product (with CTO)  
**Status:** Shipped — Link Enrichment v1 complete (24 May 2026)  
**Parent PRD:** `0001-prd-faa-aids-per-record-url-spike.md` (spike **GO**)  
**Branch policy:** All work on `v2-(first-round-of-feedback-from-RJ)` only — **`main` is frozen**

---

## 1. Introduction/Overview

### Problem statement

Users browsing aircraft incident lists (e.g. Boeing 747) cannot trust outbound “Details” links. Roughly **68% of incidents** have no resolvable active URL. The largest gap is **~157,342 FAA_AIDS** rows with almost no `source_url`. Secondary pain: NTSB edge cases (empty CAROL SPA shells, foreign-led accredited-rep investigations) send users to blank pages.

We have spent multiple sessions patching link UX incrementally. The spike (PRD 0001) proved a **100% direct FAA URL pattern** exists. Continuing open-ended link fixes without shipping FAA backfill creates diminishing returns and agent/context fatigue.

### Solution (this PRD)

**Declare and ship Link Enrichment v1** on the v2 branch in three slices:

1. **Checkpoint** — commit in-flight v2 work (link helpers, foreign-led NTSB fix, spike artifacts).
2. **FAA Phase 2** — implement ASIAS per-record URLs + batch backfill (~157k rows).
3. **Freeze scope** — adopt a narrow UX bar (“useful link **or** honest no-link + FAQ”); defer all other link work.

### Branch strategy (non-negotiable)

| Branch | Role |
|--------|------|
| **`main`** | Powers the **live portfolio deployment** today. **Do not merge v2 into `main`** until v2 is demonstrably better and product explicitly approves a portfolio cutover. |
| **`v2-(first-round-of-feedback-from-RJ)`** | All implementation for this PRD. This is the active development line. |

**Rationale:** The portfolio piece must keep working. v2 is the experiment/improvement track — not a replacement until ready.

### Goal

After v1 ships, a user looking up a **Boeing 747** (or any aircraft with FAA-sourced incidents) should see **working FAA links for the vast majority of rows**, or a **clear “no public record” message** — not empty CAROL/docket pages or broken hrefs.

Then **stop link enrichment work for at least one week** and move to the next product priority.

---

## 2. Goals

### Primary goals

1. **Commit** all uncommitted link-enrichment and spike work on v2 (clean baseline).
2. **Implement FAA ASIAS URL builder** per spike spec (`P12_AIDS_RPRT_NBR` = `source_record_id`).
3. **Backfill** active `FAA_AIDS` `IncidentSource` rows in batches (~157k).
4. **Raise incident-level link coverage** from ~32% to **≥90%** (target ~97% per spike estimate).
5. **Freeze Link Enrichment v1** — document in-scope vs deferred; no new link epics until product reopens.

### Secondary goals

1. Wire minimal CLI path for FAA backfill (if not already registered).
2. Re-run 24h FAA URL stability check before full backfill (if elapsed).
3. Smoke-test Boeing 747 (`/aircraft/70`) and one other high-FAA aircraft profile.

### Non-goals for v1 (explicit deferrals)

See §5.

---

## 3. User Stories

### Portfolio visitor / researcher

**As a** user viewing a Boeing 747 incident sourced from FAA AIDS,  
**I want** “Details” to open the **specific FAA ASIAS record** for that event,  
**So that** I can verify the incident without manual search.

### Portfolio visitor (edge case)

**As a** user viewing a foreign-led NTSB case (e.g. Bishkek DCA17RA058),  
**I want** either a working official link **or** an honest “No external link” with FAQ — not a blank CAROL/docket page,  
**So that** I trust the app is not sending me to dead ends.

### Product lead

**As** the product owner maintaining a live portfolio on `main`,  
**I want** v2 improvements shipped incrementally **without overwriting `main`**,  
**So that** my portfolio keeps working until v2 is clearly better.

### Engineer

**As a** developer,  
**I want** a bounded PRD with a written URL contract and success metrics,  
**So that** I can ship FAA backfill and stop iterating on CAROL heuristics.

---

## 4. Functional Requirements

### Phase 0 — v2 checkpoint (MUST)

1. **FR-0.1** Commit on `v2-(first-round-of-feedback-from-RJ)` all completed work:
   - `app/link_helpers.py`, `app/ingestion/url_builders/ntsb.py` (foreign-led + CAROL heuristics)
   - `app/templates/components/incident_list.html`
   - `app/__init__.py` (Jinja globals)
   - `tests/test_link_helpers.py`
   - Spike scripts + `Planning/spike-reports/` artifacts
   - `JOURNAL.md`, `context/context-2026-05-24.md` (if changed)
2. **FR-0.2** Commit message must reference PRD 0002 / link enrichment v1 baseline.
3. **FR-0.3** **Do not** merge to `main`. **Do not** force-push `main`.

### Phase 1 — FAA URL builder (MUST)

1. **FR-1.1** Update `app/ingestion/url_builders/faa_aids.py`:
   - Primary URL: `https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:{source_record_id}` (URL-encoded).
   - `links[]` roles: `primary` (ASIAS record), `catalog` (existing FAA landing page as secondary).
   - Remove catalog-only as **primary** when `source_record_id` is present.
2. **FR-1.2** Update `FAAAIDSImporter` (or post-parse hook) to set `source_url` on new imports when `source_record_id` (`c5`) exists.
3. **FR-1.3** Reject `example.com` and placeholder URLs at ingest (existing `link_schema` behavior — no regression).
4. **FR-1.4** Unit tests for URL builder: valid ID, encoding edge cases, missing ID → catalog-only fallback.

### Phase 2 — FAA backfill (MUST)

1. **FR-2.1** Run `refresh_source_links('FAA_AIDS')` (or equivalent in `backfill_urls.py`) against `data/aircraft_safety.db`.
2. **FR-2.2** Batch size ~5,000 rows; **single SQLite writer** (no parallel import/backfill).
3. **FR-2.3** Log progress: scanned, updated, skipped, errors.
4. **FR-2.4** Before full backfill: re-run `scripts/spikes/faa_aids_url_stability.py` if ≥24h since first validate run (spike report requirement).
5. **FR-2.5** Expose backfill via Flask CLI **if practical in same effort** (`flask import-data backfill-source-urls --source FAA_AIDS`); otherwise document one-liner Python invocation. Full CLI restore is not required for v1 sign-off.

### Phase 3 — UX bar (MUST)

1. **FR-3.1** **Aircraft incident list** (`incident_list.html`): show “Details ↗” only when `resolve_source_href()` returns a non-null URL.
2. **FR-3.2** When no URL: show **“No external link”** plus contextual FAQ where applicable:
   - Preliminary WA / no docket
   - Foreign-led NTSB (`cm_agency: Other`) — already implemented; verify on `/aircraft/70`
3. **FR-3.3** **Do not** expand CAROL heuristics further in v1 — current `carol_detail_has_public_content()` + foreign-led check is sufficient.
4. **FR-3.4** Primary source priority unchanged: NTSB > FAA_AIDS > FAA_SDR > ASN > MEDIA.

### Phase 4 — Verification & sign-off (MUST)

1. **FR-4.1** Coverage query: % of incidents with ≥1 active resolvable URL — target **≥90%**.
2. **FR-4.2** Manual QA: Boeing 747 (`/aircraft/70`), one FAA-heavy model (e.g. 737), confirm majority of rows link to ASIAS.
3. **FR-4.3** Confirm Bishkek row (DCA17RA058) shows no dead CAROL/docket links.
4. **FR-4.4** Mark PRD 0001 task **6.6** (spike sign-off) complete when product approves this PRD execution.
5. **FR-4.5** Update `JOURNAL.md` with v1 ship entry and final coverage numbers.

---

## 5. Non-Goals (Out of Scope for v1)

1. **Merging v2 → `main`** or redeploying portfolio — separate decision after v2 QA.
2. **`global_incident_list.html`** link-helper parity — deferred to v1.1 or later.
3. **In-app narrative** for foreign-led NTSB when no public URL — deferred.
4. **Fuzzy or exact FAA↔NTSB merge** — already evaluated (0 pairs); not revisiting.
5. **`enrich-linkless-incidents`** / MEDIA web search tier — deferred.
6. **Full Flask CLI restore** (all import-data subcommands) — only FAA backfill path required.
7. **Full-app QA pass** on every aircraft model — smoke test only (747 + one other).
8. **Perfect CAROL coverage** for every preliminary WA investigation — accept FAQ fallback.
9. **100% link coverage** — some incidents will legitimately have no public record.

---

## 6. Design Considerations

### UI / copy

| State | Display |
|-------|---------|
| Resolvable FAA ASIAS URL | **“Details ↗”** → ASIAS record (primary) |
| Resolvable NTSB CAROL (when heuristic passes) | **“Details ↗”** → CAROL investigation |
| NTSB with report PDF | Optional **“NTSB Docs ↗”** secondary link (existing) |
| No resolvable URL | **“No external link”** + italic FAQ link |
| Foreign-led NTSB | **“Foreign-led investigation (NTSB accredited rep only) — why?”** |
| Preliminary WA only | **“Preliminary NTSB record (no public docket) — why?”** |

### Link labels (FAA)

- Primary: **“FAA AIDS record”** or **“FAA ASIAS”** (match existing multi-link pattern).
- Secondary catalog: **“FAA accident/incident data (catalog)”** — never labeled as the specific event.

### Portfolio isolation

- No changes required on `main` for v1 to be “done.”
- v2 remains deployable locally (`run.py` port 5001) for dogfooding before any portfolio cutover discussion.

---

## 7. Technical Considerations

### Dependencies

| Artifact | Location |
|----------|----------|
| Spike report (GO) | `Planning/spike-reports/0001-faa-aids-url-spike-report.md` |
| URL spec | Spike report § “Winning URL builder spec” |
| Backfill module | `app/ingestion/backfill_urls.py` |
| Link resolution | `app/link_helpers.py` → `url_builders/faa_aids.py` |
| DB | `data/aircraft_safety.db` (~157,342 active FAA_AIDS) |

### Implementation touchpoints

| File | Change |
|------|--------|
| `app/ingestion/url_builders/faa_aids.py` | ASIAS direct URL as primary |
| `app/ingestion/importers/faa_aids_importer.py` | Set `source_url` on import |
| `app/ingestion/backfill_urls.py` | Batch refresh FAA_AIDS (likely no logic change) |
| `app/ingestion/cli.py` | Optional: register backfill command |
| `tests/test_faa_aids_importer.py` or new | URL builder unit tests |

### Operational constraints

- **SQLite:** one writer at a time; stop Flask dev server during backfill if needed.
- **Rate limits:** backfill writes to DB only (no HTTP per row required if URL is deterministic). Spike validation used ≤1 req/s for probes.
- **Rollback:** backfill should be idempotent; keep pre-backfill DB backup or document `git stash` + SQL restore if catastrophic.

### Risks

| Risk | Mitigation |
|------|------------|
| ASIAS URL structure changes | Spike 24h stability re-run; catalog fallback retained |
| Backfill locks SQLite for hours | Batch + off-hours run; single process |
| v2 accidentally merged to `main` | PR policy: target v2 branch only; no merge without explicit portfolio cutover PRD |
| Coverage below 90% | Investigate rows missing `source_record_id`; report in JOURNAL |

---

## 8. Success Metrics

| Metric | Baseline | v1 target |
|--------|----------|-----------|
| FAA_AIDS rows with non-empty `source_url` | 1 / 157,342 | **≥95%** of rows with valid `source_record_id` |
| Incident-level link coverage (≥1 active resolvable URL) | ~32% | **≥90%** (stretch ~97%) |
| Boeing 747 top-50 rows with working link or honest no-link | Low trust | **≥90%** useful or explicit no-link |
| Dead CAROL/docket links for `cm_agency=Other` | User-reported (Bishkek) | **0** |
| Placeholder (`example.com`) links in UI | 0 (fixed) | **0** |
| v2 commits on branch without touching `main` | — | **Yes** |

### v1 complete definition

All of:

- [x] Phase 0 commit on v2
- [x] FAA builder + importer updated
- [x] Backfill run complete with logged stats
- [x] Coverage ≥90%
- [x] 747 + one aircraft smoke QA passed
- [x] JOURNAL entry written
- [x] Product declares **Link Enrichment v1 done** — freeze for ≥1 week

---

## 9. Decisions (confirmed 24 May 2026)

| # | Topic | Decision |
|---|--------|----------|
| 1 | **Branch** | Stay on **`v2-(first-round-of-feedback-from-RJ)`**. All PRD 0002 work here. |
| 2 | **`main` branch** | **Frozen portfolio deployment.** Do not overwrite or merge until v2 is clearly better and product approves cutover. |
| 3 | **Spike outcome** | **GO** — direct ASIAS URL (100% on 500-row sample). Proceed to Phase 2. |
| 4 | **Scope** | FAA backfill + checkpoint commit + UX bar freeze. No global list parity, no in-app narrative, no enrich-linkless. |
| 5 | **UX philosophy** | Useful outbound link **or** honest “no public record” + FAQ. Stop perfecting CAROL heuristics in v1. |
| 6 | **Post-ship** | No link enrichment work for **≥1 week** unless production bug. |
| 7 | **Go/no-go for v1 ship** | **Product lead** — same authority as spike sign-off. |

---

## 10. Execution Plan (estimated 2–3 days)

### Day 0 — Checkpoint (~1 hour)

1. Review uncommitted diff on v2.
2. Commit baseline (link helpers, NTSB foreign-led, spike artifacts, docs).
3. Push v2 to remote (optional but recommended — portfolio safety net).

### Day 1 — Implement (~1 day)

1. Re-run stability script if ≥24h since validate.
2. Implement `faa_aids.py` URL builder + importer hook.
3. Add unit tests.
4. Dry-run backfill on 100 rows; verify ASIAS URLs in browser.

### Day 2 — Backfill & verify (~1 day)

1. Full FAA_AIDS backfill in 5k batches.
2. Run coverage query.
3. Smoke QA: `/aircraft/70`, one FAA-heavy aircraft.
4. JOURNAL entry + mark v1 done.

### Day 3 — Buffer

- Fix backfill edge cases only if coverage <90%.
- **Do not** start deferred items (global list, narrative, enrich-linkless).

---

## 11. Relationship to PRD 0001

| PRD 0001 (Spike) | PRD 0002 (This doc) |
|-----------------|---------------------|
| Prove URL exists | **Implement** URL |
| 500-row sample | **157k-row backfill** |
| Report + GO | **Ship + freeze** |
| Blocked Phase 2 | **Phase 2 is the product** |

Spike task **6.6** (product sign-off) closes when product approves execution of this PRD.

---

## Appendix A: Current state (24 May 2026)

- **Branch:** `v2-(first-round-of-feedback-from-RJ)` — uncommitted link + spike work
- **DB:** ~242k incidents; ~32% with ≥1 active link
- **FAA gap:** 157,342 FAA_AIDS; 1 with URL
- **Already fixed (uncommitted):** foreign-led NTSB skip, link helpers, `incident_list.html`
- **Deferred:** `global_incident_list.html`, 2 stale tests in `test_source_links.py`

## Appendix B: Related files

- Spike report: `Planning/spike-reports/0001-faa-aids-url-spike-report.md`
- Context snapshot: `context/context-2026-05-24.md`
- Engineering log: `JOURNAL.md`
- PRD process: `Planning/Prompts/PROMPT_create-prd(ryan carson).md`

---

*Next step: generate task list via `PROMPT_generate-tasks(ryan carson).md` → `tasks-0002-prd-link-enrichment-v1-ship.md`*
