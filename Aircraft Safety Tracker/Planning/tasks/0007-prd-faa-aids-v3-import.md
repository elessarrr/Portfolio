# Product Requirements Document: 0007 — FAA AIDS Enrichment (v3, ASN+NTSB-first)

**Project ID:** 0007  
**Created:** 2026-06-01  
**Author:** Product (with CTO)  
**Status:** Draft — ready for implementation  
**Branch policy:** Work on `v3-boeing-airbus-links`; keep `main` stable  
**Depends on:** PRD 0006.3 complete — **603** NTSB sources live on v3; 77 tests green  
**Follows pattern of:** PRD 0006.1 / 0006.2 / 0006.3 (NTSB enrichment pipeline)  
**Related files:**
- `app/ingestion/importers/ntsb_importer.py` — template for `FAAAIDSImporter`
- `app/ingestion/ntsb_mapping.py` — template for `FaaAidsMakeModelMapping`
- `app/ingestion/link_schema.py` — `assert_valid_source_url`, `is_catalog_url`
- `app/link_picker.py` — `SOURCE_PRIORITY` already includes `FAA_AIDS` at position 2
- `app/ingestion/importers/base.py` — `find_boeing_airbus_aircraft_id`, `resolve_boeing_airbus_aircraft_id`
- `Planning/spike-reports/0001-faa-aids-url-spike-report.md` — GO decision; URL pattern confirmed
- `Planning/branch-debrief-v2.md` §7 — FAA AIDS source intelligence
- `LEARNINGS.md` §28, §37, §38, §42, §45 — mapping gate, catalog bloat, dedupe alignment, variant remediation

---

## 1. Introduction / Overview

### Problem statement

v3 has a strong **ASN baseline** (6,126 incidents) and **NTSB enrichment** (603 additional incidents). FAA AIDS adds a third official US record:

| Gap | Detail |
|-----|--------|
| **Missing US incidents** | FAA AIDS covers all US-territory aviation events — accidents *and* incidents — many of which are not in ASN or NTSB. |
| **ASIAS URL confirmed** | Spike PRD 0001 (GO): `P12_AIDS_RPRT_NBR:{c5}` — **100% success on 500-row sample**; URL is deterministic, no per-row HTTP check needed at import. |
| **link_picker already wired** | `SOURCE_PRIORITY = ("NTSB", "FAA_AIDS", "FAA_SDR", "ASN")` — FAA AIDS slot exists; it just has zero rows. |
| **v2 code exists but not ported** | `url_builders/faa_aids.py`, `importers/faa_aids_importer.py`, `bulk/faa_aids_bulk.py` live in v2 branch but were never brought into v3. |

The v2 implementation revealed two key failure modes to avoid:
1. **Catalog bloat**: FAA AIDS uses highly fragmented `c23`/`c24` make/model strings (`7373H4`, `737322`, `B737`, `A-320`, etc.). Without a pre-import mapping file, `resolve_boeing_airbus_aircraft_id()` auto-creates hundreds of thin Aircraft pages.
2. **Import before URL** (v2 mistake): 157k rows were imported with `source_url=NULL` then backfilled. v3 rule: **URL at import time**, derived deterministically from `c5`. No backfill phase needed.

### Goal

Import FAA AIDS Boeing/Airbus records into v3, adding new incidents not already covered by ASN or NTSB, with **every row carrying a valid ASIAS URL at insert time** and **zero catalog bloat**.

---

## 2. Goals

1. **URL-first import:** Every imported FAA AIDS `IncidentSource` row must have a non-null, non-catalog `source_url` (`assert_valid_source_url` passes) at insert — no post-import backfill.
2. **Zero catalog bloat:** Bulk import must not create new `Aircraft` rows except where product explicitly approves via mapping file (same gate as NTSB).
3. **No ASN/NTSB duplication:** Score-based dedupe vs ASN incidents (±7 day window, ≥2 strong signals = covered); accept NTSB/FAA overlap without cross-source dedup (0 pairs in v2 dry-run).
4. **Mapping gate shipped first:** `data/config/faa_aids_make_model_to_aircraft.jsonl` reviewed and approved before any DB writes.
5. **Seamless UI:** FAA AIDS incidents render identically to ASN and NTSB rows in `incident_list.html` — same `Details ↗` button via `pick_primary_href`, no new template changes required.
6. **Audit trail:** Pre-import audit JSONL + post-import duplicate audit, matching the NTSB pipeline pattern.
7. **Tests green:** All existing 77 tests pass + new FAA AIDS importer tests.

