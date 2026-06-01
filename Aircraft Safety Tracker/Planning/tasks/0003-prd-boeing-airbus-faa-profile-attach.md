# Product Requirements Document: Boeing/Airbus FAA Profile Attach (Exact Match Only)

**Project ID:** 0003  
**Created:** 24 May 2026  
**Author:** Product (with CTO)  
**Status:** Shipped — 24 May 2026 (live attach: 5,877 rows)  
**Parent initiative:** Link enrichment v1 follow-on (Boeing/Airbus scope only)  
**Branch policy:** `v2-(first-round-of-feedback-from-RJ)` only — **`main` frozen (portfolio)**

---

## 1. Introduction/Overview

### Problem statement

Link Enrichment v1 backfilled **157,341 FAA ASIAS URLs**, but **Boeing/Airbus aircraft profile pages barely improved**:

| Manufacturer | Profile incidents | With live link today | No link |
|--------------|------------------:|---------------------:|--------:|
| **Boeing** | 3,416 | 1,867 (**54.7%**) | 1,549 |
| **Airbus** | 2,091 | 1,780 (**85.1%**) | 311 |

Root causes:

1. **~6,848 FAA Boeing/Airbus rows have ASIAS URLs but `aircraft_id IS NULL`** — they never appear on `/aircraft/{id}` pages.
2. **Most no-link profile rows are NTSB foreign-led or preliminary** (~1,437 Boeing) — no public outbound page exists; FAA backfill does not help those rows without a merge.
3. **Exact FAA↔NTSB merge on date+registration finds 0 pairs** in dry-run — orphan FAA events are largely *different* incidents from NTSB profile rows, not duplicates.

We only care about **Boeing and Airbus**. The 150K+ GA FAA links are out of scope.

### Solution (this PRD)

Two tracks — **exact match only**, no fuzzy merge:

| Track | Action | Dry-run yield |
|-------|--------|---------------|
| **A — Attach** | Set `aircraft_id` on orphan FAA Boeing/Airbus incidents via existing `resolve_aircraft()` | **5,877 / 6,848 (85.8%)** |
| **B — Exact merge** | When **same date + normalized registration**, attach FAA `IncidentSource` to existing profile incident that has **no resolvable link** | **0 pairs today** (still implement; safe guardrail) |

Track A adds **new FAA-linked rows** to model pages. Track B fixes existing no-link rows only when an exact duplicate exists in FAA data.

### Goal

Increase **live outbound links on Boeing/Airbus `/aircraft/{id}` pages** by surfacing FAA ASIAS URLs where we can confidently attach them — without sending users to the wrong incident page.

---

## 2. Goals

### Primary goals

1. Backfill `aircraft_id` on orphan **FAA Boeing/Airbus** incidents where `resolve_aircraft()` succeeds.
2. Implement **exact-only** FAA→profile merge: `exact_date_registration` rule only (score = 1.0, same calendar date, normalized registration match).
3. When a profile incident has no resolvable link and receives an exact FAA match, **FAA ASIAS becomes the primary Details link**.
4. Raise Boeing profile link rate measurably (target **≥65%** of incidents on Boeing models with ≥1 FAA attach).

### Secondary goals

1. Log attach failures (`resolve_aircraft` rejections) for manual review.
2. Dry-run CLI before production write.
3. Update coverage metrics in `JOURNAL.md`.

### Non-goals

See §5.

---

## 3. User Stories

**As a** user browsing a Boeing 737 profile,  
**I want** incident rows to include FAA ASIAS “Details ↗” links when FAA recorded that event for this model,  
**So that** I can verify the incident on an official source.

**As a** product owner,  
**I want** exact-match-only merging (date + registration),  
**So that** we never attach a FAA link to the wrong NTSB incident.

**As an engineer**,  
**I want** a dry-run mode with counts before writing 6K+ rows,  
**So that** I can validate attach rates without risking bad data.

---

## 4. Functional Requirements

### FR-1: Scope filter (MUST)

1. **FR-1.1** Only process `IncidentSource` where `source_name='FAA_AIDS'`, `is_active=1`, `source_url` contains `asias.faa.gov`.
2. **FR-1.2** Only process makes where `UPPER(source_data.c23)` starts with `BOEING` or `AIRBUS`.
3. **FR-1.3** Ignore all other manufacturers (Cessna, Piper, etc.).

