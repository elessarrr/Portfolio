# Task List: Taxonomy Rollup (Boeing/Airbus Family Pages)

**PRD Reference:** `Planning/tasks/0004-prd-taxonomy-rollup.md`  
**Parent PRD:** `0003-prd-boeing-airbus-faa-profile-attach.md` (FAA attach — shipped)  
**Created:** 24 May 2026  
**Completed:** 24 May 2026  
**Branch:** `v2-(first-round-of-feedback-from-RJ)` only — **`main` is frozen (portfolio)**  
**Decision owner:** Product lead

---

## Relevant Files

### Created

- ⭐ `migrations/versions/b7c4e1f2a903_add_aircraft_family_member.py` — family member table (merge migration).
- ⭐ `app/services/aircraft_family.py` — rollup query helpers.
- ⭐ `app/ingestion/family_rules_seed.py` — CSV seed + dry-run summary.
- `data/aircraft_family_members.csv` — 751 explicit mappings (15 Phase 1 families).
- `tests/test_aircraft_family_rollup.py` — 7 tests.
- `Planning/artifacts/family-rollup-summary.json` — dry-run/live summary.

### Updated

- `app/models.py` — `AircraftFamilyMember` model.
- `app/routes.py` — rollup on aircraft pages, search/autocomplete canonical resolution.
- `app/templates/aircraft.html` — family view label, variant hint, “latest 50 of N”.
- `app/templates/components/stats_grid.html` — rolled-up stats.
- `app/ingestion/cli.py` — `seed-family-rules` command.
- `JOURNAL.md` — ship entry.

### Post-run results (24 May 2026)

| Family | Before incidents | After | Before FAA | After FAA |
|--------|----------------:|------:|-----------:|----------:|
| `/aircraft/88` 737-300 | 50 | **676** | 0 | **566** |
| `/aircraft/70` 747 | 106 | **757** | 7 | **439** |
| `/aircraft/18` A320 | 224 | **640** | 0 | **208** |
| `/aircraft/877` 7373H4 (member-only) | 98 | **98** | 98 | **98** |

Phase 2: **155** unmapped Boeing/Airbus aircraft with FAA remain.

---

## Tasks

- [x] **0.0–10.0** All Phase 1 tasks complete (schema, service, routes, seed, search, tests, QA, ship).
- [ ] **9.0 Phase 2 expansion** — deferred; 155 unmapped FAA variant pages remain.

---

## Completion checklist

- [x] Migration applied; 751 family member rows seeded
- [x] `/aircraft/88` shows FAA ASIAS links (566 rolled-up)
- [x] Search “7373” → canonical id 88
- [x] `/aircraft/877` member-only unchanged (98 incidents)
- [x] Tests pass (7/7); JOURNAL updated; `main` untouched

---

*Shipped Phase 1 — 24 May 2026 via autonomous session.*