---

## 3. User Stories

1. **As a** portfolio visitor browsing a Boeing 737-800 page,  
   **I want** to see US incident records that ASN or NTSB didn't capture,  
   **so that** the safety record feels more complete.

2. **As a** portfolio visitor clicking "Details ↗" on a FAA-sourced incident,  
   **I want** to land on the specific ASIAS record for that event,  
   **so that** I can verify the details on an official FAA page.

3. **As a** product owner,  
   **I want** a reviewable mapping from FAA make/model strings → catalog aircraft before any DB writes,  
   **so that** I control which aircraft pages receive FAA data and prevent catalog bloat.

4. **As a** developer,  
   **I want** the importer to fail closed on unmapped make/model strings,  
   **so that** we never silently auto-create duplicate or spurious aircraft pages.

---

## 4. Functional Requirements

### FR-1: Scope (Boeing/Airbus only)

1. **FR-1.1** Process only FAA AIDS records where `c23` (make) begins with `BOEING` or `AIRBUS` (case-insensitive). Use `is_boeing_or_airbus_make_model()` from `app/ingestion/importers/base.py`.
2. **FR-1.2** Skip all other manufacturers at import time; do not create `Incident` or `IncidentSource` rows.
3. **FR-1.3** `source_record_id` = `c5` (control number). This is the unique FAA AIDS identifier; it must be non-empty for any row to be imported.

### FR-2: Data acquisition (CSV from ZIP)

1. **FR-2.1** Source: FAA AIDS bulk ZIP from `https://www.faa.gov/data_research/accident_incident/`. Download and extract the latest ZIP; parse the main CSV file.
2. **FR-2.2** Guard against FAA returning HTML instead of CSV (known gotcha, LEARNINGS §16 / branch-debrief §7): add `_looks_like_csv()` check — skip import and error if response is HTML.
3. **FR-2.3** Export Boeing/Airbus rows to `data/raw/faa_aids_boeing_airbus.jsonl` (one JSON per record) for audit and import use. Skip `#` comment lines when reading this JSONL later (LEARNINGS §24 pattern).
4. **FR-2.4** Export script: `scripts/export_faa_aids_boeing_airbus.py` — reads the CSV, filters Boeing/Airbus, writes JSONL with raw field names preserved.
5. **FR-2.5** Raw field mapping (from v2 spike / bulk schema):

| CSV column | Stored as | Purpose |
|-----------|-----------|---------|
| `c5` | `source_record_id` | Unique ID; key for ASIAS URL |
| `c9` | `date` | Event date (MM/DD/YYYY) |
| `c23` | make component of `make_model` | Boeing/Airbus filter key |
| `c24` | model component of `make_model` | |
| `c203` | `registration` (in `source_data`) | Aircraft tail number |
| `c26` | `operator` | Airline/operator name |
| `c28` | `location` (city) | |
| `c29` | `location` (state) | |
| `c34` | `fatalities` | Total fatal injuries |
| `c44` | `description` | Event narrative |

6. **FR-2.6** Full raw row stored as `IncidentSource.source_data` (metadata only — no `links[]` blob per v3 rule; `assert_source_data_metadata_only` must pass).

### FR-3: URL builder (deterministic, URL at import time)

1. **FR-3.1** Create `app/ingestion/url_builders/faa_aids.py` (port from v2). Primary URL pattern (confirmed by spike PRD 0001):
   ```
   https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:{source_record_id}
   ```
   where `{source_record_id}` is URL-percent-encoded `c5`.
2. **FR-3.2** Function signature: `build_faa_aids_url(source_record_id: str) -> str`. Return `None` (not catalog fallback) when `source_record_id` is empty or None — never store the catalog landing page as `source_url`.
3. **FR-3.3** `assert_valid_source_url(url)` must pass for every URL stored; `is_catalog_url()` in `link_schema.py` already rejects ASIAS catalog pages (FR-3.3 cost = zero; guard already exists).
4. **FR-3.4** **No per-row HTTP viability check required** — unlike NTSB dockets, ASIAS URLs are deterministic and 100% reliable per spike. Do not add HTTP latency to import.
5. **FR-3.5** Store raw `source_record_id` (c5) in `IncidentSource.source_data` so URL can be reconstructed on any schema change without losing the original key.

