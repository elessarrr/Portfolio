# Branch Debrief — `v2-(first-round-of-feedback-from-RJ)`

**Date:** 2026-05-24  
**Branch:** `v2-(first-round-of-feedback-from-RJ)`  
**Final commit:** `2021b9a` (docs only) / last code commit: `f3e4d52` ("going in circles")  
**Sources used:** `JOURNAL.md`, `learnings_from_errors.md`, `context/context-2026-05-24.md`, `context/context-main-branch-asn-links-2026-05-18.md`, `.cursor/plans/main_branch_link_brief_56b69f3e.plan.md`, `Planning/tasks/`, full session history.

---

## Scope and primary objective

**Scope: Boeing and Airbus aircraft only.** This app does not attempt to cover all manufacturers. Every importer, deduplication rule, URL builder, and rollup mechanism should be scoped to Boeing/Airbus records. Non-Boeing/Airbus records that slip through are noise, not features.

**Primary objective: maximise incident coverage without breaking what already works, validated by tests at every stage.** "Coverage" means: a user browsing a Boeing or Airbus aircraft page can click a working link that takes them to the specific incident record at an authoritative source. Every step that adds a new source or URL type must be gated by a test before the next step begins. No step should reduce coverage or introduce dead/broken links in previously-working rows.

This means: **ship a thin slice that works end-to-end, test it, then add the next slice.** The v2 failure mode was adding multiple sources simultaneously before any of them had reliable URL pipelines.

---

## 1. What we were trying to build

The v2 branch was meant to evolve the working but narrow `main` proof-of-concept (ASN-only links via a single `Incident.asn_url` field) into a multi-source tracker for **Boeing and Airbus incidents** that aggregates records from ASN, NTSB (CAROL/docket), FAA AIDS (~157k records), and FAA SDR, stores each source record in a normalised `IncidentSource` table, and serves every incident with a valid, prioritised outbound link to its official source page — so that a user browsing a Boeing or Airbus model could always click "Details" and land on the specific accident record. The branch also introduced aircraft-family rollup (query-time aggregation of incidents across variant profiles) and AI-generated summaries layered on top.

---

## 2. What actually happened

The branch never reached a consistent link experience. The specific failures, with evidence:

**A. FAA AIDS imported with near-zero URLs**
- 157,342 `IncidentSource` rows for `source_name='FAA_AIDS'` were imported with `source_url = NULL` (only 1 row had a URL).
- `app/ingestion/url_builders/faa_aids.py` intentionally fell back to a catalog landing page (`https://www.faa.gov/data_research/accident_incident`) — which is not a per-record link.
- Overall incident URL coverage stalled at **~32%** (~77k of ~242k incidents).
- Symptom: clicking "Details" on most FAA-sourced incidents went nowhere useful.

**B. Placeholder/test data polluted the DB**
- `example.com` URLs were present in `IncidentSource.source_url` from early test runs.
- There was no import-time guard preventing placeholder URLs from being stored as real data.
- Symptom: production DB contained links that visibly went to a browser "no such page".

**C. NTSB links pointed to sparse docket pages instead of richer CAROL investigation pages**
- The URL builder preferred `https://data.ntsb.gov/carol-main/...` docket-level pages over `https://carol.ntsb.gov/investigations/detail/` investigation pages.
- Symptom: NTSB links opened but showed minimal content or only a document list.

**D. Foreign-led NTSB and DirectorBrief cases produced empty CAROL pages**
- Incidents where NTSB was the accredited representative (`cm_agency=Other`, e.g. DCA17RA058 Bishkek) or the report type was `DirectorBrief` (e.g. ENG16IA001) would produce CAROL URLs that return HTTP 200 but render empty SPA shells.
- Symptom: users landed on "NTSB CAROL" pages with no visible incident content.

**E. Template rendered `href=""` for FAA-only incidents**
- `app/templates/components/incident_list.html` called `resolve_primary_href(incident)` but when no usable source existed, it returned `None` or `""`, which Jinja rendered as `href=""` — a broken self-link.
- Symptom: clicking "Details" on FAA-only incidents silently reloaded the current page.

**F. `global_incident_list.html` entirely bypassed link helpers**
- The global incidents page (`app/templates/components/global_incident_list.html`) was never updated to use `link_helpers.py`; it rendered raw `source_url` values directly.
- Symptom: inconsistent link quality between the aircraft detail page and the global incidents page (JOURNAL: "deferred" as of 2026-05-24).

