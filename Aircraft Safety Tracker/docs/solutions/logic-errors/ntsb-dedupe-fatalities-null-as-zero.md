---
title: NTSB dedupe must treat null audit fatalities as zero like importer
date: 2026-05-30
category: logic-errors
module: ntsb-enrichment
problem_type: logic_error
component: ntsb_ingestion
symptoms:
  - "Dedupe re-pass marks row import but post-import audit finds ASN duplicate"
  - "Audit JSONL has fatalities null; dedupe only scores date match"
  - "After import NTSB row has fatalities=0 matching ASN row"
root_cause: logic_error
resolution_type: code_fix
severity: high
tags: [ntsb, dedupe, fatalities, null-coercion, ntsb-asn]
---

# NTSB dedupe must treat null audit fatalities as zero like importer

## Problem

Dedupe re-pass and bulk import used different fatality semantics, letting duplicate incidents slip through pre-import gates and appear only in post-import audit.

## Symptoms

- Post-import audit flagged 3 NTSB/ASN duplicates (e.g. ATL02LA075, FTW96LA269, SEA02FA060)
- Dedupe re-pass had marked those rows `import`
- Audit JSONL: `fatalities: null`; dedupe scoring ignored fatality signal

## What Didn't Work

- Scoring `fatalities_close` only when both sides non-null
- Assuming null audit fatalities mean "unknown" rather than "will become 0 on import"

## Solution

Add `fatalities_like_import()` in `app/ingestion/dedupe/ntsb_asn.py` — dedupe re-pass coerces null the same way `NTSBImporter` does (`parsed.get("fatalities") or 0`).

Test: `test_null_fatalities_coerced_like_import_skips_duplicate` in `tests/test_ntsb_dedupe_repasse.py`

Post-import audit (`audit_post_ntsb_import.py`) remains safety net.

## Why This Works

Import always writes 0 for missing fatalities; dedupe must predict post-import DB state, not raw audit JSON shape.

## Prevention

- Any scoring change in importer requires matching change in dedupe helpers
- Run post-import audit after bulk NTSB write
- See `CONCEPTS.md` → FAA dedupe pass, NTSB make/model map

## Related Issues

- LEARNINGS §38
- PRD 0006.3