### FR-4: Make/model catalog export (pre-mapping, product review gate)

1. **FR-4.1** Add `scripts/export_faa_aids_make_model_catalog.py`. Reads `data/raw/faa_aids_boeing_airbus.jsonl`, computes distinct `(c23 + " " + c24).strip()` strings, outputs `data/logs/faa_aids_make_model_catalog.jsonl`.
2. **FR-4.2** Each catalog row must include:
   - `faa_make_model` — verbatim joined string (e.g. `BOEING 7373H4`)
   - `incident_count` — rows in Boeing/Airbus export using this string
   - `char_length`
   - `manufacturer_guess` (`Boeing` | `Airbus` | `unknown`)
   - `sample_c5_ids` — ≤3 control numbers for manual cross-check
3. **FR-4.3** Sort descending by `incident_count` so high-volume strings appear first during product review.
4. **FR-4.4** **Product review gate:** CTO reviews catalog, assigns each string a `canonical_model_name` and `action` (`map_to_existing` | `create_approved` | `skip`), and approves `data/config/faa_aids_make_model_to_aircraft.jsonl` before any DB writes.

### FR-5: Mapping JSONL schema

1. **FR-5.1** `data/config/faa_aids_make_model_to_aircraft.jsonl` — same format as NTSB mapping, adapted for FAA field naming:
   ```jsonl
   {"faa_make_model": "BOEING 7373H4", "canonical_model_name": "Boeing 737-300", "action": "map_to_existing"}
   {"faa_make_model": "AIRBUS A320-211", "canonical_model_name": "Airbus A320", "action": "map_to_existing"}
   ```
2. **FR-5.2** Valid `action` values: `map_to_existing`, `create_approved`, `skip`. `skip` rows are silently discarded at import without error (out-of-scope aircraft like Stearman variants, military, etc.).
3. **FR-5.3** `create_approved` requires `manufacturer` field; canonical name must contain `Boeing` or `Airbus` (same guard as `_validate_boeing_airbus_page_name` in `ntsb_mapping.py`).
4. **FR-5.4** Build `app/ingestion/faa_aids_mapping.py` modelled exactly on `app/ingestion/ntsb_mapping.py` (`FaaAidsMakeModelMapping`, `load_faa_aids_make_model_mapping`, `bootstrap_create_approved_pages`). Reuse `_validate_boeing_airbus_page_name` (or extract to shared helper).
5. **FR-5.5** If `mapping=` is provided to `FAAAIDSImporter` and a string is not in the mapping, the row is **silently skipped** (logged, not errored). Unmapped strings accumulate in `importer.skipped_unmapped` list.

### FR-6: ASN deduplication (pre-import pass)

1. **FR-6.1** Before bulk import, run a dedupe pass: for each Boeing/Airbus FAA AIDS row, score against existing ASN `Incident` rows on the same `aircraft_id` within ±2 days. (Tighter than NTSB's ±7 day window — FAA AIDS uses event dates with good US-domestic precision; NTSB's wider window accommodated investigation-date ambiguity on foreign-led cases, which is not a concern here.)
2. **FR-6.2** Score signals (reuse `app/ingestion/dedupe/ntsb_asn.py` logic or extract shared module):
   - `date_close` — within 1 calendar day (strong)
   - `fatalities_close` — delta ≤ 1 after applying `fatalities_like_import()` null→0 coercion (LEARNINGS §38)
   - `location_fuzzy` — partial string match city/state (weak)
   - `operator_fuzzy` — partial string match (weak)
3. **FR-6.3** ASN-covered threshold: **≥ 2 strong signals** → mark `asn_covered`, skip import. Same as NTSB (FR-4.3 in PRD 0006.1).
4. **FR-6.4** Write dedupe output to `data/logs/faa_aids_dedupe_audit.jsonl` with fields: `c5`, `faa_make_model`, `dedupe_status` (`asn_covered` | `import`), `closest_asn_incident_id`, `score_detail`.
5. **FR-6.5** **Do not** attempt FAA↔NTSB cross-source dedup — v2 dry-run found **0 matching pairs**; accept overlap (LEARNINGS / branch-debrief §7).
6. **FR-6.6** Script: `scripts/faa_aids_dedupe_pass.py` — reads `data/raw/faa_aids_boeing_airbus.jsonl`, writes `data/logs/faa_aids_dedupe_audit.jsonl`.

