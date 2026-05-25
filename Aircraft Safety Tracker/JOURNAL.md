# Engineering Log & Knowledge Journal

> **Format (per AGENTS.md):** One entry per completed task / major bug / schema learning.  
> **1–2 sentences each.** Detailed history lives in PRDs, commits, and `Planning/`.

**Branch:** `v3-boeing-airbus-links` · branched from `origin/main`  
**DB:** `data/aircraft_safety_v3.db` · **App:** `http://127.0.0.1:5001`

---

## May 2026 (chronological, newest first)

- **2026-05-25** — *PRD 0005 ASN-only DB bridge.* Clean v3 DB rebuilt from v2 aircraft + ASN-linked incidents only: **1,266 aircraft**, **1,796 incidents**, **0 `IncidentSource` rows**; every copied incident has `asn_url` and representative pages render Details links with no `N/A`.
- **2026-05-24** — *Step 3 NTSB slice.* `url_builders/ntsb.py` + minimal `NTSBImporter` (Boeing/Airbus gate, single `source_url`, no CAROL for Other/DirectorBrief); foreign-led FAQ in incident list; **28 pytest** green.
- **2026-05-24** — *Step 2 ASN regression.* `test_incident_list_renders_asn_details_href`; ASN import unchanged.
- **2026-05-24** — *Step 1 shipped.* `source_record_id` + `is_active` on `IncidentSource`; `link_schema.py` + `link_picker.py`; batch source load in routes; shared macro; **22 pytest** green.
- **2026-05-24** — *Dev DB policy documented.* Fresh SQLite for link arc; never attach v2 DB. See `README.md` § Local Development Setup.
- **2026-05-24** — *Step 0 complete.* Branched `v3-boeing-airbus-links` from `origin/main`; baseline test suite: **15 passed, 0 failures**. Plan doc: `.cursor/plans/2405_new_branch_plan_676fa222.plan.md`.

---

## Current state (snapshot)

| Area | Status |
|------|--------|
| Branch baseline | **28 tests** green |
| `IncidentSource` | `source_record_id`, `is_active`, indexes + unique constraint |
| `link_schema` / `link_picker` | Placeholder + catalog rejection; ASN → NTSB → FAA_AIDS |
| url_builders | `ntsb.py` (single-URL, CAROL gating) |
| Importers | `NTSBImporter` code exists; NTSB/FAA data imports deferred |
| ASN baseline | `data/aircraft_safety_v3.db` has 1,796 ASN-linked incidents and 0 source rows |
| Dev DB policy | Use clean v3 DB; keep v2 `data/aircraft_safety.db` as read-only source backup |

---

## Key learnings (durable — carried from v2 debrief)

- **FAA URLs:** `P12_AIDS_RPRT_NBR:{source_record_id}` from bulk `c5` — 100% on spike sample.
- **NTSB CAROL:** HTTP 200 SPA shell ≠ public content; skip when `cm_agency=Other` or `cm_reportType=DirectorBrief`.
- **Exact FAA↔NTSB merge:** 0 pairs at dry-run — orphan FAA events are different incidents, not dupes.
- **Anti-patterns to avoid:** See `Planning/branch-debrief-v2.md` §4 — 11 explicit rules.
- **`IncidentSource` discipline:** single `source_url` resolved at import; no JSON-blob link resolution; no catalog/placeholder URLs.
