# Product Requirements Document: Taxonomy Rollup (Boeing/Airbus Family Pages)

**Project ID:** 0004  
**Created:** 24 May 2026  
**Author:** Product (with CTO)  
**Status:** Shipped — Phase 1 live (24 May 2026); Phase 2 expansion deferred  
**Parent initiative:** Link enrichment follow-on (PRD 0002 shipped, PRD 0003 shipped)  
**Branch policy:** `v2-(first-round-of-feedback-from-RJ)` only — **`main` frozen (portfolio)**

---

## 1. Introduction/Overview

### Problem statement

PRD 0003 attached **5,877 FAA Boeing/Airbus incidents** to aircraft profiles and raised aggregate Boeing link rates to **~82%**. Users still see **empty or NTSB-only family pages** when they search for familiar model names (e.g. `737-300`, `747`).

| Page | User expectation | Reality today |
|------|------------------|---------------|
| `/aircraft/88` — `BOEING 737-300` | FAA + NTSB incidents for the 737-300 family | **50 incidents, 0 FAA** (NTSB-heavy) |
| `/aircraft/877` — `Boeing 7373H4` | (user never searches this) | **98 FAA incidents** |
| `/aircraft/70` — `BOEING 747` | Complete 747 history | Mostly NTSB; FAA on child variants only |

**Root cause:** Incidents are bucketed by **exact `aircraft.model_name`**. FAA bulk uses collapsed variant strings (`7373H4`, `737322`); NTSB and search use **family names** (`737-300`, `747`). Same data, different buckets — family pages look broken even after link enrichment.

### Solution (this PRD)

Introduce **taxonomy rollup** for **Boeing and Airbus only**:

1. **Designate canonical family pages** (A) — the `aircraft` row users search for and land on.
2. **Map variant profiles to families via explicit rules** (B) — no fuzzy guessing; a maintained rules table.
3. **Query rollup** — family `/aircraft/{id}` incident lists include incidents from all mapped member `aircraft_id`s.
4. **Keep variant URLs working** (3A) — `/aircraft/877` still loads; search/nav prefer family pages.

### Goal

When a user searches for a Boeing/Airbus **family name** and opens the profile page, they see **all incidents for that family** — including FAA ASIAS links that today only appear on obscure variant pages.

**Success in one sentence:** `/aircraft/88` shows FAA rows if any mapped child variant (877, 964, 927, …) has FAA data.

---

## 2. Goals

### Primary goals

1. Family profile pages aggregate incidents from explicitly mapped child variant `aircraft_id`s.
2. Any Boeing/Airbus page **reachable from homepage search** resolves to a family page that includes rolled-up FAA data where children have it.
3. Variant profile pages remain accessible (no redirects in v1).
4. No incident deduplication in v1 — show all rows from family + members.

### Secondary goals

1. Search/autocomplete prefer **canonical family `aircraft_id`** over variant IDs when both match.
2. Seed rules for high-traffic demo families first; framework to expand to full Boeing/Airbus catalog.
3. Dry-run report: per-family before/after incident counts and FAA link counts.
4. Document rule maintenance process in `JOURNAL.md`.

### Non-goals

See §5.

---

## 3. User Stories

**As a** portfolio visitor searching “737-300”,  
**I want** the incident list to include FAA events recorded against `7373H4`, `737322`, etc.,  
**So that** I don’t think the app has no FAA data for this model.

**As a** product owner reviewing RJ feedback,  
**I want** family names in search to land on pages that look complete,  
**So that** we don’t explain variant-level taxonomy to non-expert users.

**As an engineer**,  
**I want** explicit family→member rules (not regex-only magic),  
**So that** rollups are auditable and we never attach a 737 NG incident to a 737 Classic page.

**As an engineer**,  
**I want** variant URLs to keep working,  
**So that** we don’t break bookmarks or post-attach spot-checks.

---

## 4. Functional Requirements

