# Engineering Log & Knowledge Journal

> **Format (per AGENTS.md):** One entry per completed task / major bug / schema learning.  
> **1–2 sentences each.** Detailed history lives in PRDs, commits, and `Planning/`.

**Branch:** `v3-boeing-airbus-links` · branched from `origin/main`  
**DB:** `data/aircraft_safety.db` · **App:** `http://127.0.0.1:5001`

---

## May 2026 (chronological, newest first)

- **2026-06-01** — *PRD 0007 authored.* `Planning/tasks/0007-prd-faa-aids-v3-import.md` — FAA AIDS enrichment for v3 (Boeing/Airbus only, URL-at-import-time, mapping gate, ASN dedupe, pilot → bulk → audit pipeline; 10 phases A–J; mirrors NTSB 0006.x pattern).
- **2026-06-01** — *AGENTS.md context freshness rule.* Core Workflows: if no `context/context-YYYY-MM-DD.md` within 2 days, run `/context-distillation` and refresh `context-latest.md`; skill listed under Available Skills.
- **2026-06-01** — *Lanes A+B (polish + dev DX).* **A:** DeepSeek errors map to generic summary message; removed `\| safe` on summary card; feedback empty-submit test + HTML `required`. **B:** dev default DB → `aircraft_safety_v3.db`; `scripts/smoke_ntsb_ui.py` (httpx); README updated.
- **2026-06-01** — *PRD 0006.3 Task 7.0 post-import QA.* Added `test_importer_idempotent_re_run_with_mapping`; **71 pytest** green; HTTP smoke on `:5003` + v3 DB (Stearman/A320/AS350/737-800, 12 NTSB docket hrefs). **0006.3 tasks 5.12–7.0 complete** (mapping commit 5.16.5 still open).
- **2026-06-01** — *Deep errors audit (`/errors-audit-deep`).* Crawled terminals, agent transcript `8026f7ae`, `JOURNAL.md`, QA session report, v2 branch debrief; appended **§43–§50** to `LEARNINGS.md` (ORM dynamic/joinedload, DetachedInstance, UNIQUE source_record_id, Playwright sandbox ERR_SYSTEM, browse path/refs, feedback QA, stale ASN 404) + proactive-prevention bullets.
- **2026-06-01** — *Context distillation health check.* Generated `context/context-2026-06-01.md` (architecture, Mermaid flow, file map, 15 harvested bugs, snippets, error log, v3 state); updated `context/context-latest.md` pointer.
- **2026-05-30** — *PRD 0006.3 post-import audit (5.22).* Audit found 3 NTSB/ASN dupes (null fatalities → 0 at import); removed via `--remediate`; **603** NTSB sources; audit **passed**; **63 pytest** green.
- **2026-05-30** — *PRD 0006.3 bulk import (5.21).* Bootstrap 15 pages on real v3, dedupe re-pass (**606** candidates), imported **606/606** NTSB incidents with mapping gate; idempotent re-run clean; stats recalc on 43 pages; `scripts/ntsb_bulk_import.py`; **60 pytest** green. Real v3: **112 aircraft**, **6,129 incidents**, **606 NTSB sources**.
- **2026-05-30** — *PRD 0006.3 pilot import (5.19.3 + 5.20).* Review gate approved; cloned v3 → pilot DB, bootstrapped 15 `create_approved` pages, dedupe re-pass on pilot (606 import candidates), imported **30/30** NTSB incidents with mapping gate + audit URLs; verify **0 issues**; `scripts/ntsb_pilot_import.py` + `tests/test_ntsb_pilot_import.py`; **58 pytest** green.
- **2026-05-27** — *PRD 0005.1 ASN baseline rebuild.* Rebuilt `data/aircraft_safety_v3.db` from `scripts/scrape_*.py` + `scripts/import_data.py` (fresh scrape artifacts kept local, not committed). Verified `incident_source=0`, all incidents have `asn_url`, and parity checks: `Boeing 747-100=100`, `Boeing 727-100=100`, representative Airbus (`Airbus A320=100`); **29 pytest** green.
- **2026-05-27** — *FR-8 NTSB resolver.* Fixed `resolve_ntsb_source_url()` priority so **CAROL wins over docket** when public content + `cm_mkey` (while still blocking CAROL for `Other` / `DirectorBrief`); added unit test; **29 pytest** green.
- **2026-05-24** — *Step 3 NTSB slice.* `url_builders/ntsb.py` + minimal `NTSBImporter` (Boeing/Airbus gate, single `source_url`, no CAROL for Other/DirectorBrief); foreign-led FAQ in incident list; **28 pytest** green.
- **2026-05-24** — *Step 2 ASN regression.* `test_incident_list_renders_asn_details_href`; ASN import unchanged.
- **2026-05-24** — *Step 1 shipped.* `source_record_id` + `is_active` on `IncidentSource`; `link_schema.py` + `link_picker.py`; batch source load in routes; shared macro; **22 pytest** green.
- **2026-05-24** — *Dev DB policy documented.* Fresh SQLite for link arc; never attach v2 DB. See `README.md` § Local Development Setup.
- **2026-05-24** — *Step 0 complete.* Branched `v3-boeing-airbus-links` from `origin/main`; baseline test suite: **15 passed, 0 failures**. Plan doc: `.cursor/plans/2405_new_branch_plan_676fa222.plan.md`.

---

## Current state (snapshot)

| Area | Status |
|------|--------|
| Branch baseline | **77 tests** green |
| NTSB bulk import | **603** NTSB on real v3; PRD **0006.3** pipeline complete through Task **7.0** |
| Real v3 DB | **112 aircraft**, **6,126 incidents**, **603 NTSB** |
| `IncidentSource` | `source_record_id`, `is_active`, indexes + unique constraint |
| `link_schema` / `link_picker` | Placeholder + catalog rejection; ASN → NTSB → FAA_AIDS |
| url_builders | `ntsb.py` (single-URL, CAROL gating) |
| Importers | `NTSBImporter` (Boeing/Airbus); FAA pending Step 5 |
| ASN scrape/import | Unchanged on `Incident.asn_url` |
| Step 4 (NTSB bulk) | **6.0** — Make/Model column + importer hardening |
| Dev DB policy | Documented in `README.md` — fresh SQLite only |

---

## Key learnings (durable — carried from v2 debrief)

- **FAA URLs:** `P12_AIDS_RPRT_NBR:{source_record_id}` from bulk `c5` — 100% on spike sample.
- **NTSB CAROL:** HTTP 200 SPA shell ≠ public content; skip when `cm_agency=Other` or `cm_reportType=DirectorBrief`.
- **Exact FAA↔NTSB merge:** 0 pairs at dry-run — orphan FAA events are different incidents, not dupes.
- **Anti-patterns to avoid:** See `Planning/branch-debrief-v2.md` §4 — 11 explicit rules.
- **`IncidentSource` discipline:** single `source_url` resolved at import; no JSON-blob link resolution; no catalog/placeholder URLs.

**2026-05-30** — Git commit blocked on broken gstack submodule symlink. **Tried:** `git update-index --force-remove` + re-add `.claude/skills/gstack` as mode `120000` symlink (`../gstack`). **Outcome:** `git status` works; staged `typechange` for next commit.