**G. Two pre-existing test failures remained unresolved at session close**
- `tests/test_source_links.py` had 2 failing tests at final commit.

**H. Session ended in declared stall**
- Commit `f3e4d52` message: "going in circles, so wrapping up for now. Will start a new branch."

---

## 3. Root causes

**The real issue was that link quality was treated as a post-import enrichment problem, not an import-time contract.** Everything else follows from this.

Specifically:

**RC-1: No URL contract enforced at write time.**  
The `IncidentSource` model accepted `source_url = NULL` and placeholder values at insert. There was no DB constraint, no importer validation, and no test gate that required a non-null, non-placeholder URL before an `IncidentSource` row was committed. This meant the entire FAA AIDS corpus was importable — and imported — without any usable link, creating a structural data gap that required a separate spike + mass backfill to repair.

**RC-2: FAA AIDS URL builder was never implemented for per-record URLs.**  
At the time the FAA AIDS bulk import was built, the ASIAS per-record URL pattern was unknown. The builder deliberately fell back to a catalog page. The correct approach was to spike the URL pattern *before or during* the importer build, not weeks later. The spike confirmed a 100% reliable pattern (`P12_AIDS_RPRT_NBR:{source_record_id}`) — this should have been the first step, not the last.

**RC-3: Multi-link storage (`source_data.links[]` JSON) made URL resolution opaque.**  
NTSB introduced a JSON blob in `IncidentSource.source_data` that stored multiple links with roles (`investigation`, `docket`, `brief`). Resolving "which URL to show" required runtime Python logic (`app/link_helpers.py`), Jinja globals, and conditional template branches. This complexity propagated into every render path and made it easy to miss a code path (as `global_incident_list.html` shows).

**RC-4: HTTP 200 is not a proxy for public content on NTSB CAROL.**  
CAROL returns 200 on SPA shell pages even when no content is available (foreign-led, DirectorBrief). Validation logic that checked only HTTP status silently passed bad URLs through. This required bespoke `carol_detail_has_public_content()` logic keyed on `cm_agency` and `cm_reportType` values — knowledge that was only discovered by inspecting real incidents, not before the NTSB importer was built.

**RC-5: Cross-source deduplication was prioritised before the single-source baseline was reliable.**  
Significant effort went into FAA↔NTSB exact-merge logic, which ultimately found 0 matching pairs at dry-run. The energy would have been better spent ensuring every source had a valid URL *before* attempting to merge sources.

**RC-6: The `main` branch's working pattern (scrape → store URL verbatim → render verbatim) was abandoned rather than extended.**  
`main` stored a trustworthy `asn_url` directly on `Incident` and rendered it without any indirection. v2 replaced this with a layered resolution stack (`IncidentSource` → `link_helpers` → Jinja globals → template conditionals) before all sources had reliable URLs. The complexity was introduced ahead of the data readiness.

---

## 4. What NOT to do in the new branch

1. **Do not import a source record without a URL.** If the URL pattern is unknown, spike it first. If there is no stable per-record URL, mark the source as catalog-only in code (not by storing a catalog URL as if it were a record link). NULL + a `source_url_status` enum is more honest than a wrong URL.

2. **Do not store placeholder or catalog-fallback URLs as `source_url` values.** `https://www.faa.gov/data_research/accident_incident` is not a per-record link. Storing it as one poisons coverage metrics and misleads users. Use NULL and a UI fallback instead.

3. **Do not add cross-source deduplication logic until every source has a trustworthy URL pipeline.** FAA↔NTSB merge found zero pairs and consumed significant effort. Ship reliable single-source links first; deduplication is a later-phase optimisation.

4. **Do not use JSON blobs (`source_data`) as the primary link store.** Resolving a URL from a JSON column at render time requires framework coupling (Jinja globals), is invisible to DB-level queries, and is impossible to validate at write time. Resolve to a single `source_url` at import.

5. **Do not use low-cardinality fields as globally unique keys.** Learned from `learnings_from_errors.md` 2026-05-03: using a domain name as `source_record_id` caused `UNIQUE constraint failed` when multiple incidents shared the same domain. Always derive `source_record_id` from an incident-specific identifier plus a deterministic hash.

