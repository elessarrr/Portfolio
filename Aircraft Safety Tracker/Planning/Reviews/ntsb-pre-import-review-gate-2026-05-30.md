# NTSB Pre-Import Review Gate (0006.3 — Task 5.19)

**Status:** Complete — pilot import passed (5.19.3 + 5.20)  
**Generated:** 2026-05-30  
**Inputs:** `data/config/ntsb_make_model_to_aircraft.jsonl`, `data/logs/ntsb_enrichment_audit_rows.jsonl`, `data/aircraft_safety_v3.db`

---

## Executive summary

| Metric | Count | Notes |
|--------|------:|-------|
| Working-link rows (Task 5.10) | **657** | Unchanged from link-quality audit |
| Mapping coverage | **657 / 657** | 279 distinct strings → 50 target pages; 0 unmapped |
| **Import candidates (after dedupe re-pass)** | **396** | Rows with `dedupe_repasse_status=import` |
| Newly ASN-covered at re-pass | **51** | Would duplicate ASN baseline — **do not import** |
| Pending `create_approved` pages | **210** | **15** empty catalog pages bootstrapped on pilot DB before incident import (FR-20.0), not at first insert |
| Distinct existing catalog IDs used | **35** | Of 97 current v3 aircraft |
| Distinct canonical page names | **50** | 35 existing + 15 to create |

**Net new incidents expected after bulk import:** ~396 (subject to pilot verification in 5.20).

---

## Artifacts (5.18 outputs)

| File | Purpose |
|------|---------|
| `data/logs/ntsb_pre_import_summary.json` | Review gate counts (FR-19.2) |
| `data/logs/ntsb_dedupe_repasse.json` | Dedupe re-pass report + 10 sample matches (FR-18.2) |
| `data/logs/ntsb_enrichment_audit_rows_normalized.jsonl` | 657 rows enriched with mapping + `dedupe_repasse_status` (FR-19.1) |

**Tooling:** `scripts/ntsb_dedupe_repass.py` · `scripts/bootstrap_ntsb_create_approved_pages.py` · `app/ingestion/ntsb_dedupe_repass.py`

---

## 5.19.1 Count verification (automated)

- [x] `working_link_total` = 657 (matches Task 5.10 export)
- [x] `skipped_unmapped` = 0 (FR-16.3 100% string coverage holds at row level)
- [x] Status partition sums to 657: 396 import + 51 skip_asn_covered + 210 skip_pending_create
- [x] `newly_deduped_count` = 51 = `skipped_asn_covered_repasse` (all working-link rows were import-viable at audit; re-pass recovered ASN dedupe for previously `unknown_aircraft` rows)
- [x] 15 distinct `create_approved` target pages account for 210 rows (81 strings → 15 pages per mapping builder stats)

---

## 5.19.2 Spot-check — mapping intent (sample)

### Import candidates (roll to existing pages)

| NTSB string | Target page | Action |
|-------------|-------------|--------|
| `Boeing 757` | Boeing 757-200 | map_to_existing |
| `Boeing 737-300` | Boeing 737-300 | map_to_existing |
| `Airbus Industrie A300B4-605R` | Airbus A300 | map_to_existing |
| `Boeing 727-224` | Boeing 727-200 | map_to_existing |

### Newly deduped (skip — ASN already has incident)

| NTSB string | Target page | ASN incident | Signals |
|-------------|-------------|--------------|---------|
| `Airbus Industrie A320-200` | Airbus A320 | id 4554 | date + location |
| `Boeing 767-332` | Boeing 767-300 | id 2181 | date + operator + location |
| `BOEING 717-200` | Boeing 717 | id 253 | date + operator |

### Pending create (bootstrap before pilot import)

| NTSB string | New page (FR-20.0 bootstrap) |
|-------------|-------------------|
| Generic 737 family strings | **Boeing 737** |
| `BOEING 787-8` etc. | **Boeing 787** |
| Helicopter strings | **Airbus Helicopters AS350**, **EC135**, etc. |
| `BOEING MD-82` | **Boeing MD-82** |

All 15 new page names contain **Boeing** or **Airbus** (FR-23). Created as empty catalog rows on pilot clone **before** incident import — not lazily at first insert.

---

## Risks / notes for pilot (5.20)

1. **210 rows** on new family pages: dedupe re-pass on v3 DB used lookup-only (`skip_pending_create`). After bootstrap on pilot DB, optional re-run may recover a few more ASN dupes, but **family rollups** (e.g. generic `Boeing 737`) still won't match ASN on variant pages (`Boeing 737-300`, etc.).
2. **396 import candidates** is the bulk-import set (`dedupe_repasse_status=import`), not the raw 657.
3. Raw NTSB `make_model` preserved on each row for future Make/Model column (Task 6.8).
4. **Pilot order:** clone DB → bootstrap 15 pages → (optional) dedupe re-pass → import 30 incidents.

---

## 5.19.3 Product decision

- [x] **Approve** proceed to pilot import (Task 5.20) with 396-row import candidate set
- [ ] **Hold** — specify overrides (mapping edits, count concerns)

**Sign-off:** Product (chat) · Date: 2026-05-30

---

## 5.20 Pilot import results (2026-05-30)

| Step | Result |
|------|--------|
| Clone DB | `data/aircraft_safety_v3_pilot.db` |
| Bootstrap | 15 pages created (`ntsb_bootstrap_create_approved_pilot.json`) |
| Dedupe re-pass (pilot) | 606 import candidates (210 formerly `skip_pending_create` now importable) |
| Import | **30/30** written (`scripts/ntsb_pilot_import.py run-all`) |
| Verify | **0 issues** — pages, URLs, no ASN dupes (`ntsb_pilot_import_report.json`) |

**Next:** Task 5.21 bulk import on real v3 DB (bootstrap + 396-row import set).
