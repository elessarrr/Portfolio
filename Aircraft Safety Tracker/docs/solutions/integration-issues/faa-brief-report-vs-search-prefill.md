---
title: FAA brief report page 18 vs search prefill page 12
date: 2026-06-01
category: integration-issues
module: faa-aids
problem_type: convention
component: faa_ingestion
severity: high
applies_when:
  - "Auditing or migrating FAA AIDS source_url values"
  - "Deciding product-ready vs HTTP-OK URL buckets"
tags: [faa-aids, page-18, page-12, brief-report, asias, url-audit]
---

# FAA brief report page 18 vs search prefill page 12

## Context

FAA AIDS URLs on ASIAS exist in two forms: page 12 (search prefill) and page 18 (direct brief report). HTTP success on page 12 does not mean the user gets a one-click Details experience.

## Guidance

**Product-ready:** `working_brief_report` — ASIAS page 18 (`AP_BRIEF_RPT_VAR`). User clicks Details and sees the brief immediately.

**Not product-ready:** `working_search_prefill` — page 12 (`P12_AIDS_RPRT_NBR`). User must click Search AIDS again.

Default audit mode: `--url-mode brief` (page 18). DB write-back keeps active only for `working_brief_report`.

Migration: `migrate_faa_aids_urls_to_brief.py --apply --require-audit <jsonl>`

Importer default after PRD 0007.2: `build_faa_aids_brief_report_url()` → page 18.

## Why This Matters

Conflating page-12 HTTP OK with shippable links caused false sign-off. Three-tier buckets separate HTTP viability, product tier, and DB activation policy.

## When to Apply

- Any FAA URL audit, migration, or importer change
- Unit tests must assert `AP_BRIEF_RPT_VAR`, not `P12_AIDS_RPRT_NBR` (see LEARNINGS §51)

## Examples

```bash
python scripts/audit_faa_aids_urls.py --url-mode brief
python scripts/migrate_faa_aids_urls_to_brief.py --apply --require-audit data/logs/merged.jsonl
```

## Related

- `docs/solutions/integration-issues/asias-liveness-gate-false-positive-audit.md`
- PRD 0007.2, PRD 0009
- `CONCEPTS.md` → `working_brief_report`, `working_search_prefill`