6. **Do not trust HTTP 200 as proof of public NTSB CAROL content.** CAROL returns 200 for empty SPA shells. The `carol_detail_has_public_content()` check (in `app/ingestion/url_builders/ntsb.py`) must be applied before storing a CAROL URL, not only at display time.

7. **Do not let any template render a link without going through a single, audited resolution path.** `global_incident_list.html` was missed. All templates that render incident links must use the same helper (or a shared macro wrapping it). Add a test that verifies no template directly renders `source_url` or `asn_url` without going through `link_helpers`.

8. **Do not add ORM eager-loading (`joinedload`) to relationships declared as `lazy='dynamic'`.** `Incident.sources` is dynamic; `joinedload` on it throws `InvalidRequestError`. Learned from `learnings_from_errors.md` 2026-04-04.

9. **Do not carry ORM instances across Flask app context boundaries.** `DetachedInstanceError` appeared twice (2026-04-26, 2026-05-02). Store primitive IDs before exiting context blocks.

10. **Do not add multi-source complexity before the ASN baseline link is guaranteed on every incident that has one.** The `main` branch's ASN-only pipeline worked because it was simple and direct. Restore that guarantee first, then add sources on top.

11. **Do not import non-Boeing/Airbus records.** Every importer must gate on manufacturer before creating `Aircraft`, `Incident`, or `IncidentSource` rows. Orphaned records for other manufacturers add noise to coverage metrics and cause false positives in deduplication logic.

---

## 5. What to carry forward

These are worth preserving verbatim or with minimal changes:

| Artifact | File | Why |
|----------|------|-----|
| Link resolution core | `app/link_helpers.py` | Centralises CAROL preference, placeholder filtering, foreign-led NTSB handling, and primary href resolution. The logic is correct; the problem was that it was not applied universally. |
| NTSB URL builder | `app/ingestion/url_builders/ntsb.py` | `carol_detail_has_public_content()` captures hard-won knowledge about `cm_agency=Other` and `DirectorBrief` edge cases. Keep verbatim. |
| FAA ASIAS URL builder | `app/ingestion/url_builders/faa_aids.py` | Contains the spike-validated ASIAS URL pattern `P12_AIDS_RPRT_NBR:{source_record_id}`. 100% hit rate on spike sample. Keep `build_faa_aids_primary_url()`. |
| Link schema | `app/ingestion/link_schema.py` | `normalize_link_entry()` and `is_placeholder_url()` are solid utility functions for import-time validation. |
| `resolve_aircraft()` | `app/ingestion/importers/base.py` | Hardened model resolution (exact → prefix fallback → Boeing/Airbus auto-create). Prevents the FAA/NTSB orphan problem from recurring. |
| Family rollup | `app/services/aircraft_family.py` + `AircraftFamilyMember` model | Query-time aggregation of incidents across variant profiles. No incident migration required. 751 mappings loaded. Keep the pattern, not just the data. |
| Error log | `learnings_from_errors.md` | 50+ documented error/fix/prevention entries. Read this before starting any ingestion or test work. |
| All PRD task files | `Planning/tasks/` | Track what was solved (Phase 1–4 of PRD-0013 fully complete) and what remains (family rollup Phase 2, 155 unmapped variants). |
| `IncidentSource` model structure | `app/models.py` | The multi-source schema is correct. The problem was data quality in it, not the model itself. |
| Context comparison doc | `context/context-main-branch-asn-links-2026-05-18.md` | Documents exactly how `main`'s ASN pipeline works — the pattern to replicate for each new source. |
| Test suite (minus 2 failures) | `tests/` | 140+ passing tests. The 2 failures in `tests/test_source_links.py` are the first thing to fix. |

---

## 6. Recommended starting point for the new branch

**Branch from `main`, not from v2 HEAD.**

v2's codebase carries accumulated complexity that was itself the cause of the problems: layered resolution stacks, JSON-blob link storage, inconsistent templates, and 2 pre-existing test failures on day one. Starting from `main` gives a working baseline with no failures, the proven scrape→store→render pattern, and a clean mental model to extend. The data (242k incidents) lives in the SQLite file and is not lost; it can be re-imported once the new importers are built correctly. The code worth saving from v2 (see §5) is a short list of specific files that can be cherry-picked in as controlled additions — that is a better outcome than inheriting the full mess.

**The core discipline for the new branch: add one source at a time, test it end-to-end before adding the next.**

