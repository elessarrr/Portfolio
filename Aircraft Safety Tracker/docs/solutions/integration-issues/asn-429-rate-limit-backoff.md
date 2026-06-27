---
title: ASN 429 rate-limiting silently dropped incidents — get_soup now backs off and retries
date: 2026-06-27
module: asn-ingestion
problem_type: integration_issue
component: development_workflow
severity: medium
related_components: [ntsb_ingestion]
tags: [asn, scraping, http-429, rate-limit, backoff, retry, ingestion, silent-failure]
symptoms:
  - "Local ASN refresh logs hundreds of 'Client error 429 Too Many Requests' for aviation-safety.net listing and wikibase pages"
  - "Scrape 'completes' but some models/incidents are missing or imported with null narrative/fatalities"
  - "Large catch-up run (~100+ new detail fetches) trips ASN's rate limiter where a small weekly run would not"
root_cause: rate_limit_or_throttle
resolution_type: code_fix
applies_when:
  - "A backfill/catch-up ASN run issues many requests back-to-back and gets throttled"
  - "You need a scraper to recover from 429 instead of swallowing it as a silent skip"
---

# ASN 429 rate-limiting silently dropped incidents

## Problem

The first big local ASN incremental refresh (catching up a months-old backlog) had ~107
genuinely-new incidents to fetch. Issuing every type-listing page plus ~107 detail pages
back-to-back tripped aviation-safety.net's rate limiter: **314 × `429 Too Many Requests`**
in a single run.

`scraper_utils.get_soup()` caught the 429 like any other error and returned `None`, so:
- a 429 on a **type-listing** page → that whole model was skipped that run, and
- a 429 on an **incident detail** page → the incident still imported but with a **null
  narrative/fatalities**.

Both were **silent** (same failure class as the ASN 403 cloud-IP issue): the run reported
`status=ok` despite incomplete/degraded data.

## Resolution

`get_soup()` now handles 429 explicitly with exponential backoff that respects a
`Retry-After` header, instead of swallowing it:

```python
def get_soup(url, client, *, max_retries=4, base_delay=2.0, sleep=time.sleep):
    for attempt in range(max_retries + 1):
        try:
            response = client.get(url, headers=HEADERS, timeout=30.0)
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}"); return None
        if response.status_code == 429:
            if attempt < max_retries:
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else base_delay * (2 ** attempt)
                sleep(wait); continue
            logger.error(f"429 ... exhausted {max_retries} retries"); return None
        ...
```

`sleep`/`max_retries`/`base_delay` are injected so tests run instantly (no real sleeping).
A persistent 429 after all retries is logged as an **ERROR** (surfaced), not a silent skip.

## Outcome

Re-running the backfill: **274 × 429, 136 backoffs, only 1 "exhausted"** — and that one loss
was a *listing* grouping page (`_B757`), not an incident. Across the two runs ~177 new
incidents were recovered and imported. Normal weekly runs fetch only a handful of new
incidents and won't trip the limiter at all; the backoff is the safety net for catch-up runs.

## Where

- `scripts/scraper_utils.py` — `get_soup()` 429 backoff/Retry-After loop.
- Tests: `tests/test_asn_incremental.py::TestGetSoupRateLimit` (retry-then-succeed,
  respects Retry-After, gives-up-after-max-retries, success-no-sleep).
- Sibling decision (why ASN is a local refresh at all): `asn-403-datacenter-ip-cloud-scrape.md`.
