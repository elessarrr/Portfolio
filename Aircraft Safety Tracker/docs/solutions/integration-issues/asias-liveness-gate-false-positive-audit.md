---
title: ASIAS liveness gate prevents false-positive mass URL audit wipe
date: 2026-06-01
category: integration-issues
module: faa-aids
problem_type: integration_issue
component: url_audit
symptoms:
  - "ASIAS homepage returns Akamai CDN 503 during site-wide outage"
  - "Bulk per-record URL audit marks all FAA URLs not_working"
  - "apply_faa_audit_buckets_to_db deactivates thousands of valid brief links"
root_cause: incomplete_setup
resolution_type: workflow_improvement
severity: critical
tags: [asias, liveness-gate, faa-aids, false-positive, url-audit]
---

# ASIAS liveness gate prevents false-positive mass URL audit wipe

## Problem

Running a full FAA AIDS URL audit while ASIAS is globally down causes every per-record check to fail, producing a false-positive mass wipe of `is_active` flags in the database.

## Symptoms

- ASIAS homepage returns HTTP 503 (Akamai CDN error page), not just individual dead records
- All 6,466 per-record brief checks fail with `asias_cdn_error` or similar
- DB write-back sets `is_active=False` on URLs that were product-ready before the outage

## What Didn't Work

- Proceeding with bulk audit when homepage probe failed — individual checks also 503
- Treating spike success (500-row format proof) as substitute for full corpus audit

## Solution

Require **ASIAS liveness probe** (homepage HTTP 2xx) before any bulk URL audit or DB write-back:

```python
# app/ingestion/url_builders/faa_aids_viability.py — probe_asias_liveness()
```

Defer retry batches (retry4/retry5 cron) until liveness returns true. Document in `/audit-urls` skill and `Planning/runbooks/`.

## Why This Works

Site-wide CDN/backend failure affects homepage and all record URLs equally. Per-record checks cannot distinguish infra outage from dead IDs during an outage.

## Prevention

- Always run liveness probe first in audit CLI and cron wrappers
- Abort audit + DB apply when homepage ≠ 2xx
- JOURNAL/LEARNINGS: URL spike ≠ full audit (different questions)

## Related Issues

- `docs/solutions/integration-issues/faa-brief-report-vs-search-prefill.md`
- PRD 0007.1, PRD 0009
- `LEARNINGS.md` proactive bullet (linked)