### FR-1: Scope (MUST)

1. **FR-1.1** Rollup applies only when `aircraft.manufacturer` is **Boeing** or **Airbus** (case-insensitive).
2. **FR-1.2** **General Aviation** (Cessna, Piper, Beech, etc.) — **no rollup**. Existing GA pages unchanged.
3. **FR-1.3** Rollup is **read/query-time only** — do not move or duplicate `incident.aircraft_id` rows in v1.

### FR-2: Canonical family pages (MUST — decision A)

1. **FR-2.1** Each rollup family has exactly one **canonical `aircraft_id`** — the page users search for (e.g. id 88 = `BOEING 737-300`).
2. **FR-2.2** Canonical families are **designated explicitly** in config/rules — not inferred at query time from “shortest model name” alone.
3. **FR-2.3** A canonical family row may have **zero direct incidents** today; rollup still shows member incidents.

### FR-3: Explicit member rules (MUST — decision B)

1. **FR-3.1** Maintain an **`aircraft_family_member`** (or equivalent) table:

   | Column | Purpose |
   |--------|---------|
   | `family_aircraft_id` | Canonical family page |
   | `member_aircraft_id` | Variant/child profile whose incidents roll up |
   | `created_at` | Audit |

   Unique constraint on `(family_aircraft_id, member_aircraft_id)`.

2. **FR-3.2** Membership is **explicit** — each row is a deliberate mapping. Optional helper script may *suggest* mappings from model-string patterns; **human or dry-run review approves** before insert.
3. **FR-3.3** A member `aircraft_id` maps to **at most one** family (no dual rollup).
4. **FR-3.4** Family `aircraft_id` is implicitly a member of itself (include direct incidents + member incidents).
5. **FR-3.5** **Unmapped** variant pages behave as today — show only their own incidents until a rule exists.

### FR-4: Incident query rollup (MUST)

1. **FR-4.1** `/aircraft/<id>` and `/aircraft/<id>/incidents` query incidents where `incident.aircraft_id IN (family_id ∪ member_ids)`.
2. **FR-4.2** Existing filters (date, type, system, source) apply to the rolled-up set.
3. **FR-4.3** Existing sort order (`apply_source_priority_order`) unchanged.
4. **FR-4.4** **No deduplication** in v1 — if the same event appears on family and member (unlikely without merge), show both rows (decision 4C).
5. **FR-4.5** CSV export uses the same rolled-up incident set.
6. **FR-4.6** Stats on family page header (total incidents, fatalities) should reflect rolled-up counts **or** show a clear “family view” label — product prefers **rolled-up counts** for demo clarity.

### FR-5: Search integration (MUST — decision 5B)

1. **FR-5.1** Homepage search and autocomplete for Boeing/Airbus return **canonical family `aircraft_id`** when the match is a mapped member variant.
2. **FR-5.2** Any Boeing/Airbus result reachable from search must either:
   - **(a)** Be a canonical family with complete rollup rules for its members, **or**
   - **(b)** Be an unmapped leaf page that already owns its incidents (no false empty state).
3. **FR-5.3** Search grouping (`/search` series buckets) should not bury family pages under variant-only entries when a canonical family exists.

### FR-6: Variant pages (MUST — decision 3A)

1. **FR-6.1** `/aircraft/{member_id}` continues to show **member-only** incidents (no reverse rollup to family).
2. **FR-6.2** Optional UI hint on variant page: “Also view [Family name] for all variants” — **SHOULD**, not blocking.

### FR-7: CLI & seed data (SHOULD)

1. **FR-7.1** `flask import-data seed-family-rules --dry-run` — report proposed mappings, incident/FAA counts per family.
2. **FR-7.2** `flask import-data seed-family-rules` — apply approved seed file (YAML/CSV in repo).
3. **FR-7.3** Seed file checked into `data/aircraft_family_members.csv` (or `Planning/artifacts/`) with initial demo families.

