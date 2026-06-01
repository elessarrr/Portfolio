# Product Requirements Document: FAA AIDS Per-Record URL Spike

**Project ID:** 0001  
**Created:** 23 May 2026  
**Author:** Product (with CTO)  
**Status:** Spike complete — **GO** (awaiting product sign-off on spike report)  
**Parent initiative:** Multi-source incident link enrichment (Track B — FAA)

---

## 1. Introduction/Overview

### Problem statement

Aircraft Safety Tracker has **~157,342 FAA_AIDS** `IncidentSource` rows; **only 1** has a usable `source_url`. That caps overall incident link coverage at **~32%** (~77k of ~242k incidents). NTSB and ASN are fully linked; merge/backfill and exact FAA↔NTSB dedupe found **0** overlapping rows to inherit URLs from.

Today, `app/ingestion/url_builders/faa_aids.py` intentionally falls back to a **catalog landing page** (`https://www.faa.gov/data_research/accident_incident`) when no per-record URL exists — which does not satisfy “open the specific event” UX.

### Solution (this PRD)

A **time-boxed spike (1–2 days)** to determine whether FAA AIDS bulk data (or a supported FAA public API/page) exposes **stable, per-record public URLs** keyed by fields we already store (e.g. control number `c5` / `source_record_id`).

### Goal

Produce a **go / no-go recommendation** with evidence. **Only if the spike succeeds** do we proceed to implementation (importer + `url_builders` + optional backfill). Other enrichment tracks (CLI restore, `enrich-linkless`, full QA) are explicitly deferred until after this decision.

---

## 2. Goals

### Primary goals

1. **Discover** whether a deterministic URL pattern exists for ≥90% of AIDS records in our bulk sample.
2. **Validate** that sampled URLs resolve (HTTP 200 or acceptable redirect) and show content related to the event (not generic search).
3. **Document** field mapping (bulk column → URL parameter) and stability expectations (same URL after re-import).
4. **Deliver go/no-go** with estimated coverage lift and implementation effort (S/M/L). **Decision owner: product lead (sole sign-off).**

### Secondary goals

1. Capture FAA terms-of-use / robots / rate-limit constraints for automated backfill.
2. Identify fallback tiers if full per-record URLs are impossible (e.g. search URL with control number, monthly archive PDF).

### Success threshold (spike gate)

| Outcome | Criteria | Next step |
|--------|----------|-----------|
| **Go** | ≥90% of 500-record sample resolve to stable, event-specific pages; pattern documented | PRD Phase 2 — implement builder + backfill |
| **Conditional go** | 50–89% coverage or redirects only; pattern documented with caveats | Scoped implementation + UI “catalog” fallback |
| **No-go** | No stable pattern; or URLs are auth-gated / break on re-test | Stop FAA URL work; revisit MEDIA enrichment or accept catalog-only |

---

## 3. User Stories

### Researcher / analyst

**As a** user reviewing a Boeing 737 incident sourced from FAA AIDS,  
**I want** a “View on FAA” link that opens the **specific** accident/incident record,  
**So that** I can verify details without manually searching the FAA site.

### Product lead (stakeholder)

**As** the product owner,  
**I want** evidence that FAA URLs are reliable before we invest engineering in backfill,  
**So that** we do not ship 157k broken or generic links.

### Engineer

**As a** developer,  
**I want** a written URL contract (`source_record_id` → URL + `links[]` roles),  
**So that** I can implement `build_faa_aids_links()` and a backfill job without guesswork.

---

## 4. Functional Requirements

*Spike deliverables — not production implementation.*

### FR-1: Bulk field inventory (MUST)

1. **FR-1.1** Export schema documentation for FAA AIDS bulk fields **already loaded in our DB** (column list, especially `c5` control number and any URL-like columns in `source_data`).
2. **FR-1.2** Download and inspect the **latest FAA AIDS ZIP** only (per §9) — confirm whether it includes `url`, `link`, or hyperlink columns populated.
3. **FR-1.3** Compare **imported bulk vs latest ZIP** for URL column presence and format drift (not a full historical archive review).

### FR-2: URL pattern discovery (MUST)

