# MCD: NTSB Enrichment Audit Pipeline (2026-05-29)

**PRD:** 0006.1 — NTSB Enrichment (v3)  
**Branch:** `v3-boeing-airbus-links`  
**Status:** Full-corpus audit complete — **review gate** before write-path import

---

## Summary

Implemented dedupe unit tests, NTSB link viability gate, and full-corpus enrichment audit (no DB writes). Product must review `data/logs/ntsb_enrichment_full_audit.json` before Task 6 (write path).

## Full-corpus audit results (2026-05-29)

| Bucket | Count |
|--------|------:|
| Total Boeing/Airbus NTSB records | 3,710 |
| Parsed | 3,710 |
| Skipped (ASN deduped) | 61 |
| Unknown aircraft (included, limited dedupe) | 3,482 |
| **Viable unique** | **3,649** |
| **Working links** | **679** |
| Broken links | 2,970 |
| Unreleased docket | 2,970 |

**Sample audit (500 records):** 44 viable → 2 working, 42 broken.

## Architecture

```text
data/raw/ntsb_records_full.json  (export from v2 DB)
  → scripts/audit_ntsb_enrichment.py
      → NTSBImporter.parse() — Boeing/Airbus filter
      → find_boeing_airbus_aircraft_id() — lookup only
      → score_ntsb_vs_asn() — skip if ASN-covered (when aircraft_id known)
      → include unknown-aircraft rows (FR-6.1)
      → resolve_ntsb_source_url()
      → validate_ntsb_url() — HTTP GET, reject unreleased dockets
  → data/logs/ntsb_enrichment_full_audit.json
  → [REVIEW GATE — product approval]
  → Task 6: NTSBImporter enrichment write path (not started)
```

## New / modified modules

| File | Role |
|------|------|
| `app/ingestion/dedupe/ntsb_asn.py` | Score-based dedupe (≥2 strong signals) |
| `app/ingestion/url_builders/ntsb_viability.py` | `validate_ntsb_url()` — docket body check |
| `scripts/audit_ntsb_enrichment.py` | Audit CLI: `--check-links`, `--include-unknown-aircraft` |
| `scripts/export_ntsb_boeing_airbus.py` | Export v2 `IncidentSource.source_data` → JSON |
| `tests/test_ntsb_dedupe.py` | Dedupe edge-case tests |
| `tests/test_ntsb_link_viability.py` | Mocked HTTP viability tests |

## Key decisions

1. **Unknown aircraft included** per FR-6.1 — 3,482 rows had no v3 `aircraft_id`; ASN dedupe skipped (FR-6.2). Viable count is inflated vs strict dedupe; model normalization needed before write.
2. **Link gate rejects ~81%** of viable unique (2,970/3,649) — mostly unreleased dockets on foreign-led/DirectorBrief cases.
3. **UI freeze holds** — no template changes until product approves working-link set (679 candidates).

## Open items before write path

- Product review of 679 working-link rows
- Model normalization for unknown-aircraft rows (PRD open question #3)
- Decide whether to insert only the 679 with working links among known-aircraft subset first
