# PRD 0010 — ASRS Contributing Factors Layer

**Status:** Ready for review  
**Created:** 2026-06-04  
**Updated:** 2026-06-18  
**Author:** Bhavesh (Product) / AI (CTO assist)

**Acquisition decision (2026-06-18):** NASA staff extract (2026-06-04) unanswered — closed. **Primary source:** [elihoole/asrs-aviation-reports](https://huggingface.co/datasets/elihoole/asrs-aviation-reports) (~47.7k rows, DBOL-derived parquet/CSV). **Gap-fill only:** manual DBOL CSV for models missing from HF snapshot. No DBOL scraping.

---

## 1. Introduction / Overview

NASA's Aviation Safety Reporting System (ASRS) is a confidential, voluntary reporting programme that collects first-hand safety reports from pilots, controllers, and crew. Unlike the official accident records in our database (ASN, NTSB, FAA AIDS), ASRS captures *near-misses and systemic concerns* — events that never appear in official registries but reveal how crews actually experience flying a given aircraft type.

This PRD adds an **ASRS Contributing Factors panel** to each aircraft detail page. The panel is positioned **below the summary section and above the incident table** and shows:

- A coded breakdown of contributing factors (Human Factors, Equipment, ATC, Environment, Other) expressed as percentages
- The number of ASRS reports backing the data (`n = X`)
- An external link to the NASA ASRS DBOL search page

This is a **distinct product** from the incident table — it surfaces self-reported safety culture, not confirmed accident history. The two layers are complementary: official records tell you what regulators documented; ASRS tells you what crews experienced.

---

## 2. Goals

1. Give users a second, qualitatively different safety signal alongside official incident counts.
2. Cover all aircraft models in our DB that have matching ASRS records (via HF bulk import + heuristic make/model match).
3. Persist raw ASRS rows in a new DB table so aggregations can be changed without re-importing.
4. Provide a refresh path: re-run HF import when dataset updates; optional DBOL CSV gap-fill.
5. Be honest about data limitations: show `n =` counts, include a source disclaimer, and display gracefully when data is sparse.

---

## 3. User Stories

| # | As a… | I want to… | So that… |
|---|-------|-----------|---------|
| US-1 | Curious visitor | See a contributing-factors breakdown for the Boeing 737 | I can understand what crews say goes wrong, beyond just accident counts |
| US-2 | Researcher | Know how many ASRS reports back the percentages shown | I can judge the statistical weight of the data |
| US-3 | Any user | Click a link to view the raw anonymous reports on the NASA site | I can read actual crew narratives myself |
| US-4 | Any user | See the panel even when report counts are low | I know we looked, and I can judge credibility from `n =` |

---

## 4. Functional Requirements

### 4.1 Data Ingestion

**FR-1** — Create a new `AsrsReport` table in the SQLite DB with at minimum the following columns:

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `acn` | TEXT | ASRS Accession Number (unique per report) |
| `aircraft_make_model_raw` | TEXT | Raw ASRS make/model string |
| `primary_problem` | TEXT | `Assessments.1_Primary Problem` (HF) / DBOL equivalent |
| `contributing_factors` | TEXT | JSON array of raw factor strings |
| `phase_of_flight` | TEXT | |
| `report_year` | INTEGER | Parsed from date field when available |
| `synopsis` | TEXT | Analyst synopsis (anonymised) |
| `imported_at` | TEXT | ISO timestamp of import batch |
| `source` | TEXT | `huggingface` or `dbol_csv` |
| `aircraft_id` | INTEGER FK | FK → `Aircraft.id`, NULL if unmatched |

**FR-2** — Write `scripts/import_asrs.py` that:
- **Primary:** `--source huggingface` loads [elihoole/asrs-aviation-reports](https://huggingface.co/datasets/elihoole/asrs-aviation-reports) (requires `datasets`; see `requirements-ingest.txt`)
- **Gap-fill:** `--csv path` or `--csv-dir dir` for DBOL CSV exports
- Maps make/model to `Aircraft` via heuristic matcher + optional `data/config/asrs_make_model_to_aircraft.jsonl` overrides
- Is idempotent: skip rows whose `acn` already exists
- Supports `--dry-run` and `--apply`
- Logs summary: imported, duplicate, unmatched

**FR-3** — Optional `data/config/asrs_make_model_to_aircraft.jsonl` for overrides (same pattern as FAA mapping).

### 4.2 Aggregation

**FR-4** — `app/services/asrs.py` → `get_asrs_profile(aircraft_id: int) -> dict | None`:
- Returns `None` if `n = 0`
- Returns `n`, `contributing_factors` (% by bucket), `top_event_types` (top 3), `limited_data` (n < 5), `asrs_query_url`

**FR-5** — Normalise raw ASRS factor strings into display buckets: Human Factors, Aircraft Equipment, ATC Issue, Weather/Environment, Other.

### 4.3 Display

**FR-6** — ASRS Contributing Factors card on aircraft detail page (below summary, above incident table):
- Header: `n = X crew reports`
- Factor breakdown (horizontal bars)
- Link: **View source reports on NASA ASRS →** → `https://asrs.arc.nasa.gov/search/database.html`
- Disclaimer: *"ASRS reports are voluntary and confidential. Not linked to specific accidents."*
- HF snapshot note: *"Aggregated from public ASRS research dataset (~48k reports)."*

**FR-7** — Hide card when `n = 0`.

**FR-8** — If `n < 5`, show *"Limited data — interpret with caution."*

### 4.4 Data Acquisition

**FR-9** — Document workflow in `scripts/README_asrs_refresh.md`:

| Priority | Source | Command |
|----------|--------|---------|
| **Primary** | Hugging Face dataset | `pip install -r requirements-ingest.txt && python scripts/import_asrs.py --source huggingface --apply` |
| **Gap-fill** | DBOL CSV (per-model, ≤5k) | `python scripts/import_asrs.py --csv path/to/export.csv --apply` |

**v1 ship gate:** ≥10 catalog aircraft with `n > 0` after HF import (expect top Boeing/Airbus models to match).

**Not in scope:** DBOL Playwright bot, reverse-engineered ASP.NET postbacks, NASA staff extract.

---

## 5. Non-Goals (Out of Scope)

- No per-incident ASRS linking
- No LLM summarisation in v1
- No verbatim narrative display in v1
- No automated DBOL scraping
- No real-time ASRS queries
- No deep-linked ASRS URL per aircraft

---

## 6. Design Considerations

- Match existing summary card styling (white card, shadow, muted disclaimer)
- Simple CSS percentage bars — no chart library

---

## 7. Technical Considerations

- Alembic migration for `asrs_report` table
- Idempotency key: `acn`
- Aggregate at query time in v1
- `datasets` only in `requirements-ingest.txt` (not production Flask deps)
- HF dataset is a subset (~48k) of full ASRS — disclose in UI

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| Aircraft models with ASRS data | ≥ 10 |
| Panel on top-10 pages | Where HF coverage exists |
| `n =` accurate | Matches DB count |
| Tests green | Existing + ASRS unit tests |
| Import idempotent | Re-run produces same state |

---

## 9. Open Questions

| # | Question | Status |
|---|----------|--------|
| OQ-1 | HF column mapping | **Resolved** — elihoole schema documented in import script |
| OQ-2 | First batch scope | **Resolved** — full HF dataset in one import |
| OQ-3 | Factor normalisation | **Resolved** — bucket map in `app/services/asrs.py` |
| OQ-4 | v2 LLM + quotes | **Deferred** |
| OQ-5 | NASA staff extract | **Closed** |
| OQ-6 | Make/model match rate post-HF | **Resolved** — 53 aircraft with n>0; 17,226/47,723 rows matched (`data/logs/asrs_coverage_summary.json`) |