### FR-7: FAAAIDSImporter (v3 port)

1. **FR-7.1** Create `app/ingestion/importers/faa_aids_importer.py`. Modelled on `ntsb_importer.py`:
   - Class `FAAAIDSImporter`, `source_name = "FAA_AIDS"`
   - Constructor: `FAAAIDSImporter(records=..., mapping=...)` — `mapping` required for bulk; accepts `FaaAidsMakeModelMapping` or path string/Path.
   - Methods: `run() -> int`, `upsert(raw_record) -> bool`, `parse(raw_record) -> Optional[dict]` (static), `_resolve_aircraft_id(faa_make_model)`.
2. **FR-7.2** `parse()` contract — returns dict with keys:
   ```
   source_record_id, date, operator, location, fatalities,
   description, make_model, source_url, source_data
   ```
   Return `None` if `c5` missing, date unparseable, or not Boeing/Airbus.
3. **FR-7.3** `source_url` = `build_faa_aids_url(c5)` — set at parse time, never None for a valid row. `assert_valid_source_url(source_url)` must pass before upsert writes.
4. **FR-7.4** `upsert()` idempotent: if `IncidentSource` row with `(source_name="FAA_AIDS", source_record_id=c5)` already exists, update `source_url` and `source_data`; do not create a duplicate `Incident`.
5. **FR-7.5** `_resolve_aircraft_id()` uses mapping when provided (fail-closed); falls back to `resolve_boeing_airbus_aircraft_id()` only when no mapping supplied (dev/test use only).
6. **FR-7.6** `IncidentSource.source_data` stores raw CSV fields as metadata. Must pass `assert_source_data_metadata_only()` — no `links[]` key.
7. **FR-7.7** `IncidentSource.source_data` must include `faa_aids_make_model` key (verbatim `c23 + c24`) — mirrors `ntsb_make_model` key in NTSB rows, enables future display if needed.

### FR-8: Bootstrap create_approved pages

1. **FR-8.1** Before bulk import, run `scripts/bootstrap_faa_aids_create_approved_pages.py` — creates empty `Aircraft` rows for all `create_approved` targets in the mapping file.
2. **FR-8.2** Bootstrap is idempotent: already-existing pages are skipped without error.
3. **FR-8.3** Dry-run mode: `--dry-run` reports would-create list without writing.
4. **FR-8.4** Reuse `bootstrap_create_approved_pages()` from `faa_aids_mapping.py` (modelled on `ntsb_mapping.py`).

### FR-9: Pilot import (30-row canary)

1. **FR-9.1** Clone v3 DB before pilot: `cp data/aircraft_safety_v3.db data/aircraft_safety_v3.db.pre-faa-aids-pilot`.
2. **FR-9.2** Run `scripts/faa_aids_pilot_import.py` — imports the first 30 `dedupe_status=import` rows from the dedupe audit JSONL against the cloned pilot DB.
3. **FR-9.3** Verify 30 rows:
   - Correct `aircraft_id` (matches expected catalog page)
   - `source_url` is non-null, non-catalog, passes `assert_valid_source_url`
   - Details link returns HTTP 200 (spot-check 5 URLs via `curl`)
   - No duplicate `Incident` rows (same date + aircraft)
4. **FR-9.4** Product review gate: CTO reviews pilot report before bulk import proceeds.

### FR-10: Bulk import

1. **FR-10.1** Backup real v3 DB before bulk: `cp data/aircraft_safety_v3.db data/aircraft_safety_v3.db.pre-faa-aids-bulk`.
2. **FR-10.2** Run `scripts/faa_aids_bulk_import.py`:
   - Input: `data/logs/faa_aids_dedupe_audit.jsonl` filtered to `dedupe_status=import`
   - Mapping: `data/config/faa_aids_make_model_to_aircraft.jsonl` (required — `--mapping`)
   - Output report: `data/logs/faa_aids_bulk_import_report.json`
