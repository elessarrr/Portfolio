# Session: May 2 — WA Incident Press Enrichment (Task 1.0)

## What we're doing

Implementing the **Press Article Enrichment Background Job** — task 1.0 from `tasks-0020-prd-wa-incident-press-enrichment-and-faq.md`. The goal is to automatically find press/news coverage for WA-coded NTSB incidents (international investigations where the NTSB docket is typically not released) and attach those links as `IncidentSource` records with `source_name='MEDIA'`.

## Why this matters

WA-coded incidents (Western Region, international) don't get NTSB dockets released. But press coverage often exists on Aviation Herald, Reuters, AP, etc. Without enrichment, users have no way to find any information about these incidents beyond what was in the original import. This feature closes that gap.

---

## What was built

### `app/services/web_search.py` (new)

| Component | Purpose |
|---|---|
| `SearchResult` dataclass | Holds url, title, tier, domain per candidate |
| `_rate_limit()` | Per-domain throttling (0.3s) to avoid IP bans |
| `_retry()` | Exponential backoff retry helper — configurable attempts, base delay, and exception types |
| `validate_url()` | HTTP GET → 200 + non-empty body required. Retries transient errors (timeout, transport) up to 3x with 1.0s base delay |
| `_duckduckgo_search()` | Scrapes DuckDuckGo HTML results (no API key needed). Falls back gracefully when blocked |
| `_search_aviation_herald()` | Tier 1: `site:aviation-herald.com` query |
| `_search_news_wires()` | Tier 2: Reuters + AP + Bloomberg via site: clauses |
| `_search_general()` | Tier 3: unfiltered web search |
| `WebSearchService.search_tiered()` | Orchestrates tiers; stops at first tier returning ≥1 validated result; caps at 5 articles |

Key design: DuckDuckGo HTML scraping was chosen over a paid search API (SerpAPI, Google Custom Search) to keep infra costs at zero. The tradeoff is that DDG blocks some users/CDNs — the code degrades gracefully (returns empty list, cascades to next tier).

### `app/ingestion/cli.py` — added `enrich-wa-incidents`

The CLI command attached to the `import-data` group. Target identification:

```sql
-- NOT targeted (has active NTSB)
SELECT incident_id FROM incident_source
  WHERE source_name='NTSB' AND is_active=True

-- Targeted (inactive NTSB only, no MEDIA)
SELECT incident_id FROM incident_source
  WHERE source_name='NTSB' AND is_active=False
  AND incident_id NOT IN (SELECT incident_id FROM incident_source WHERE source_name='MEDIA')
  AND incident_id NOT IN (SELECT incident_id FROM incident_source WHERE source_name='NTSB' AND is_active=True)
```

When an article is found:
- `source_name = 'MEDIA'`
- `source_record_id = domain`
- `source_url = best_article_url`
- `is_active = True`
- `confidence_level = 'Low'`
- `source_data = { enrichment_tier, enrichment_event_id, articles: [all candidates] }`

All-candidate storage means if the best URL breaks later, the alternatives are still in `source_data`.

### `tests/test_web_search_service.py` — 18 unit tests
### `tests/test_enrich_wa_incidents.py` — 9 integration tests

Both pass cleanly (27/27).

---

## Key decisions and tradeoffs

### 1. DuckDuckGo vs paid search API
**Decision:** DuckDuckGo HTML scraping
**Rationale:** Zero cost, no API key needed, works for Aviation Herald and news sites
**Risk:** DDG may 403 block some IPs; cascading to next tier mitigates this

### 2. Tiered search instead of parallel
**Decision:** Run tiers sequentially, stop at first success
**Rationale:** Tier 1 (Aviation Herald) is most relevant and cleanest; lower tiers add noise. Stopping early is correct behavior.
**Alternative considered:** Parallel all tiers → more results but more HTTP load and no confidence ordering

### 3. Idempotency — SQL vs in-loop check
**Decision:** SQL query excludes `MEDIA` incidents (primary), in-loop `existing` check as secondary guard
**Rationale:** The SQL-level exclusion means a re-run is cheap (0 targets found). The in-loop check is redundant but acts as a defensive backup.

### 4. Retry vs fail-fast on transient errors
**Decision:** Retry `httpx.TimeoutException` and `httpx.TransportError` 3x with exponential backoff (1.0s base)
**Rationale:** Cloudflare/CDN timeouts are often transient. 3 retries with backoff avoids both hammering a failing server and giving up too quickly.
**Non-retried:** 4xx/5xx responses and empty bodies — these are deterministic failures, retrying won't help.

### 5. Rate limiting — why 0.3s per domain
**Decision:** 0.3s between requests to the same domain
**Rationale:** Based on prior experience with `validate_incident_links.py` — Cloudflare flags IPs that make >100 requests/minute to the same domain. 0.3s = 200 requests/minute max per domain, with headroom.

### 6. `confidence_level = 'Low'` for MEDIA sources
**Decision:** All enriched MEDIA sources are `confidence_level='Low'`
**Rationale:** Press links are less authoritative than NTSB dockets. Keeping them visually distinguishable in the UI (task 2.0) is important — this field drives that.

---

## What's next (tasks 2.0–5.0, not yet started)

| Task | What it involves |
|---|---|
| 2.0 | Template changes — ensure `incident_list.html` and `global_incident_list.html` render MEDIA links with no special styling |
| 3.0 | Add FAQ link note to WA incidents in templates ("No official NTSB docket — why?") |
| 4.0 | New `/faq` route and `faq.html` template with ICAO Annex 13 explanation + national authority table |
| 5.0 | Add FAQ link to site navigation in `base.html` |

---

## File locations

```
Aircraft Safety Tracker/
├── app/
│   ├── services/
│   │   └── web_search.py          ← new
│   └── ingestion/
│       └── cli.py                 ← modified (added enrich-wa-incidents)
├── tests/
│   ├── test_web_search_service.py ← new (18 unit tests)
│   └── test_enrich_wa_incidents.py ← new (9 integration tests)
└── Planning/
    ├── tasks/
    │   └── tasks-0020-prd-wa-incident-press-enrichment-and-faq.md  ← PRD
    └── sessions/
        └── May_2_press_article_enrichment.md ← this file
```

## Running the job

```bash
cd "/Users/Bhavesh/Documents/GitHub/Portfoilo/Aircraft Safety Tracker"

# Preview
flask import-data enrich-wa-incidents --dry-run

# Execute
flask import-data enrich-wa-incidents
```

## Test command

```bash
cd "/Users/Bhavesh/Documents/GitHub/Portfoilo/Aircraft Safety Tracker"
python -m pytest tests/test_web_search_service.py tests/test_enrich_wa_incidents.py -v
```