### FR-8: Link resolution (MUST — inherits PRD 0002/0003)

1. **FR-8.1** No change to `resolve_source_href` / URL builders — rollup is query-only.
2. **FR-8.2** Rolled-up FAA rows display existing ASIAS links from `incident_list.html`.

---

## 5. Non-Goals (Out of Scope)

1. **GA rollup** — Cessna/Piper/etc. stay per exact `aircraft_id`.
2. **Incident deduplication** — no date+reg merge on family view (v1).
3. **Moving `incident.aircraft_id`** — no data migration re-parenting incidents to family rows.
4. **Fuzzy family inference** — no ML, no “closest string match” without an explicit rule row.
5. **Redirect variant → family** — deferred (decision 3A: keep both).
6. **FAA attach changes** — PRD 0003 logic unchanged; rollup surfaces existing attached rows.
7. **NTSB foreign-led / DirectorBrief fixes** — separate/in-flight work; rollup does not fix dead NTSB links.
8. **`global_incident_list.html`** rollup — deferred.
9. **Merging v2 → `main`** — separate portfolio decision.

---

## 6. Design Considerations

### UX

- Family page incident count **will increase** (e.g. 737-300 from 50 → 400+). Existing **limit 50** per page still applies — consider noting “showing latest 50 of N” if not already visible.
- Users may see **more 1980s FAA rows** mixed with modern NTSB — acceptable for v1 (no dedupe).
- Variant column/filter may need to show **member model name** when incident comes from a child profile — **SHOULD** display `aircraft.model_name` or `raw_model_variant` on each row for clarity.

### Search mental model

```
User types "737-300"
  → autocomplete returns canonical id=88
  → page shows incidents from ids {88, 877, 964, 927, …}
  → FAA links visible
```

### Phased rollout

| Phase | Scope |
|-------|--------|
| **Phase 1** | Seed rules for demo families: 737 Classic (−300/−400/−500), 737 NG, 737 MAX, 747, 777, 767, 757, 727, A320 family, A330, A350, A380 |
| **Phase 2** | Expand rules until **every Boeing/Airbus search result** satisfies FR-5.2 (decision 5B) |

---

## 7. Technical Considerations

### Touchpoints

| File / object | Change |
|---------------|--------|
| New migration | `aircraft_family_member` table |
| `data/aircraft_family_members.csv` | Seed mappings (family_id, member_id) |
| `app/models.py` | `AircraftFamilyMember` model |
| `app/services/aircraft_family.py` (new) | `get_family_member_ids(family_id)`, `resolve_canonical_family(aircraft_id)` |
| `app/routes.py` | `aircraft_details`, `get_incidents`, `export_incidents_csv` — use rolled-up query |
| `app/routes.py` | `search`, `search_autocomplete` — prefer canonical family id |
| `app/ingestion/cli.py` | `seed-family-rules` command |
| `tests/test_aircraft_family_rollup.py` | Unit + integration tests |

### Query pattern (sketch)

```python
def incident_query_for_aircraft(aircraft_id: int):
    member_ids = get_family_member_ids(aircraft_id)  # includes self
    return Incident.query.filter(Incident.aircraft_id.in_(member_ids))
```

### Example seed (737 Classic)

| family_aircraft_id | member_aircraft_id | member model_name |
|-------------------:|-------------------:|-------------------|
| 88 | 88 | BOEING 737-300 |
| 88 | 877 | Boeing 7373H4 |
| 88 | 964 | Boeing 737322 |
| 88 | 927 | Boeing 737300 |
| … | … | (explicit rows — no wildcard-only config in prod) |

### Baseline metrics (24 May 2026)

| Metric | Value |
|--------|------:|
| Boeing/Airbus `aircraft` rows | 1,266 |
| Aircraft with ≥1 FAA incident | 571 |
| `/aircraft/88` direct incidents | 50 (0 FAA) |
| `/aircraft/877` direct incidents | 98 FAA |
| Orphan unmapped variants with FAA | Many (require Phase 1 seed) |