3. **FR-10.3** Batch commits (every 1,000 rows). Single SQLite writer — do not run Flask dev server concurrently during import (LEARNINGS §19).
4. **FR-10.4** Log: rows_read, imported, skipped_unmapped, skipped_asn_covered, skipped_no_date, errors.
5. **FR-10.5** Idempotent re-run: second run on same data must produce 0 new rows (upsert path, not insert-only).
6. **FR-10.6** Recalculate `Aircraft.total_incidents`, `fatal_incidents`, `total_fatalities` for all touched aircraft pages after import (same as NTSB `recalc_aircraft_stats()`).

### FR-11: Post-import duplicate audit

1. **FR-11.1** Run `scripts/audit_post_faa_aids_import.py` after bulk import. Checks:
   - FAA AIDS incidents that have an ASN incident with ≥2 strong dedupe signals (same logic as NTSB post-import audit)
   - `IncidentSource` rows with `source_name="FAA_AIDS"` and `source_url` failing `assert_valid_source_url`
   - Near-duplicate `Aircraft` rows (same model_name variants differing only in casing/spacing)
2. **FR-11.2** Report to `data/logs/faa_aids_post_import_audit.json`.
3. **FR-11.3** `--remediate` flag: delete confirmed FAA AIDS duplicates (same pattern as `audit_post_ntsb_import.py`).
4. **FR-11.4** Audit must pass (0 critical issues) before marking this PRD complete.

### FR-12: Test suite

1. **FR-12.1** `tests/test_faa_aids_importer.py`:
   - `parse()` returns correct fields for valid Boeing row
   - `parse()` returns `None` for non-Boeing/Airbus row
   - `parse()` returns `None` when `c5` missing
   - `upsert()` with mapping gate: mapped string → insert; unmapped → skip
   - `upsert()` idempotent re-run: same row twice → 1 `IncidentSource`
   - `source_url` is non-null, non-catalog for any successfully parsed row
2. **FR-12.2** `tests/test_faa_aids_url_builder.py`:
   - `build_faa_aids_url("12345")` → correct ASIAS URL
   - `build_faa_aids_url(None)` → `None`
   - `build_faa_aids_url("")` → `None`
   - `is_catalog_url()` rejects catalog pattern, passes per-record URL
3. **FR-12.3** `tests/test_faa_aids_mapping.py`:
   - Load valid JSONL → correct mapping entries
   - `action=skip` rows → `skipped_unmapped` at import
   - `create_approved` → bootstrap creates `Aircraft`
   - Empty JSONL → `ValueError`
4. **FR-12.4** `PYTHONPATH=. pytest -q` must pass with all existing tests still green.

### FR-13: link_picker and UI (no template changes required)

1. **FR-13.1** `pick_primary_href()` in `app/link_picker.py` already handles `FAA_AIDS` at position 2 in `SOURCE_PRIORITY` — no changes needed.
2. **FR-13.2** `incident_list.html` already renders `Details ↗` via `pick_primary_href` — no template changes needed.
3. **FR-13.3** `display_make_model()` currently checks NTSB source only. Update to also return `faa_aids_make_model` from `source_data` for FAA AIDS rows (same pattern, same template cell).
4. **FR-13.4** FAA AIDS incidents share the same `Make/Model` column as NTSB — display the exact `c23 + c24` string from `source_data.faa_aids_make_model`.

---

## 5. Non-Goals (Out of Scope)

1. **FAA↔NTSB deduplication**: v2 dry-run found 0 exact pairs; cross-source merge not attempted (LEARNINGS / branch-debrief §7). Accept overlap; both sources add independent value.
2. **FAA SDR importer**: Deferred until FAA AIDS is stable. SDR has a broken fetch endpoint (HTML returned instead of CSV); effort cost uncertain (branch-debrief §7).
3. **Live ASIAS URL viability checks per row**: URL pattern is deterministic and 100% reliable per spike. No HTTP probes at import time.
4. **Family rollup** (query-time aggregation across variant pages): Separate PRD 0008 / post-FAA work. FAA AIDS will land on whatever pages the mapping file assigns.
5. **Operator/airline search**: Not part of this PRD.
6. **Merging v3 → `main`** or redeploying the portfolio: Separate product decision.
7. **Historical FAA AIDS archive sweep**: Only the latest ZIP download. No multi-vintage historical trawl.
8. **FAA SDR `source_url` backfill**: Out of scope.
9. **100% coverage**: Some FAA AIDS rows legitimately lack a `c5` control number or date — they are skipped; not a blocker.

---

## 6. Design Considerations

### UI (zero new template work)