### First 3 moves

**Move 1 — Confirm `main` is green, then add the `IncidentSource` schema.**  
Run the `main` test suite to establish a clean baseline. Then add the migration and model changes from v2 for `IncidentSource` only — no importers yet. Write a test that asserts: any `IncidentSource` row with a non-null `source_url` passes `is_placeholder_url()` = False. This is the import-time contract that v2 lacked, codified before a single record is imported.

**Move 2 — Port ASN as the first source through `IncidentSource`, following `main`'s proven pattern.**  
Cherry-pick `app/ingestion/url_builders/` and adapt the `main` ASN scraper to write into `IncidentSource` instead of `Incident.asn_url` directly. Verify ASN link coverage is 100% for scraped rows before touching NTSB or FAA. This re-establishes the working baseline in the new schema.

**Move 3 — Port NTSB second, using the CAROL content-detection logic from day one.**  
Cherry-pick `app/ingestion/url_builders/ntsb.py` (with `carol_detail_has_public_content()`) and the NTSB importer from v2. Gate CAROL URL storage on that check at write time, not at display time. Add a test asserting that `cm_agency=Other` rows are stored without a CAROL `source_url`. Only after NTSB links are green do you introduce FAA AIDS.

---

## 7. Source intelligence — what we know about each data source

This section captures everything learned about each source that bears on the coverage objective. Read before making any decisions about importers, URL builders, or deduplication.

### ASN (Aviation Safety Network)

- **What it covers:** Worldwide Boeing and Airbus incidents with narrative, metadata, and per-event pages. Best single source for coverage breadth.
- **URL pattern:** `https://aviation-safety.net/database/record.php?id=YYYYMMDD-N` — one URL per incident, stable, scraped from the date-column anchor on model/type pages.
- **Dedupe key:** `asn_url` itself — unique per ASN event page, and stable. This is why `main` works: dedupe is trivial and reliable.
- **How `main` uses it:** `scripts/scraper_utils.py` extracts `asn_url` from the date-column `<a>` tag; `scripts/import_data.py` stores it on `Incident.asn_url` and deduplicates on it. The template renders it verbatim. No resolution logic needed.
- **Gotchas:** Scraping-based, so subject to ASN site structure changes. Rate-limit scraping to avoid blocks. ASN narrative text may mention NTSB or FAA — this does not mean an NTSB.gov URL is stored anywhere.
- **Coverage for Boeing/Airbus:** Very high. This should be the non-negotiable baseline on every incident that is in ASN.

### NTSB (National Transportation Safety Board)

- **What it covers:** US-registered aircraft accidents and some foreign accidents where the US was lead investigator. Does **not** cover all Boeing/Airbus incidents — only US-territory or US-lead.
- **URL types (in priority order):**
  1. CAROL investigation detail: `https://carol.ntsb.gov/investigations/detail/{investigation_id}` — richest content, but only valid if `carol_detail_has_public_content()` returns True.
  2. CAROL docket: `https://data.ntsb.gov/carol-main/document-viewer/...` — useful fallback when investigation detail is not available.
  3. DirectorBrief: goes to docket, not investigation detail.
- **Critical gotcha — CAROL HTTP 200 ≠ public content:** CAROL is a JavaScript SPA. It returns HTTP 200 on the shell page even when the investigation has no public content. You must check `cm_agency` and `cm_reportType` in the bulk data *before* storing a CAROL URL:
  - `cm_agency = 'Other'` → NTSB was accredited representative only (foreign-led investigation). No public CAROL or docket page. Do not generate a CAROL URL. Show a FAQ explanation in the UI instead.
  - `cm_reportType = 'DirectorBrief'` → engine/component brief. Content publishes to the docket, not CAROL investigation detail. Use docket URL if available.
  - The function `carol_detail_has_public_content()` in `app/ingestion/url_builders/ntsb.py` encodes these rules. Always call it before storing a CAROL URL.
- **Bulk data download:** Files at `app.ntsb.gov/avdata`. Must parse the index HTML to find canonical download-link hrefs — direct/guessed file paths are unreliable. NTSB blocks non-browser user-agent strings; use browser-like headers.
- **Dedupe with FAA AIDS:** Attempted exact merge found **0 matching pairs**. FAA AIDS and NTSB cover overlapping events but with different record IDs and no shared key. Do not spend effort on cross-source ID matching — it does not pay off.
- **Coverage for Boeing/Airbus:** Good for US-registered aircraft; partial for foreign-registered aircraft involved in US-investigated accidents.

