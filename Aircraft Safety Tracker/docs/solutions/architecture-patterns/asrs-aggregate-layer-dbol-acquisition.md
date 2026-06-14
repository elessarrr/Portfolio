---
title: ASRS aggregate layer — aircraft-type aggregation, not incident joins
date: 2026-06-06
last_updated: 2026-06-04
category: architecture-patterns
module: asrs-integration
problem_type: architecture_pattern
component: development_workflow
severity: medium
applies_when:
  - "Evaluating NASA ASRS as a data source for the aircraft safety tracker"
  - "Planning CSV acquisition from ASRS Database Online (DBOL)"
  - "Designing crew-reported safety UI distinct from official incident records"
tags: [asrs, dbol, csv-export, aggregate-profile, data-acquisition, prd-0010]
---

# ASRS aggregate layer — aircraft-type aggregation, not incident joins

## Context

PRD 0010 proposes a **Crew Safety Reports / contributing factors** panel on aircraft detail pages using NASA ASRS data. ASRS is voluntary, confidential, and de-identified — it captures near-misses and systemic concerns, not confirmed accidents with stable per-report URLs.

Initial DBOL search for **B737 All Series** returned **23,252 ACNs**, but CSV export was blocked above the per-session download cap (UI showed **5,000**; NASA docs cite up to **10,000**). There is **no public ASRS bulk API**.

## Guidance

### Product model: aggregate at aircraft-type level

Do **not** join ASRS reports to individual `Incident` rows. The unit of analysis is **`Aircraft.model_name`**, not a specific accident.

**Show:** coded factor percentages, top event types, `n =` report count, disclaimer, link to ASRS DBOL search.

**Do not show:** per-incident ASRS links, implied 1:1 mapping to ASN/NTSB/FAA events, or narrative quotes in v1.

Official records (ASN/NTSB/FAA) and voluntary crew reports (ASRS) are **complementary layers** — the gap between them is a product signal, not a dedupe problem.

### Data acquisition (no public API)

| Path | When to use |
|------|-------------|
| **Hugging Face bulk (primary v1)** | `elihoole/asrs-aviation-reports` (~47.7k rows). One command: `scripts/import_asrs.py --source huggingface --apply`. Requires `requirements-ingest.txt` / `.venv-asrs` if conda pyarrow broken. |
| **DBOL CSV gap-fill** | Models missing from HF snapshot; per-model export ≤5k rows. |
| **Date-range sharding** | Large DBOL families only when HF + gap-fill insufficient. |

**Importer:** `scripts/import_asrs.py` — HF, `--csv`, `--csv-dir`; dedupe on `acn`; overrides in `data/config/asrs_make_model_to_aircraft.jsonl`.

**Measured (2026-06-18):** 47,723 rows imported; 53 catalog aircraft with n>0; ship gate PASS. See `data/logs/asrs_coverage_summary.json`.

**Post-review remap (2026-06-04, PRD 0012):** Matcher hardened (min 4-char substring keys; family rollup; tie → None). `scripts/remap_asrs_aircraft_ids.py --apply` cleared 3,682 false-positive assignments (Boeing 40 n=881, Boeing 80 n=570 removed). Matched rows 17,226 → 13,544; top models (737-800, A320) unchanged.

### Aircraft matcher rules (`app/ingestion/asrs_aircraft_match.py`)

- Exact compact match wins over substring / fuzzy family.
- Substring `in` checks require `series_key` length ≥ 4 (avoids Boeing 40/80 matching `737400` / `A380`).
- Generic `B737` with no variant digit → family rollup row (`series_key == family_key`).
- Equal top scores after tie-breakers → unmatched (`None`).
- After rule changes: `scripts/remap_asrs_aircraft_ids.py` recomputes `aircraft_id` from stored raw strings (no HF re-download).

**Prerequisite:** `flask db upgrade head` before `import_asrs.py --apply` (no `db.create_all()` in import script).

**Non-goal:** Playwright DBOL scraping; NASA staff extract (closed, no response).

### Blocker framing

| Track | Blocked? |
|-------|----------|
| Engineering (schema, importer, UI card, tests) | **No** — build against any small CSV sample |
| Full coverage on all 153 models | **Yes (soft)** — until CSVs exist via sharding, per-model pulls, or NASA response |
| Portfolio demo | **No** — panel on models with `n > 0` is credible; hide when `n = 0` |

Engineering and NASA outreach should run **in parallel**.

## Why This Matters

Treating ASRS like ASN/NTSB/FAA (per-record `IncidentSource` with verified Details links) fights the dataset's confidentiality design and fails on missing stable URLs. Aggregate profiles reuse existing aircraft-page mental models while staying honest about voluntary, non-accident data.

## When to Apply

- Scoping PRD 0010 or any ASRS UI work
- Estimating data-acquisition effort before promising full fleet coverage
- Writing external requests to NASA ASRS (keep under form limits; state non-commercial portfolio use)

## Examples

**Wrong:** "Link ASRS report ACN 123456 to NTSB incident MIA08FA123."

**Right:** "On Boeing 737-800 page, show Human Factors 63%, Equipment 31%, `n = 412`, disclaimer, link to DBOL."

**Acquisition shard example (B737 All Series):**

| Shard | Occurrence dates | Export |
|-------|------------------|--------|
| 1 | 1970–1999 | CSV ≤5k |
| 2 | 2000–2009 | CSV ≤5k |
| … | … | merge by ACN |

## Related

- `Planning/tasks/0010-prd-asrs-contributing-factors-layer.md`
- `Planning/ASRS-nasa-contact-draft-2026-06-04.md`
- `CONCEPTS.md` → `ASRS aggregate profile`, `DBOL export cap`
- Compare: `docs/solutions/integration-issues/faa-brief-report-vs-search-prefill.md` (official source URL tiers)