The `incident_list.html` already handles the full multi-source case via `pick_primary_href`. FAA AIDS rows will render as normal incidents with a `Details ↗` button pointing to the ASIAS record.

| State | Display (existing) |
|-------|--------------------|
| FAA AIDS row with `source_url` | **"Details ↗"** → ASIAS per-record URL |
| ASN row | **"Details ↗"** → ASN wikibase URL (unchanged) |
| NTSB row | **"Details ↗"** → NTSB docket URL (unchanged) |
| No resolvable URL | No button rendered |

### Make/Model column

`display_make_model()` updated to also return the FAA AIDS `faa_aids_make_model` from `source_data` — exact string like `BOEING 7373H4` or `AIRBUS A320-211`. Same table cell, same template logic.

---

## 7. Technical Considerations

### New files to create

| File | Purpose |
|------|---------|
| `app/ingestion/url_builders/faa_aids.py` | `build_faa_aids_url(source_record_id)` |
| `app/ingestion/importers/faa_aids_importer.py` | `FAAAIDSImporter` (port + harden from v2) |
| `app/ingestion/faa_aids_mapping.py` | `FaaAidsMakeModelMapping`, `load_faa_aids_make_model_mapping`, `bootstrap_create_approved_pages` |
| `scripts/export_faa_aids_boeing_airbus.py` | CSV → JSONL export for Boeing/Airbus rows |
| `scripts/export_faa_aids_make_model_catalog.py` | Distinct make_model catalog for product review |
| `scripts/faa_aids_dedupe_pass.py` | ASN dedupe scoring; writes `faa_aids_dedupe_audit.jsonl` |
| `scripts/bootstrap_faa_aids_create_approved_pages.py` | Idempotent Aircraft page creation |
| `scripts/faa_aids_pilot_import.py` | 30-row canary against cloned DB |
| `scripts/faa_aids_bulk_import.py` | Full Boeing/Airbus import with mapping gate |
| `scripts/audit_post_faa_aids_import.py` | Post-import duplicate + URL audit |
| `tests/test_faa_aids_importer.py` | Importer unit tests |
| `tests/test_faa_aids_url_builder.py` | URL builder unit tests |
| `tests/test_faa_aids_mapping.py` | Mapping JSONL load + resolve tests |

### Files to modify

| File | Change |
|------|--------|
| `app/link_picker.py` | `display_make_model()` — add FAA_AIDS `source_data.faa_aids_make_model` branch |
| `data/config/` | Add `faa_aids_make_model_to_aircraft.jsonl` after product review |

### Files **not** to touch

- `app/models.py` — schema already supports `IncidentSource` with `source_name="FAA_AIDS"`
- `app/ingestion/link_schema.py` — `is_catalog_url` already rejects ASIAS catalog pattern
- `app/link_picker.py` — `SOURCE_PRIORITY` already correct (only `display_make_model` needs update)
- `app/templates/components/incident_list.html` — no template changes needed

### Operational constraints

- **Single SQLite writer**: stop Flask dev server during bulk import (LEARNINGS §19).
- **Rate limits (export only)**: ZIP download is one HTTP request; no per-row HTTP needed.
- **DB backup mandatory** before pilot and bulk writes (mirror NTSB discipline).
- **Run from `Aircraft Safety Tracker/`** directory, not `Portfolio/` root (LEARNINGS §4).
- **Use conda/venv interpreter** (`python`), not bare `python3` (LEARNINGS §31).

### Key identifiers / field mapping

| FAA field | v3 meaning |
|-----------|-----------|
| `c5` | `source_record_id` + ASIAS URL key |
| `c9` | `date` (parse `MM/DD/YYYY`) |
| `c23` | Make component (Boeing/Airbus filter) |
| `c24` | Model component |
| `c23 + c24` | `faa_make_model` string for mapping file |
| `c26` | `operator` |
| `c28` + `c29` | `location` (city, state) |
| `c34` | `fatalities` (coerce null → 0 at import, per LEARNINGS §38) |
| `c44` | `description` |
| `c203` | `registration` (in `source_data`) |

### Hard-won lessons from NTSB (apply from day one)

