# Catalog of Engineering Learnings

A curated set of non-obvious lessons from building this project across two major versions — from a single-source scrape to a three-source, URL-verified incident tracker. Intended as a reference for anyone working in similar territory: data pipelines, government APIs, Flask applications, or multi-source deduplication.

Grouped by theme. The internal `LEARNINGS.md` contains the full numbered inventory with verbatim error messages; this document extracts the ones with broader transferability.

---

## 1. URL validity is not the same as link quality

**HTTP 200 is not a product guarantee.**

Three distinct failure modes looked identical from the outside:

- **NTSB unreleased dockets** — returned HTTP 200 with body text "The docket for this investigation has not been released." A status-only check passes; a user clicking through hits a dead end.
- **NTSB CAROL SPA shells** — `carol.ntsb.gov/investigations/detail/{id}` returns HTTP 200 with an empty `<main id="root"></main>`. The page is a React app that never hydrated. No investigation content is present.
- **FAA ASIAS search prefill vs. brief report** — the "page 12" ASIAS URL pre-fills a search form; the user still has to click "Search AIDS" to see anything. The "page 18" URL opens the brief report directly. Both return 200. Both are technically "reachable." Only one is a usable link.

**The fix in all three cases:** classify by response *body content*, not HTTP status. Define what "working" means from the user's perspective, not the server's.

---

## 2. Infrastructure behaviour is a product consideration

When auditing 6,500 FAA ASIAS URLs, 49 records classified as "not working" after an aggressive concurrent pass (16 workers, 15-second timeout). The same 49 URLs, checked three days later with gentler settings (3 workers, 25-second timeout, 500–1500ms random jitter between requests), returned 49/49 working. Same URLs. Same data.

The original failures were rate limiting and Akamai CDN throttling under load — not bad records.

**The practical implication:** before concluding that a record is genuinely dead, distinguish between "the URL failed under our load" and "the URL doesn't exist." For government portals operating under budget constraints and not built for bulk automated access, the former is common.

**Related:** any bulk audit of a government API needs a liveness gate on the homepage before running individual checks. The ASIAS portal has experienced site-wide CDN outages where the homepage returned a CDN error page. Without a liveness check, a 20-minute outage would soft-delete 6,000+ active records.

---

## 3. Cross-agency deduplication requires conservative thresholds

The same real-world aviation accident often appears in ASN, NTSB, and FAA AIDS — three agencies maintaining independent databases with no shared primary key. Matching the same event across sources requires fuzzy scoring on date proximity, operator name similarity, location text, and fatality count.

The key design choice: **set the match threshold conservatively high.** A false positive (merging two different incidents into one row) is worse than a false negative (showing two rows for the same event). Users can handle apparent redundancy; they cannot recover from silently dropped records.

**Specific gotcha:** null fatalities in the source data. The audit pipeline scored null fatalities as "unknown" (not comparable), but the import step stored them as `0`. A record that didn't match at audit time would match post-import — producing a duplicate that the post-import audit then had to find and remediate. The fix: align the deduplication scoring function to use the same null-to-zero coercion as the importer.

---

## 4. Government data portals are not built for developers

Several discoveries that weren't obvious before starting:

- **ASIAS is the only public per-record URL source for FAA AIDS data.** `av-info.faa.gov` redirects to ASIAS. FAA removed the AIDS dataset from `faa.gov/data_research` in 2022. There is no data.gov per-record endpoint. If ASIAS is down, there is no alternative.
- **NTSB CAROL** is a JavaScript SPA. Static HTTP fetches return the shell only, not investigation content. Any viability check must either use a headless browser or detect the empty shell pattern in the HTML.
- **The FAA AIDS bulk export format** stores the incident ID in column `c5`, make in `c23`, model in `c24`. The column names are not documented in the ZIP; they required inspection of the raw CSV.
- **FAA AIDS make/model strings** (e.g. "BOEING 737-8H4", "BOEING 737-7H4") don't map directly to product catalog pages (e.g. "Boeing 737-800"). A 725-string mapping file, built by hand with script assistance, bridges the gap.