1. **FR-2.1** Research FAA public surfaces: data catalog, legacy AIDS/CAROL interfaces, FOIA portals, and any documented deep-link patterns.
2. **FR-2.2** If bulk has no URL, attempt **constructed URLs** from control number + date + registration (document each candidate pattern).
3. **FR-2.3** Record HTTP behavior: status codes, redirects, soft-404 pages, and content signals (control number visible in HTML/PDF).

### FR-3: Sample validation (MUST)

1. **FR-3.1** Draw a **stratified sample of 500** AIDS rows from `data/aircraft_safety.db` (or source ZIP): mix of years, fatal vs non-fatal, with/without registration.
2. **FR-3.2** For each candidate URL pattern, score: **match / redirect-ok / fail / unrelated**.
3. **FR-3.3** Re-test **50** URLs after 24h to check stability (same final URL, still valid).

### FR-4: Spike report & recommendation (MUST)

1. **FR-4.1** Write `Planning/spike-reports/0001-faa-aids-url-spike-report.md` with: methods, findings, sample stats, recommended URL builder spec, risks.
2. **FR-4.2** Include **go / conditional go / no-go** with effort estimate for Phase 2.
3. **FR-4.3** If **go**: draft minimal changes list (files: `faa_aids.py`, `faa_aids_importer.py`, `backfill_urls.py`, optional CLI).

### FR-5: Legal / operational check (SHOULD)

1. **FR-5.1** Note whether automated HEAD/GET validation for 500 URLs is acceptable under FAA site policies.
2. **FR-5.2** Document recommended rate limits for a future backfill (e.g. ≤1 req/s, User-Agent string).

---

## 5. Non-Goals (Out of Scope)

1. **Implementing** production backfill or changing `faa_aids_importer` behavior (spike only).
2. **Fuzzy or exact FAA↔NTSB merge** (already evaluated; 0 pairs).
3. **`enrich-linkless-incidents`** / MEDIA web search enrichment.
4. **Restoring Flask CLI commands** (`backfill-source-urls`, etc.) — deferred.
5. **Full-app QA pass** on incident lists — deferred.
6. **Scraping behind login**, paywalls, or non-public FAA systems.
7. **Guaranteeing 100% coverage** — spike only proves what is feasible.

---

## 6. Design Considerations

### UI (if Phase 2 follows)

- Reuse existing multi-link rendering in `app/templates/components/incident_list.html` and `global_incident_list.html` via `resolve_source_hrefs()`.
- **Primary** link = per-record FAA page when available; **secondary** `catalog` role retains current landing page as fallback (`app/ingestion/url_builders/faa_aids.py`).
- Do not show placeholder domains (`example.com`) — already blocked at ingest via `link_schema`.

### UX copy

- If only catalog URL exists, label **“FAA accident/incident data (catalog)”** — not “View report”.
- If per-record URL exists, label **“FAA AIDS record”** or equivalent FAA-official wording.

---

## 7. Technical Considerations

### Current codebase touchpoints

| File | Role today |
|------|------------|
| `app/ingestion/importers/faa_aids_importer.py` | Parses bulk; `source_url` from raw only if present |
| `app/ingestion/url_builders/faa_aids.py` | Catalog fallback when no `source_url` |
| `app/ingestion/backfill_urls.py` | `refresh_source_links` / `backfill_source_urls` (no Flask CLI wired on current branch) |
| `app/ingestion/bulk/faa_aids_bulk.py` | ZIP download + CSV parse (`FAA_AIDS_ZIP_URL_TEMPLATE`) |
| `data/aircraft_safety.db` | ~157k FAA_AIDS sources; production-sized |

### Spike methods (suggested)

1. **Static analysis** — grep bulk CSV/ZIP for `http`, `www`, column headers across vintages.
2. **Pattern probes** — script under `scripts/spikes/` (throwaway OK) to HEAD/GET candidate URLs for sample control numbers.
3. **Manual verification** — 20–30 random rows opened in browser; capture screenshots for report appendix.
4. **Cross-check** — rows that also have NTSB (rare) to see if FAA page exists for same event.

### Key identifiers

- **Control number:** `c5` → stored as `source_record_id` (see importer `parse()`).
- **Other useful fields:** `c9` date, `c203` registration, `c23`/`c24` make/model.

### Risks

| Risk | Mitigation |
|------|------------|
| FAA changes URL structure | Document version/date; prefer stable API over HTML scraping |
| Bulk never contained URLs | No-go or catalog + search URL tier only |
| Rate limiting during validation | Throttle; sample size 500 not full 157k |
| False positives (generic search results) | Human review subsample; require control # on page |