### Risks

| Risk | Mitigation |
|------|------------|
| Wrong family mapping (737 NG → Classic) | Explicit rules only; dry-run counts; no auto-apply wildcards without review |
| Page performance (large `IN` clause) | Index on `incident.aircraft_id`; typical family < 30 members |
| Duplicate-looking rows | Accept for v1; document; dedupe is future PRD |
| Search regression | Test autocomplete for top 20 queries |
| Stats/summary drift | Recompute rolled-up totals or label “family view” |

---

## 8. Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| `/aircraft/88` shows ≥1 FAA-linked incident | **0** | **≥1** (ideally ~400 rolled-up) |
| Canonical family pages with FAA children show FAA links | Unknown | **100%** of Phase 1 seed families |
| Boeing/Airbus search results landing on empty FAA family pages | Many | **0** for mapped families |
| Wrong-family incident on QA spot-check | — | **0** |
| Variant URL breakage | — | **0** |

### Acceptance (decision 7A)

- [ ] Phase 1 seed file reviewed and applied
- [ ] `/aircraft/88` (737-300) shows FAA ASIAS links from child variants
- [ ] `/aircraft/70` (747) shows FAA from mapped 747 variants where they exist
- [ ] Search “737-300”, “747”, “A320” → canonical family pages with rolled-up data
- [ ] `/aircraft/877` still works (member-only view)
- [ ] Dry-run + before/after JSON artifact
- [ ] Tests pass; `JOURNAL.md` updated; `main` untouched

---

## 9. Decisions (confirmed 24 May 2026)

| # | Topic | Decision |
|---|--------|----------|
| 1 | **Manufacturers** | Boeing + Airbus only |
| 2 | **Family model** | **A + B:** canonical family pages + explicit member rules table |
| 3 | **Variant pages** | Keep working; family aggregates; no redirects v1 |
| 4 | **Dedupe** | None in v1 |
| 5 | **Search bar** | Every Boeing/Airbus search result must land on a complete family or legitimate leaf page |
| 6 | **GA** | No GA rollup |
| 7 | **Success** | Family pages show FAA when mapped children have FAA |

---

## 10. Execution Plan (estimated 2–3 days)

### Phase 1 — Schema + query rollup

1. Migration: `aircraft_family_member`.
2. `get_family_member_ids()` helper.
3. Update `aircraft_details` / incidents partial / CSV export.
4. Unit tests with fixture family + members.

### Phase 2 — Seed rules + dry-run

1. Build seed CSV for demo families (737 Classic, 747, A320, …).
2. CLI dry-run: before/after incident + FAA counts per family.
3. Product review of mapping sheet.

### Phase 3 — Search + QA

1. Autocomplete/search prefer canonical family id.
2. Spot-check hero searches and RJ-relevant pages.
3. `JOURNAL.md` + mark PRD shipped.

---

## Appendix A: Why not move `incident.aircraft_id`?

PRD 0003 deliberately set `aircraft_id` on orphan FAA rows to **variant** profiles via exact `resolve_aircraft()` match. Re-parenting thousands of rows to family ids would:

- Break variant-only views
- Require a new migration with rollback risk
- Conflate attach semantics with display semantics

Query-time rollup achieves the UX win without a data rewrite.

## Appendix B: Related docs

- PRD 0002: Link Enrichment v1 (FAA URLs — shipped)
- PRD 0003: Boeing/Airbus FAA Profile Attach (shipped)
- `app/routes.py` — search grouping, `aircraft_details`
- Conversation baseline: `/aircraft/88` vs `/aircraft/877` FAA split

---

*Next step: `PROMPT_generate-tasks(ryan carson).md` → `tasks-0004-prd-taxonomy-rollup.md`*
