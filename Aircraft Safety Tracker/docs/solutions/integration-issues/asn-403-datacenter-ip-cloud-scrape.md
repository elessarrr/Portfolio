---
title: ASN (aviation-safety.net) 403s cloud IPs — cron is NTSB-only, ASN is a local refresh
date: 2026-06-27
module: asn-ingestion
problem_type: integration_issue
component: development_workflow
severity: medium
related_components: [ntsb_ingestion]
tags: [asn, scraping, http-403, github-actions, cloud-ip, ingestion, false-positive]
symptoms:
  - "GitHub Actions run: HTTP 403 Forbidden on https://aviation-safety.net/asndb/types/B and /types/A"
  - "ASN scrape 'completes' having saved 0 incidents, yet weekly run reports status=ok (false green)"
  - "The identical scrape succeeds when run locally from a residential IP"
root_cause: rate_limit_or_throttle
resolution_type: code_fix
applies_when:
  - "Scheduling the weekly ingest or any aviation-safety.net scrape on a cloud runner"
  - "A scraper 'succeeds' with 0 rows and you need the orchestrator to treat that as failure"
---

# ASN 403s cloud IPs — cron is NTSB-only, ASN is a local refresh

## Problem

The first GitHub Actions dispatch of the weekly ingest (PRD 0012) showed NTSB working
(2 new Boeing/Airbus rows) but **ASN returning `403 Forbidden`** for both type-index
pages. aviation-safety.net blocks **datacenter/cloud IP ranges** (GitHub Actions = Azure,
also Railway). The realistic Chrome `User-Agent` is already sent and still 403s, so this
is **IP/ASN-based blocking, not a header problem** — a residential IP (the dev's home
machine) works fine.

Worse, the scrape failed **silently**: `scraper_utils.get_soup()` catches the 403, returns
`None`, `get_model_links()` returns `{}`, and `scrape_boeing.main()` finishes normally having
written 0 incidents. The orchestrator's retry wrapper only treats a raised exception as
failure, so ASN counted as a success and the whole run reported `status=ok` — a false green
on a job meant to be "set and forget".

## Resolution

1. **Cron is NTSB-only.** `run_ingest()` now defaults to `include_ntsb=True, include_asn=False`;
   the GHA workflow runs `scripts/weekly_ingest.py` with no flags → NTSB only. data.ntsb.gov
   is reachable from the cloud, so NTSB stays fully automated.
2. **ASN never reports a silent success.** `ingest_asn()` takes the scrape/import callables
   (injectable for tests), sums Boeing+Airbus counts, and **raises `RuntimeError` on a
   0-incident scrape** — a block surfaces as `status=partial`, never `ok`. `scrape_boeing.main()`
   / `scrape_airbus.main()` now return `len(all_incidents)` to feed this check.
3. **ASN is an opt-in local refresh** from a residential IP:
   - `PYTHONPATH=. python scripts/weekly_ingest.py --asn-only`  (ASN only)
   - `PYTHONPATH=. python scripts/weekly_ingest.py --with-asn`   (NTSB + ASN)
   It writes to the same `DATABASE_URL`, so a local run updates Railway Postgres directly.

## Why not a proxy

A residential proxy would let ASN run on GHA but adds recurring cost + a brittle dependency,
against the project's "$0, zero-maintenance" goal. ASN data for Boeing/Airbus changes slowly
and the historical corpus is already loaded, so an occasional manual local refresh is enough.

## Where

- `app/ingestion/weekly_ingest.py` — `run_ingest(include_ntsb/include_asn)`, `ingest_asn()` raise-on-zero.
- `scripts/weekly_ingest.py` — `--with-asn` / `--asn-only` flags.
- `scripts/scrape_boeing.py`, `scripts/scrape_airbus.py` — `main()` returns incident count.
- `.github/workflows/weekly-ingest.yml` — NTSB-only comment. Tests: `tests/test_weekly_ingest.py`.