### FR-2: Aircraft attach backfill (MUST — Track A)

1. **FR-2.1** For orphan FAA rows (`incident.aircraft_id IS NULL`), build `make_model` from `c23` + `c24`.
2. **FR-2.2** Call `FAAAIDSImporter.resolve_aircraft()` (or shared base helper) — reuse existing exact/prefix/auto-create logic for Boeing/Airbus.
3. **FR-2.3** If `aircraft_id` resolved, update `incident.aircraft_id` (batch commits, single SQLite writer).
4. **FR-2.4** Do **not** create duplicate `Incident` rows — update existing orphan incident in place.
5. **FR-2.5** Dry-run mode: report would-attach count, target model breakdown, failures — no writes.

### FR-3: Exact merge (MUST — Track B)

1. **FR-3.1** Merge rule: **`exact_date_registration` only** — same `incident.date` (calendar day) AND normalized registration (`[^A-Z0-9]` stripped, uppercased).
2. **FR-3.2** Candidate target: Boeing/Airbus profile incident with **no resolvable link** (`resolve_source_href` returns `None` for all active sources).
3. **FR-3.3** Candidate source: orphan FAA Boeing/Airbus incident (before or after attach) with same date+reg.
4. **FR-3.4** If **exactly one** FAA candidate matches → reparent FAA `IncidentSource` to target incident (reuse `incident_linker._reparent_sources` pattern).
5. **FR-3.5** If **0 or >1** FAA candidates → **skip** (log as `ambiguous` or `no_match`). **No fuzzy scoring, no date windows, no location/operator similarity.**
6. **FR-3.6** After reparent, delete orphan incident if empty.

### FR-4: UI / link resolution (MUST)

1. **FR-4.1** No template change required if FAA source is on incident and `resolve_source_href` works (already implemented in `incident_list.html`).
2. **FR-4.2** Source priority remains NTSB > FAA_AIDS — but when NTSB has no resolvable URL, FAA becomes effective primary.
3. **FR-4.3** Foreign-led NTSB rows remain no-link + FAQ (unchanged).

### FR-5: CLI & observability (SHOULD)

1. **FR-5.1** `flask import-data attach-faa-boeing-airbus --dry-run` (or script) with summary: attached, merge_linked, skipped, failed, ambiguous.
2. **FR-5.2** Write summary JSON to `Planning/artifacts/` or log in `JOURNAL.md`.

---

## 5. Non-Goals (Out of Scope)

1. **Fuzzy merge** — no date windows, no location/operator similarity, no `min_score` thresholds below 1.0.
2. **Non-Boeing/Airbus** FAA attach (GA fleet).
3. **New FAA URL research** — ASIAS URLs done (PRD 0002).
4. **In-app narrative** for foreign-led NTSB — separate PRD if needed.
5. **`global_incident_list.html`** link helpers — deferred from v1.
6. **Merging v2 → `main`** — portfolio cutover is a separate decision.
7. **Fixing `resolve_aircraft` validation** for edge cases (e.g. `BOEING A75N1`) unless attach rate blocks success metric.

---

## 6. Design Considerations

### UX

- New FAA-attached rows appear in existing aircraft incident table (newest first, limit 50 unchanged).
- Users may see **more incident rows** on 727/737/757 profiles — mostly 1980s FAA data.
- **747 profile may still show few FAA links** if FAA bulk has few 747-attached rows after `resolve_aircraft`.

### Duplicate rows vs merged rows

- Dry-run shows **0 exact merges** today → most gain is **new rows**, not fixing existing 1,549 Boeing no-link rows.
- Foreign-led NTSB no-link rows (**~1,437 Boeing**) will **remain** without outbound links unless we ship in-app narrative (out of scope).

---

## 7. Technical Considerations

### Touchpoints

| File | Change |
|------|--------|
| New script or `app/ingestion/linking/faa_profile_attach.py` | Attach + exact merge orchestration |
| `app/ingestion/importers/base.py` | `resolve_aircraft()` (read-only reuse) |
| `app/ingestion/linking/incident_linker.py` | Reparent helpers (read-only reuse) |
| `app/ingestion/cli.py` | Register command |
| `tests/test_faa_profile_attach.py` | Exact match unit tests |