**The meta-lesson:** when building on government data, budget time to understand the source's own internal structure before writing import logic. The URL format, the column names, the edge cases in bulk exports — these are not documented and require investigation.

---

## 5. Schema decisions made at import are hard to undo

Early in the project, FAA AIDS records were imported with "page 12" search-prefill URLs (`P12_AIDS_RPRT_NBR`). These were technically reachable but required an extra click. Migrating 6,084 records to page-18 brief URLs required:

1. A full re-audit of all 6,466 records against the new URL pattern
2. A gated migration script (`--require-audit` enforces the audit must have run before any DB write)
3. A separate overlay merge pipeline to reconcile multiple retry passes
4. A post-migration smoke test

The cost wasn't catastrophic, but it took a full sprint. **Choosing the right URL format at import time would have cost an afternoon.** When the source offers multiple URL types for the same record, test the user experience of each before committing to one.

---

## 6. "Working" has three different meanings in a data pipeline

Useful taxonomy that emerged from this project:

| Level | What it means | Example |
|-------|--------------|---------|
| **HTTP working** | Server returned a response | 200 OK, even with empty body |
| **Product working** | User lands on meaningful content | ASIAS brief report page with narrative text |
| **DB working** | Record is active and will be shown in the UI | `is_active=True` after overlap audit |

A record can be HTTP working, product broken, and DB active at the same time (the original page-12 FAA URLs). A record can be HTTP working, product working, but DB inactive (a FAA record that duplicates an ASN baseline incident).

Auditing only at the HTTP layer misses the product layer. The `working_brief_report` / `working_search_prefill` / `not_working` bucket taxonomy in this project encodes the distinction.

---

## 7. Soft deletes preserve optionality; hard deletes don't

All "dead" links in this project are handled with `is_active=False` on the `IncidentSource` row, not by deleting the row. Reasons this paid off:

- When 49 FAA records appeared "not working" due to CDN throttling, restoring them was a single `--apply` pass after a successful retry. No re-import required.
- When the FAA vs ASN overlap audit found 13 records that duplicated the ASN baseline, deactivating them preserved the FAA provenance data while hiding the duplicate from the UI.
- Post-import audits can re-examine any record and reverse a deactivation if the original classification was wrong.

The cost: the DB grows; queries filter on `is_active`. For 10,000-record scale, that's negligible. For larger datasets, consider whether the optionality is worth the storage and query overhead.

---

## 8. Data pipelines need the same practices as application code

Scripts that modify production data should support:

- `--dry-run` mode that computes and logs what *would* change without touching the DB
- `--apply` that requires an explicit flag (don't default to writing)
- Idempotency — running the same script twice should produce the same result
- Audit logs (JSONL output) that record what changed and why

These practices feel like overhead when writing a one-off migration script. They pay back when the script needs to be re-run after a retry, or when a future engineer (or future you) needs to understand what state the DB was in at a given point.

---

## 9. Flask Jinja globals must be registered at app startup

`app/__init__.py` registers template globals like `display_ai_summary()` and `pick_primary_href()` when the app is created. A running Flask dev server started *before* those globals were added will serve 500 errors on any page that calls them — with no indication in the error page of what's actually missing.

The failure mode (`jinja2.exceptions.UndefinedError: 'display_ai_summary' is undefined`) only appears in the Flask console output, not the browser error page. After adding new Jinja globals, restart the dev server.

---

## 10. PostgreSQL fuzzy search is more capable than most application-layer implementations

The `pg_trgm` extension enables similarity matching directly at the database layer. Enabling it and using `%` (similarity) or `ilike` with trigram indexes means the database handles all the fuzzy logic — no Python loop, no in-memory scoring, no loading full result sets to filter down.

For aircraft model search ("Boing 737" → "Boeing 737"), this is both simpler and faster than any application-layer implementation. The cost is production-only (SQLite doesn't support `pg_trgm`), which means local dev uses `ILIKE` and production uses trigram similarity — test both paths.

---

*Full error inventory with verbatim messages, root causes, and fixes: see `LEARNINGS.md`.*  
*Engineering log with per-sprint outcomes: see `JOURNAL.md`.*