---

## 8. Success Metrics

### Spike completion metrics

| Metric | Target |
|--------|--------|
| Sample size tested | ≥500 records |
| Candidate patterns evaluated | ≥3 documented |
| Spike report delivered | Yes, with go/no-go |
| Timebox | ≤2 engineering days |

### Phase 2 metrics (only if **go** — for reference, not in spike scope)

| Metric | Target |
|--------|--------|
| FAA_AIDS rows with non-catalog `source_url` | ≥90% of active rows |
| Incident-level link coverage | Material lift above 32% (estimate in spike report) |
| Broken link rate (30-day re-check) | <5% on 200-row sample |
| Placeholder / catalog-only mislabeled as primary | 0 |

---

## 9. Decisions (confirmed 23 May 2026)

| # | Topic | Decision |
|---|--------|----------|
| 1 | **Bulk vintages** | **Only** data already imported in `data/aircraft_safety.db` **plus** the **latest FAA AIDS ZIP** from FAA (no historical archive sweep for now). Easiest scope: proves pattern for what we have + what we’d import next. |
| 2 | **“Conditional go” (search links)** | **Accepted** if we cannot find a reliable direct per-record URL. Spike must prove search links land on the right event ≥80% of the time; then we may ship those instead of blocking on a perfect direct link. See §9.1. |
| 3 | **Live FAA requests** | Yes — spike may hit live FAA sites from dev, with polite rate limits (e.g. ≤1 req/s). |
| 4 | **Go/no-go authority** | **You only** — no other sign-off required. |
| 5 | **If no-go** | MEDIA enrichment for fatal FAA-only rows stays **out of scope** until you review the spike report and choose next work. |

### 9.1 ELI5: What is “conditional go” (question 2)?

FAA might **not** give us a direct link like:

`https://faa.gov/.../record/12345` → always opens **that one** accident.

Sometimes the only option is a **search link**, like:

`https://faa.gov/search?q=12345` → opens a **search results** page; you hope the right event is there.

| Spike result | What it means | Example |
|--------------|---------------|---------|
| **Go** | Direct link works almost every time | Click → that exact AIDS record |
| **Conditional go** | No direct link, but search link usually lands on the right event | Click → search page, correct row visible ≥80% |
| **No-go** | Neither works reliably | Click → wrong page, empty, or login wall |

**Your preference:** conditional go is **OK** when direct links aren’t available — as long as the spike proves search links work well enough (≥80% in sample). **You** still make the final go / conditional go / no-go call when you read the report.

---

## 10. Spike execution plan (1–2 days)

### Day 1 — Discovery

1. Inventory bulk columns from DB + latest FAA ZIP (not full archive).
2. List ≥3 candidate URL patterns from FAA docs + bulk hints.
3. Build sample set (500 rows) from DB or source files.

### Day 2 — Validation & decision

1. Run automated validation script; tabulate match rates.
2. Manual QA on 20–30 edge cases (missing reg, old dates).
3. Write spike report + go/no-go.
4. If **go**: append Phase 2 implementation outline to report (do not code yet).

---

## 11. Phase 2 outline (reference only — not in spike scope)

*Execute only after **go**.*

1. Update `build_faa_aids_links()` with validated pattern(s) and `links[]` roles.
2. Set `source_url` in `FAAAIDSImporter.parse()` when derivable.
3. Run `refresh_source_links('FAA_AIDS')` in batches (SQLite: single writer, no parallel jobs).
4. Re-run coverage metric; QA 10 aircraft profiles with heavy FAA counts.

---

## Appendix A: Context from link enrichment (May 2026)

- **NTSB:** 75,499 active sources, all with URLs; `links[]` refresh completed.
- **ASN:** 1,796 / 1,796 with URLs.
- **FAA_AIDS:** 157,342 / 1 with URL — **primary gap**.
- **Exact FAA↔NTSB merge:** 0 pairs.
- **Overall incident coverage:** ~32% with ≥1 active URL.

---

## Appendix B: Related files

- Ryan Carson PRD process: `Bookmarks_knowledge_assistant/Planning/Prompts/PROMPT_create-prd(ryan carson).md`
- Context: `context/context-main-branch-asn-links-2026-05-18.md`