### Exact match spec

```python
def exact_match_key(date, registration) -> Optional[tuple]:
    reg = re.sub(r"[^A-Z0-9]", "", (registration or "").upper())
    if not date or not reg:
        return None
    return (date.isoformat(), reg)
```

Merge allowed **only** when both sides produce the same key and exactly one FAA incident matches.

### Dry-run results (24 May 2026)

| Metric | Value |
|--------|------:|
| Orphan FAA Boeing/Airbus rows | 6,848 |
| `resolve_aircraft` success | **5,877 (85.8%)** |
| `resolve_aircraft` fail | 971 |
| Top attach targets | Boeing 727 variants, 757, 737 families |
| Profile incidents without link (Boeing+Airbus) | 1,901 |
| **Exact date+reg merge pairs** | **0** |
| Ambiguous exact keys | 0 |

**Current link rates:** Boeing 53.7%, Airbus 84.8%  
**Projected new FAA-linked profile rows (attach only):** up to ~5,877 (distributed across models; not all on 747).

### Risks

| Risk | Mitigation |
|------|------------|
| Wrong model attach (727232 → wrong 727 variant) | Prefix match is existing behavior; document; no fuzzy merge |
| Profile clutter (thousands of 1980s FAA rows) | Optional future: filter by date or source on UI — out of scope |
| 971 attach failures | Log + report; don't force |
| SQLite lock | Single writer; stop Flask during backfill |

---

## 8. Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| FAA Boeing/Airbus orphans with `aircraft_id` set | 0 / 6,848 | **≥5,000 (≥73%)** |
| Boeing models with ≥1 FAA-linked incident | ~1 | **≥50 models** |
| Boeing profile incident link rate | 54.7% | **≥65%** *(may require denominator increase from new rows)* |
| Exact merge wrong-link incidents | — | **0** |
| Fuzzy merge incidents | — | **0** (by design) |

### Acceptance

- [ ] Dry-run reviewed and approved by product
- [ ] Attach backfill executed on v2
- [ ] Exact merge pass executed (even if 0 merges)
- [ ] Spot-check: `/aircraft/` pages for 727, 737, A320 show ASIAS links
- [ ] 747 page: document outcome (likely still NTSB-heavy)
- [ ] `main` untouched

---

## 9. Decisions (confirmed 24 May 2026)

| # | Topic | Decision |
|---|--------|----------|
| 1 | **Manufacturers** | Boeing and Airbus only |
| 2 | **Merge policy** | **Exact date + registration only** — no fuzzy |
| 3 | **Ambiguous exact key** | Skip (>1 FAA row same date+reg) |
| 4 | **Branch** | v2 only; `main` frozen |
| 5 | **Primary lever** | Track A (aircraft_id attach) — merge is guardrail, not expected yield |
| 6 | **747 expectation** | May not improve much; FAA bulk is 727/737-heavy |

---

## 10. Execution Plan (estimated 1–2 days)

### Phase 1 — Implement + dry-run

1. Build `attach_faa_boeing_airbus(dry_run=True)` with FR-1–FR-3 logic.
2. Run dry-run; compare to appendix metrics.
3. Product sign-off on attach counts.

### Phase 2 — Execute attach

1. Stop Flask; run attach backfill (~6K rows).
2. Run exact merge pass.
3. Coverage SQL + spot-check 727/737/A320/747 pages.

### Phase 3 — Document

1. `JOURNAL.md` entry with before/after link rates.
2. Mark PRD shipped.

---

## Appendix A: Why exact merge = 0

Profile no-link incidents are overwhelmingly **NTSB foreign-led** (accredited rep, no public URL). FAA orphan rows are **separate GA/airline events** with different registrations/dates — they don't share exact date+reg with those NTSB rows. Attaching FAA to profiles adds **new** linked incidents rather than fixing existing dead NTSB rows.

## Appendix B: Related docs

- PRD 0002: Link Enrichment v1 (FAA URL backfill — shipped)
- `app/ingestion/dedupe.py` — `exact_date_registration` rule definition
- Dry-run script: ad-hoc 24 May 2026 (reproduce via Phase 1 CLI)

---

*Next step: `PROMPT_generate-tasks(ryan carson).md` → `tasks-0003-prd-boeing-airbus-faa-profile-attach.md`*