### FAA AIDS (Accident/Incident Data System)

- **What it covers:** US-territory aviation accidents and incidents — broader than NTSB (covers incidents, not just accidents) and broader geographically for US-registered aircraft. ~157k records in v2.
- **Per-record URL (confirmed):** `https://asias.faa.gov/boeingasias/asias.framework.main?...P12_AIDS_RPRT_NBR:{source_record_id}` where `source_record_id` = the control number field `c5` in bulk data. **100% success rate on 500-record spike sample.** This pattern is reliable and should be used at import time, not backfilled later.
- **URL builder:** `build_faa_aids_primary_url()` in `app/ingestion/url_builders/faa_aids.py`. Keep and use from day one.
- **Bulk data:** CSV download from FAA. The FAA catalog pattern (`faa.gov/data_research/accident_incident`) is a landing page, not a per-record URL — do not store it as `source_url`.
- **Manufacturer filtering:** FAA AIDS covers all manufacturers. Must filter to Boeing/Airbus at import time using `resolve_aircraft()`. The `resolve_aircraft()` hardening in `app/ingestion/importers/base.py` handles exact → prefix fallback → Boeing/Airbus auto-create.
- **Gotchas:** FAA can return HTML (not CSV) from what looks like a CSV endpoint — the `_looks_like_csv()` guard in the SDR importer exists for this reason. FAA blocks some automated requests; respect rate limits.
- **Coverage for Boeing/Airbus:** Adds significant incremental coverage beyond ASN+NTSB, especially for incidents (not just accidents) and for US-registered aircraft.

### FAA SDR (Service Difficulty Reports)

- **What it covers:** Airworthiness and maintenance difficulty reports — **not accident/incident reports.** These are reports of part failures, service difficulties, and airworthiness issues filed by operators and maintenance shops.
- **Relevance to coverage objective:** Lower priority than ASN/NTSB/FAA AIDS. SDRs are not "incidents" in the same sense — they are maintenance flags. Include only if explicitly adding airworthiness coverage is a product goal.
- **Known issue:** `FAASDRImporter._fetch_remote_records()` has a live-endpoint problem: the endpoint currently returns HTML instead of CSV, causing `_looks_like_csv()` to return False and the importer to silently return zero records. This must be diagnosed before any SDR work begins.
- **Recommendation:** Defer FAA SDR until ASN + NTSB + FAA AIDS are shipping cleanly. The coverage lift from SDRs is uncertain; the engineering cost of fixing the fetch pipeline is real.

### Source overlap and deduplication reality

- **ASN and NTSB overlap:** Many significant Boeing/Airbus accidents appear in both. ASN covers them with narrative; NTSB covers US-investigated ones with official investigation data. These are *complementary*, not duplicate — a user benefits from seeing both.
- **FAA AIDS and NTSB overlap:** Same events may appear in both (NTSB investigates accidents; FAA AIDS records them independently). Exact merge found **0 matching pairs** — the record IDs are different, and the datasets are maintained independently. Accept the overlap rather than spending effort on deduplication.
- **Practical implication:** Model as "one incident, multiple sources" (`IncidentSource` rows per source per event). Show the best available link. Do not try to collapse sources into a single authoritative record — the data does not support it.

### Family rollup (Boeing/Airbus variant problem)

- **The problem:** Boeing and Airbus aircraft are registered under dozens of variant names in FAA and NTSB data (e.g. `Boeing 737-800`, `B737-800`, `737-8`, `B-737`). Without rollup, a search for "Boeing 737" misses most FAA incidents.
- **The solution (implemented in v2):** `AircraftFamilyMember` table maps variant `aircraft_id` entries to a canonical family (e.g. all 737 variants → family ID 88). `app/services/aircraft_family.py` aggregates incidents at query time across all member profiles. 751 mappings loaded in v2.
- **Coverage impact:** `/aircraft/88` went from 0 to 566 FAA links after rollup was enabled. This is one of the highest-leverage things in v2 — keep the pattern.
- **Phase 2 gap:** 155 unmapped Boeing/Airbus FAA variant pages remain. Adding these mappings is a high-value, low-risk task.
