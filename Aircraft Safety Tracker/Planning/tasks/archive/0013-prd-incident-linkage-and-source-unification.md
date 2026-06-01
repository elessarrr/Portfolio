# 0013-prd-incident-linkage-and-source-unification

## 1. Introduction / Overview

This PRD addresses the root cause of the "missing data sources" bug: the vast majority of
NTSB and FAA_AIDS incidents in the database have `aircraft_id = NULL`, making them
structurally invisible to every aircraft detail page and incident list view. It also
resolves the FAA_SDR zero-records pipeline failure and eliminates the split data model
where ASN incidents bypass the `IncidentSource` table entirely.

**Scope:** Boeing and Airbus aircraft only (commercial aviation focus). General aviation
records that cannot be resolved to a Boeing/Airbus `Aircraft` row are intentionally left
unlinked and are out of scope.

---

## 2. Problem Statement

| Symptom | Root Cause |
|---|---|
| Aircraft detail pages show 0 incidents despite 240k+ records in DB | `incident.aircraft_id IS NULL` for ~236k rows; routes filter by `aircraft.incidents` relationship |
| Only ASN incidents appear | ASN legacy importer sets `aircraft_id` directly; NTSB/FAA use `IncidentSource` but linkage fails |
| FAA_SDR shows 0 processed records | Pipeline bug — separate from linkage issue |
| No repeatable backfill mechanism | `scripts/backfill_aircraft_ids.py` was deleted |
| ASN incidents have no `IncidentSource` row | Legacy `scripts/import_data.py` writes `asn_url` directly, bypassing the unified source model |

---

## 3. Goals

1. **Backfill** — Recreate a repeatable, safe backfill script that links historical orphaned
   Boeing/Airbus incidents to their `Aircraft` rows.
2. **Fix-forward** — Harden `resolve_aircraft()` so future imports link correctly on first
   ingest.
3. **FAA_SDR pipeline** — Diagnose and fix the zero-records ingestion failure.
4. **ASN unification** — Migrate existing ASN incidents to also have `IncidentSource` rows,
   eliminating the split data model.

---

## 4. Non-Goals

- Linking non-Boeing/Airbus (general aviation) incidents.
- Adding new data sources.
- Changing the UI or display logic (PRD-0012 already handles that).
- Re-importing raw data from scratch.

---

## 5. Success Metrics

| Metric | Target |
|---|---|
| Linked Boeing/Airbus NTSB incidents | Materially higher than current 3,710 |
| Linked Boeing/Airbus FAA_AIDS incidents | Materially higher than current 1 |
| FAA_SDR processed records per run | > 0 |
| ASN incidents with an `IncidentSource` row | 1,798 / 1,798 (100%) |
| `backfill_aircraft_ids.py` present in `scripts/` | ✅ |
| All four phases have passing tests | ✅ |

---

## 6. Phases

### Phase 1 — Recreate the Backfill Script
Recreate `scripts/backfill_aircraft_ids.py` as a safe, idempotent, batch-processing script
that retroactively links orphaned Boeing/Airbus incidents to `Aircraft` rows.

### Phase 2 — Harden `resolve_aircraft()` Fix-Forward
Improve the resolver so future ingestion runs link Boeing/Airbus incidents correctly on
first import, without requiring a post-hoc backfill.

### Phase 3 — Fix FAA_SDR Zero-Records Pipeline
Diagnose why `last_records_processed = 0` for FAA_SDR and fix the pipeline so it
processes and links records correctly.

### Phase 4 — Unify ASN into `IncidentSource`
Migrate existing ASN incidents to have `IncidentSource` rows, and update
`scripts/import_data.py` to write `IncidentSource` rows on future runs.

---

## 7. Affected Files (Expected)

| File | Phase |
|---|---|
| `scripts/backfill_aircraft_ids.py` | 1 (create) |
| `app/ingestion/importers/base.py` | 2 |
| `app/ingestion/importers/ntsb_importer.py` | 2 |
| `app/ingestion/importers/faa_aids_importer.py` | 2 |
| `app/ingestion/importers/faa_sdr_importer.py` | 3 |
| `app/ingestion/bulk/faa_sdr_bulk.py` | 3 |
| `app/ingestion/clients/` (if FAA_SDR has a client) | 3 |
| `scripts/import_data.py` | 4 |
| `app/models.py` | 4 (read-only verify) |
| `tests/test_importer_base.py` | 2 |
| `tests/test_faa_sdr_importer.py` | 3 |
| `tests/test_faa_sdr_bulk.py` | 3 |
| `tests/test_asn_sync.py` | 4 |

---

## 8. Open Questions

- None. Scope is locked per product decision: Boeing/Airbus only, backfill + fix-forward,
  FAA_SDR in scope, ASN migration in scope.
