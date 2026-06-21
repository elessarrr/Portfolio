---
title: NTSB incremental ingest uses avdata monthly .mdb, not the CAROL JSON API
date: 2026-06-21
module: ntsb-enrichment
problem_type: tooling_decision
component: ntsb_ingestion
severity: medium
related_components: [development_workflow]
tags: [ntsb, carol, avdata, mdbtools, github-actions, ingestion, incremental]
applies_when:
  - "Adding or repairing automated NTSB data refresh"
  - "Tempted to call the CAROL backend JSON API for investigations"
  - "Choosing a host for a job that needs system packages like mdbtools"
---

# NTSB incremental ingest uses avdata monthly .mdb, not the CAROL JSON API

## Decision

For perpetual weekly NTSB refresh (PRD 0012), fetch the **NTSB avdata weekly update
files** (`https://data.ntsb.gov/avdata` → `up<DD><MON>.zip`, DD∈{01,08,15,22}, ~0.5 MB,
Microsoft Access `.mdb`), parse with **`mdbtools`**, filter Boeing/Airbus, and **diff
against existing `IncidentSource.source_record_id`** before importing. Run it on
**GitHub Actions** (writes to Railway Postgres), not a Railway cron.

## Why not the CAROL JSON API (approach A — rejected)

- `POST https://data.ntsb.gov/carol-main-public/api/Query/Main` is live and returns JSON,
  but **every column name is rejected**: `{"Error":"TableColumn <X> was not found within
  the configuration"}` (tried `Event Date`, `Mode`; `SortColumn` validated the same way).
- **No discoverable config/swagger** to enumerate valid columns (GetSearchTerms, GetColumns,
  swagger/v1, … all 404). Valid identifiers live only in the minified SPA bundle → any client
  is an undocumented, brittle, unsupported contract. Contrary to a "zero-maintenance" goal.
- Corroborated by PRD-0019 research: no documented public date-query endpoint.

## Why this works

- avdata is NTSB's official, stable bulk product; the importer + mapping already speak its
  shape. `aircraft.acft_make`/`acft_model` are UPPERCASE and `"{make} {model}"` (e.g.
  `"BOEING 737"`) is **exactly** the key format in `data/config/ntsb_make_model_to_aircraft.jsonl`,
  so `NTSBImporter` runs unchanged.
- Records get a deterministic docket URL (`data.ntsb.gov/Docket/?NTSBNumber=<ntsb_no>`) with
  **no network** during import (fetcher=None path in `resolve_ntsb_source_url`).
- Diff-on-`source_record_id` makes the exact file picked irrelevant — re-imports are no-ops.

## Gotchas

- **`mdb-export -D '%Y-%m-%d'` does NOT normalize dates** here — output is `MM/DD/YY HH:MM:SS`.
  Normalize in code (`_normalize_event_date`) or `NTSBImporter._parse_date` rejects every row.
- **mdbtools is the friction point**: it installs in one apt line on GitHub Actions but is painful
  on Railway's nixpacks/mise builder (cf. the Python attestation fight). Hence GitHub Actions host.
- New make/model strings absent from the mapping are silently dropped via
  `NTSBImporter.skipped_unmapped` — the weekly job must log that count prominently.

## Where

- `app/ingestion/clients/ntsb_bulk.py` (adapter), `app/ingestion/weekly_ingest.py` (orchestrator),
  `.github/workflows/weekly-ingest.yml` (host). Tests: `tests/test_ntsb_bulk.py`.
