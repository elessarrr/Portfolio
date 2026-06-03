# Engineering Log & Knowledge Journal

> **Format (per AGENTS.md):** One entry per completed task / major bug / schema learning.  
> **1–2 sentences each.** Group by month (`## June 2026`, etc.); newest entry first within each month.  
> Detailed history lives in PRDs, commits, and `Planning/`.

**Branch:** `v3-boeing-airbus-links` · branched from `origin/main`  
**DB:** `data/aircraft_safety.db` · **App:** `http://127.0.0.1:5001`

---

## June 2026 (newest first)

- **2026-06-03** — *Tail row 20090520857189A.* Stale `working_search_prefill` → live re-check `working_brief_report`; migrate page 12→18 + activate — **6466/6466 (100%)** brief gate.
- **2026-06-03** — *PRD 0007.2 complete.* Gate 99.98%; tail migrate **381** URLs; spot-check 10/10; smoke + post-import pass; task list closed. Review: `Planning/reviews/faa-aids-brief-migration-gate-0007.2-2026-06-03.md`.
- **2026-06-03** — *retry5 (49 gentle).* concurrency 3, timeout 25s, jitter 500–1500ms → **49/49** brief; merged **6465/6466 (99.98%)**; DB **6233** active FAA brief (+49). **Learning:** prior failures were rate/load, not bad IDs.
- **2026-06-03** — *Re-merge + DB apply (no link left behind).* Overlay from `merged_pre_retry4` + retry4/gap → **6416/6466 (99.23%)** brief; `--apply --overlap-audit` → **6184** active FAA brief in v3 DB. **Outcome:** 22 stale merge rows fixed; 49 infra flakes stay inactive.
- **2026-06-03** — */audit-urls v1.2.* Documented retry4 deferred batch, gap-fill, overlay merge, JSONL integrity; added `merge_faa_aids_audit_overlay.py`; cron counts valid `source_record_id`s. **Outcome:** skill + `faa-asias.md` reference updated via `gen:skill-docs`.
- **2026-06-03** — *PRD 0009 retry4 + re-merge.* ASIAS up; retry4 **345/368** brief; gap-filled 5 corrupt/missing JSONL lines; merged gate **6394/6466 (98.89%)**; refreshed app-link export. **Outcome:** optional `apply_faa_audit_buckets_to_db --apply` for ~310 new brief rows.
- **2026-06-03** — *PRD 0008 Tasks 5–6 complete.* SQLite write-back (`db_writeback.py`, ask-before-write, `--dry-run`); CLI flags finalized; **146 pytest green** — PRD 0008 done.
- **2026-06-03** — *PRD 0008 Task 4.0.* Retry/merge: `url_audit/merge.py`, `--retry-failures-from` / `--merge-into`, safe `_merged.jsonl` naming; 7 merge tests; **139 pytest green**.
- **2026-06-03** — *PRD 0008 Task 3.0.* Portable core engine: `url_audit/http.py`, `classify.py`, `engine.py`, CLI audit run + JSONL output; 9 new tests; **132 pytest green**.
- **2026-06-03** — *PRD 0009 implemented (ship path).* FR-0: 246 FAA↔ASN/NTSB overlaps deactivated; 6,084 URLs migrated to page 18; `is_active` from brief buckets; UI hides linkless FAA-only rows; post-import audit passed; retry4 deferred (ASIAS down).
- **2026-06-02** — */errors-audit-deep.* Harvested FAA migration session into `LEARNINGS.md` §51–§55 (overlay stale merge, ReadTimeout, importer test drift, legacy DeepSeek DB, JSONL gap-fill) + proactive bullets.
- **2026-06-02** — */context-distillation.* Generated `context/context-2026-06-02.md` (FAA brief migration state, 55 bugs, §7–§8); updated `context-latest.md`.
- **2026-06-02** — *PRD 0009 FAA link app integration.* `0009-prd-faa-aids-link-app-integration.md` — NTSB-parity pipeline (brief audit gates, JSONL review export, migrate + `is_active`, smoke); builds on 0007.2; no re-import.
- **2026-06-02** — *FAA brief retry4 cron.* `run_faa_brief_retry4_when_live.py` + 30-min cron probes ASIAS (2xx gate); auto-starts retry3-style audit on 376-row input when up; logs `faa_brief_retry4_watch.log` / `faa_brief_retry4_audit_run.log`.
- **2026-06-01** — *PRD 0007.2 drafted.* `Planning/tasks/0007.2-prd-faa-aids-brief-report-url-migration.md` — full brief audit, gated migrate, importer switch, optional `is_active`; sample gate 200/200.
- **2026-06-01** — *Page-18 experiment retry (60 flakes).* Re-audited 60 failed sample URLs with `--url-mode brief`; 53+7 after second pass → **200/200** `working_brief_report` in `faa_aids_report_url_experiment_200.jsonl`.
- **2026-06-01** — *FAA URL audit v1.1.* Three-tier buckets, `--url-mode brief|search` (default brief), stricter page-12 classification, `migrate_faa_aids_urls_to_brief.py`; skill split generic vs `references/faa-asias.md`.
- **2026-06-01** — *`/audit-urls` skill — FAA lessons section.* Expanded tmpl with three-tier “working” (HTTP vs product vs DB), rejected approaches, page-18 gate, false positives, future code table; filled `references/faa-asias.md`.
- **2026-06-01** — *`/audit-urls` skill.* Added `.claude/gstack/audit-urls/` (tmpl + FAA reference); defaults documented: concurrency 16, jitter on, retry_once; code aligned (`--no-jitter` flag).
- **2026-06-01** — *FAA URL audit optimizations + retry.* httpx pool, 64KB body cap, retry-on-transient, defaults 24 workers / 15s / no jitter; re-checked 28 prior failures — **28/28 working**; merged export `faa_aids_url_audit_merged_2026-06-01.jsonl` (6,466 working).
- **2026-06-01** — *ASIAS global outage + alternative source investigation.* ASIAS portal returned Akamai CDN errors site-wide (homepage + all record URLs); confirmed no alternative per-record URL source exists — `av-info.faa.gov` redirects to ASIAS, FAA removed AIDS from `faa.gov/data_research`, no data.gov per-record dataset. PRD 0007.1 URL audit blocked until ASIAS recovers; liveness probe guards against false-positive mass soft-delete.
- **2026-06-01** — *PRD 0007.1 FAA AIDS URL verification.* Built `faa_aids_viability.py` (ASIAS dead-end classifier + liveness probe), `audit_faa_aids_urls.py` (ThreadPoolExecutor CLI, 8 workers, ~15 min for 6,466 URLs, dry-run + DB write-back); 9 new unit tests; `link_picker.py` + `routes.py` already gate on `is_active` — no template changes needed; **109 pytest** green.
- **2026-06-01** — *FAA mapping remediation.* Refined mapping (**685** `map_to_existing`, **40** `skip`, **0** `create_approved`); moved **3,465** incidents to catalog pages; deleted **316** bootstrap bloat aircraft; wrote `data/logs/faa_aids_enrichment_final_import_01Jun2026.jsonl` (**6,466** rows).
- **2026-06-01** — *PRD 0007 FAA AIDS v3 import (autonomous session).* Export **6,848** rows; mapping **725** strings; bootstrap **356** pages; bulk **6,466** FAA incidents; post-import audit **passed**; **98 pytest** green.
- **2026-06-01** — *PRD 0007 authored.* `Planning/tasks/0007-prd-faa-aids-v3-import.md` — FAA AIDS enrichment for v3 (Boeing/Airbus only, URL-at-import-time, mapping gate, ASN dedupe, pilot → bulk → audit pipeline; 10 phases A–J; mirrors NTSB 0006.x pattern.
- **2026-06-01** — *AGENTS.md context freshness rule.* Core Workflows: if no `context/context-YYYY-MM-DD.md` within 2 days, run `/context-distillation` and refresh `context-latest.md`; skill listed under Available Skills.
- **2026-06-01** — *Lanes A+B (polish + dev DX).* **A:** DeepSeek errors map to generic summary message; removed `\| safe` on summary card; feedback empty-submit test + HTML `required`. **B:** dev default DB → `aircraft_safety_v3.db`; `scripts/smoke_ntsb_ui.py` (httpx); README updated.
- **2026-06-01** — *PRD 0006.3 Task 7.0 post-import QA.* Added `test_importer_idempotent_re_run_with_mapping`; **71 pytest** green; HTTP smoke on `:5003` + v3 DB (Stearman/A320/AS350/737-800, 12 NTSB docket hrefs). **0006.3 tasks 5.12–7.0 complete** (mapping commit 5.16.5 still open).
- **2026-06-01** — *Deep errors audit (`/errors-audit-deep`).* Crawled terminals, agent transcript `8026f7ae`, `JOURNAL.md`, QA session report, v2 branch debrief; appended **§43–§50** to `LEARNINGS.md` (ORM dynamic/joinedload, DetachedInstance, UNIQUE source_record_id, Playwright sandbox ERR_SYSTEM, browse path/refs, feedback QA, stale ASN 404) + proactive-prevention bullets.
- **2026-06-01** — *Context distillation health check.* Generated `context/context-2026-06-01.md` (architecture, Mermaid flow, file map, 15 harvested bugs, snippets, error log, v3 state); updated `context/context-latest.md` pointer.

## May 2026 (newest first)

- **2026-05-30** — *PRD 0006.3 post-import audit (5.22).* Audit found 3 NTSB/ASN dupes (null fatalities → 0 at import); removed via `--remediate`; **603** NTSB sources; audit **passed**; **63 pytest** green.
- **2026-05-30** — *PRD 0006.3 bulk import (5.21).* Bootstrap 15 pages on real v3, dedupe re-pass (**606** candidates), imported **606/606** NTSB incidents with mapping gate; idempotent re-run clean; stats recalc on 43 pages; `scripts/ntsb_bulk_import.py`; **60 pytest** green. Real v3: **112 aircraft**, **6,129 incidents**, **606 NTSB sources**.
- **2026-05-30** — *PRD 0006.3 pilot import (5.19.3 + 5.20).* Review gate approved; cloned v3 → pilot DB, bootstrapped 15 `create_approved` pages, dedupe re-pass on pilot (606 import candidates), imported **30/30** NTSB incidents with mapping gate + audit URLs; verify **0 issues**; `scripts/ntsb_pilot_import.py` + `tests/test_ntsb_pilot_import.py`; **58 pytest** green.
- **2026-05-30** — *Git / gstack symlink.* Commit blocked on broken gstack submodule symlink. **Tried:** `git update-index --force-remove` + re-add `.claude/skills/gstack` as mode `120000` symlink (`../gstack`). **Outcome:** `git status` works; staged `typechange` for next commit.
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
| Branch baseline | **98 tests** green |
| NTSB bulk import | **603** NTSB on real v3; PRD **0006.3** complete |
| FAA AIDS bulk | **6,466** FAA_AIDS sources on v3; PRD **0007** complete |
| Real v3 DB | **~469 aircraft**, **12,592 incidents**, **603 NTSB** + **6,466 FAA** |
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