| Lesson | Applied where |
|--------|--------------|
| URL at import time, never backfill | `parse()` derives `source_url` from `c5` before `upsert` |
| Mapping gate fail-closed | `_resolve_aircraft_id()` returns None on unmapped string |
| `fatalities_like_import()` — null → 0 | Dedupe pass + importer |
| `assert_source_data_metadata_only()` | `upsert()` before every write |
| `UNIQUE (source_name, source_record_id)` | Already on `IncidentSource`; enforce at import |
| Backup before any write | Pilot + bulk scripts |
| Recalculate Aircraft stats after import | `faa_aids_bulk_import.py` |
| Post-import audit as safety net | `scripts/audit_post_faa_aids_import.py` |
| Skip `#` comment lines in JSONL loops | All JSONL-reading scripts |
| Bootstrap `create_approved` pages before import | `bootstrap_faa_aids_create_approved_pages.py` |

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| New FAA AIDS `IncidentSource` rows on v3 | > 0 Boeing/Airbus rows with `source_url` |
| `source_url` coverage | **100%** of imported rows have non-null, non-catalog `source_url` |
| Catalog bloat | **0** new `Aircraft` rows created outside approved mapping |
| ASN duplicate rate post-import | **< 1%** of imported FAA rows flagged as ASN-covered by post-import audit |
| Existing tests | **All 77** (+ new FAA tests) green after import |
| Details links sampled (manual QA) | **≥ 95%** of spot-checked ASIAS URLs return HTTP 200 with event-specific content |

---

## 9. Open Questions

1. **Expected Boeing/Airbus subset size**: The v2 DB had ~157k FAA AIDS rows total. After filtering to Boeing/Airbus only and deduping against ASN, what is the realistic import count on v3? (Estimate: several thousand — to confirm after catalog export.)
2. **Fatality dedup threshold**: Should `fatalities_close` use the same `fatalities_like_import()` null→0 coercion as NTSB? (Recommended: yes, for consistency — but confirm.)
3. **`skip` action in mapping**: Should skipped strings be explicitly listed in the mapping file (opt-in skip), or should any unmapped string be silently skipped? (Recommended: silent skip for unmapped, explicit `skip` only for known out-of-scope strings like Stearman variants shared with the NTSB catalog.)
4. **Operator alias handling in dedupe**: FAA AIDS operator strings (e.g. `FEDEX EXPRESS`) may differ from ASN (`FedEx`). Should the dedupe fuzzy score use the same partial-match approach as NTSB, or normalise to uppercase first?
5. **CSV encoding**: FAA AIDS ZIP may use Latin-1 encoding for older records. Confirm encoding handling in `export_faa_aids_boeing_airbus.py` (use `errors='replace'` or detect).

---

## 10. Execution Order (task phases)

| Phase | Tasks | Gate |
|-------|-------|------|
| **A — Acquisition** | FR-2: Export script, download ZIP, write `faa_aids_boeing_airbus.jsonl` | JSONL on disk |
| **B — Catalog** | FR-4: `export_faa_aids_make_model_catalog.py`, write catalog JSONL | Product reviews catalog |
| **C — Mapping** | FR-5: Build `faa_aids_make_model_to_aircraft.jsonl`, `faa_aids_mapping.py` | **Product sign-off** |
| **D — Dedupe** | FR-6: `faa_aids_dedupe_pass.py`, write `faa_aids_dedupe_audit.jsonl` | Counts reviewed |
| **E — Builder + Importer** | FR-3 + FR-7: `faa_aids.py`, `faa_aids_importer.py`, unit tests (FR-12) | All tests green |
| **F — Bootstrap** | FR-8: `bootstrap_faa_aids_create_approved_pages.py`, dry-run → live | Pages confirmed |
| **G — Pilot** | FR-9: `faa_aids_pilot_import.py` (30 rows, cloned DB) | **Product sign-off** |
| **H — Bulk** | FR-10: `faa_aids_bulk_import.py` on real v3 DB | Import report reviewed |
| **I — Audit** | FR-11: `audit_post_faa_aids_import.py` | 0 critical issues |
| **J — UI verify** | FR-13: manual smoke test on `:5003`; verify Details links + Make/Model column | QA pass |

*Phases A–E can partially overlap. Phases F–J must be sequential. Do not start Phase G until Phase C product sign-off is received.*

---

*Prior source PRDs: `0005.1` (ASN baseline), `0006.1–0006.3` (NTSB enrichment). Next: PRD 0008 — Family Rollup (query-time aggregation across variant pages).*
