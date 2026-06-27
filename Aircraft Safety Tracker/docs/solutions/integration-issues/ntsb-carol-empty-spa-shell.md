---
title: NTSB CAROL empty SPA shell is not a viable investigation link
date: 2026-05-27
category: integration-issues
module: ntsb-enrichment
problem_type: integration_issue
component: ntsb_ingestion
symptoms:
  - "carol.ntsb.gov returns HTTP 200 for investigation detail URL"
  - "Response body is empty React shell with main id root only"
  - "No investigation text in HTML"
root_cause: wrong_api
resolution_type: code_fix
severity: high
tags: [ntsb, carol, empty-spa, url-validation, link-viability]
---

# NTSB CAROL empty SPA shell is not a viable investigation link

## Problem

CAROL investigation detail URLs can return HTTP 200 while containing no usable investigation content, causing false "working link" classification in audits and imports.

## Symptoms

- URL pattern: `carol.ntsb.gov/investigations/detail/{mkey}`
- HTTP 200 with `<main id="root"></main>` and no investigation text
- Audit export marks row as viable when only HTTP status is checked

## What Didn't Work

- HTTP 200 alone as viability gate
- Assuming CAROL detail pages always render server-side HTML

## Solution

Reject via body check in `validate_ntsb_url()` / `is_carol_empty_spa_shell()`:

- Reason code: `carol_empty_spa`
- Fall back to docket URL when CAROL is empty shell
- Post-FR-12: `resolve_ntsb_source_url_checked()` uses url_builders.ntsb validators

## Why This Works

CAROL is a client-rendered SPA; empty shell means the page loaded but investigation data did not render — same user experience as a broken link.

## Prevention

- All NTSB URL audits must use body checks, not HEAD/HTTP status alone
- Mock validators in tests at `app/ingestion/url_builders/ntsb.py` after FR-12 refactor
- See `CONCEPTS.md` → `carol_empty_spa`

## Related Issues

- PRD 0006.x NTSB enrichment
- `tests/` for CAROL empty shell cases
