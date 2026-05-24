# Engineering Log & Knowledge Journal

> **Format (per AGENTS.md):** One entry per completed task / major bug / schema learning.  
> **1–2 sentences each.** Detailed history lives in PRDs, commits, and `Planning/`.

**Branch:** `v2-(first-round-of-feedback-from-RJ)` · **`main` frozen (portfolio)**  
**DB:** `data/aircraft_safety.db` · **App:** `http://127.0.0.1:5001`

---

## May 2026 (chronological, newest first)

- **2026-05-24** — *Session wrap-up.* User paused link work (“going in circles”); commit `f3e4d52`. Next: fresh branch or main cutover decision (`context/context-main-branch-asn-links-2026-05-18.md`).
- **2026-05-24** — *PRD 0004 shipped (`5b0dcf5`).* Taxonomy rollup: `aircraft_family_member` + 751 CSV mappings; `/aircraft/88` **0→566 FAA** links via query-time family aggregation; Phase 2 = 155 unmapped FAA variants.
- **2026-05-24** — *747 Delta/Russian airspace bug.* `DirectorBrief` NTSB rows (e.g. ENG16IA001) had bulk narrative but blank CAROL; fix skips CAROL, prefers docket in `ntsb.py` + `link_helpers.py`.
- **2026-05-24** — *PRD 0003 shipped (`4ebff2d`).* FAA profile attach: 5,877 Boeing/Airbus orphans got `aircraft_id`; Boeing link rate **54.7%→81.9%**; exact merge = 0 pairs.
- **2026-05-24** — *PRD 0002 shipped.* FAA ASIAS backfill **157,342/157,342** rows; incident URL coverage **~32%→97%**; foreign-led NTSB FAQ (Bishkek DCA17RA058).
- **2026-05-23** — *Git/Cursor workspace.* Fixed nested repo origin mapping; branch detection from `Aircraft Safety Tracker` subfolder.

---

## Current state (snapshot)

| Area | Status |
|------|--------|
| Link enrichment v1–v4 (PRD 0002–0004) | Shipped on v2 |
| Family rollup Phase 2 | **155** unmapped Boeing/Airbus FAA variant pages |
| `global_incident_list.html` | Still raw URLs — deferred |
| v2 → `main` cutover | Not started; see main-branch ASN brief |
| Pre-existing test failures | 2 in `tests/test_source_links.py` |

---

## Key learnings (durable)

- **FAA URLs:** `P12_AIDS_RPRT_NBR:{source_record_id}` from bulk `c5` — 100% on spike sample.
- **FAA attach ≠ family pages:** Attach lands on variant `aircraft_id`s; rollup (PRD 0004) needed for search-friendly family UX.
- **NTSB CAROL:** HTTP 200 SPA shell ≠ public content; skip when `cm_agency=Other` or `cm_reportType=DirectorBrief`.
- **Exact FAA↔NTSB merge:** 0 pairs at dry-run — orphan FAA events are different incidents, not dupes.

---

## Archive

Detailed 2026-05-23 session notes (spike scripts, file lists, pre-ship roadblocks) superseded by PRD 0002–0004 ship entries above. See git history `9342bd8`–`5b0dcf5` and `Planning/tasks/` for full detail.
