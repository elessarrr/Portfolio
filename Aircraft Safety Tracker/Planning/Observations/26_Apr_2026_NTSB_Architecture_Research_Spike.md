# 26 Apr 2026: NTSB Architecture Research Spike (PRD-0019)

## Scope

This note documents Task `1.1` from `tasks-0019-prd-source-link-attribution-remediation.md`:
research and documentation of NTSB-operated systems, what each system covers, and URL patterns.

## NTSB Systems Inventory

### 1) CAROL (Case Analysis and Reporting Online)

- Purpose: NTSB search portal for investigations and recommendations.
- Coverage (from CAROL landing copy): recommendations `1967-present`, aviation investigations `1962-present`, surface investigations `2010-present`.
- Coverage caveat (from NTSB field-descriptions/help page): investigations view includes records created in the system and is not a complete investigation corpus.
- URL patterns observed:
  - Root search UI: `https://carol.ntsb.gov/`
  - Investigation details page: `https://carol.ntsb.gov/investigations/detail/{mkey}`
  - Enhanced/search entry points are currently JavaScript app routes under the same host.

### 2) Legacy Aviation Accident Database (NTSB Aviation Accident Database & Synopses)

- Purpose: historical aviation accident/incident records and narratives.
- Coverage: civil aviation accidents from `1962+` (explicitly called out by NTSB).
- Important routing note on official page: for cases after 2008, users are directed to CAROL query.
- URL patterns observed:
  - Search page: `https://www.ntsb.gov/pages/AviationQuery.aspx`
  - Legacy dynamic endpoint family (referenced in public docs/resources): `https://www.ntsb.gov/_layouts/ntsb.aviation/index.aspx`

### 3) data.ntsb.gov endpoints (API/utility surfaces)

- Purpose: docket/report and data-access surfaces used by NTSB tools and integrations.
- URL patterns observed:
  - Docket search UI: `https://data.ntsb.gov/Docket/Forms/searchdocket`
  - Docket query form currently used by importer: `https://data.ntsb.gov/Docket/?NTSBNumber={ntsb_number}`
  - Repgen PDF endpoint currently in code: `https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/{ntsb_number}/pdf`
- Initial implication: `data.ntsb.gov` is an integration surface, not a single canonical investigation-detail site for all historical records.

### 4) Downloadable Aviation Data Products

- Purpose: bulk downloadable aviation datasets useful for mapping and backfill analysis.
- Coverage: NTSB publishes downloadable data sets for `1962-1981` and `1982-present`.
- URL pattern entry point:
  - `https://www.ntsb.gov/safety/data/pages/Data_Stats.aspx`

## Research Outcome for Task 1.1

- NTSB ecosystem is multi-system, with overlapping but not identical coverage windows.
- CAROL should not be assumed to be complete for all legacy records.
- URL remediation must be identifier-aware and likely year-aware, rather than defaulting every record to CAROL detail URLs.

## Task 1.2: `source_data` Inspection on Affected NTSB Records

### Method

- Queried local SQLite (`data/aircraft_safety.db`) `incident_source` rows where `source_name='NTSB'`.
- Inspected 25 recent rows and 24 randomized rows split across:
  - modern period (`event_date >= 2015`) and
  - legacy period (`event_date < 2009`).
- Compared these fields:
  - `source_record_id`
  - `source_data.cm_ntsbNum`
  - `source_data.cm_mkey`
  - `source_url`

### Empirical Findings

- `NTSB` row count: `82,664`.
- `source_data` populated on `82,664/82,664` rows.
- `source_data.cm_mkey` present on `82,664/82,664` rows.
- `source_data.cm_ntsbNum` present on `82,664/82,664` rows.
- `source_data.cm_ntsbNum == source_record_id` on `82,664/82,664` rows.
- `source_url` is CAROL detail URL on `82,664/82,664` rows.
- `source_url` exactly equals `https://carol.ntsb.gov/investigations/detail/{cm_mkey}` on `82,664/82,664` rows.

### Identifier Interpretation

- The human-readable investigation ID is `cm_ntsbNum` (e.g., `ERA23LA375`, `NYC08CA227`), which is what we store as `source_record_id`.
- The numeric `cm_mkey` is used universally (legacy + modern years) as a backend key and is currently treated as a CAROL detail route key.
- Based on sampled records spanning 1988-2025 and full-table equality checks above, stored MKeys appear to be **dataset/backend investigation keys** (legacy-continuity keys), **not a separate CAROL-only identifier namespace**.
- Practical implication for remediation: we should treat `cm_mkey` as an internal lookup key that may map to different NTSB delivery surfaces by era/type; we should not assume CAROL detail pages are authoritative for every `cm_mkey`.

## Sources

- `https://carol.ntsb.gov/`
- `https://www.ntsb.gov/investigations/Pages/field-descriptions.aspx`
- `https://www.ntsb.gov/pages/AviationQuery.aspx`
- `https://www.ntsb.gov/safety/data/pages/Data_Stats.aspx`
- `https://data.ntsb.gov/Docket/Forms/searchdocket`

## Task 1.3: Legacy URL Reverse-Engineering (Pre-2010)

### Method

- Manually validated public legacy NTSB investigation pages discoverable via NTSB search indexing.
- Tested both candidate legacy formats:
  - `https://www.ntsb.gov/Pages/brief.aspx?ev_id=<value>&key=0`
  - `https://www.ntsb.gov/Pages/brief.aspx?ev_id=<value>`
- Also tested alphanumeric accident number values (example: `NYC02LA081`) as `ev_id`.

### Working Legacy URLs (sample of 10)

- `https://www.ntsb.gov/Pages/brief.aspx?ev_id=42928&key=0`
- `https://www.ntsb.gov/Pages/brief.aspx?ev_id=81532&key=0`
- `https://www.ntsb.gov/Pages/brief.aspx?ev_id=9746&key=0`
- `https://www.ntsb.gov/Pages/brief.aspx?ev_id=23958&key=0`
- `https://www.ntsb.gov/Pages/brief.aspx?ev_id=18792&key=0`
- `https://www.ntsb.gov/Pages/brief.aspx?ev_id=46436&key=0`
- `https://www.ntsb.gov/Pages/brief.aspx?ev_id=34374&key=0`
- `https://www.ntsb.gov/Pages/brief.aspx?ev_id=122&key=0`
- `https://www.ntsb.gov/Pages/brief.aspx?ev_id=79308&key=0`
- `https://www.ntsb.gov/Pages/brief.aspx?ev_id=79476&key=0`

### Findings

- The legacy investigation detail route uses a **numeric** `ev_id` query parameter, not `cm_mkey` and not `cm_ntsbNum`.
- `key=0` consistently appears on working legacy links and should be treated as part of the canonical legacy pattern.
- Passing `cm_ntsbNum`-style identifiers (e.g., `NYC02LA081`) as `ev_id` did not resolve to a populated legacy case page.
- Practical implication: we cannot deterministically derive legacy URLs from currently stored identifiers alone; remediation needs an additional mapping source (`cm_ntsbNum`/`cm_mkey` -> legacy `ev_id`).

## Task 1.4: API/Bulk Mapping Availability

### Method

- Inspected NTSB public aviation query surfaces and page source:
  - `https://www.ntsb.gov/pages/AviationQuery.aspx`
  - `https://www.ntsb.gov/pages/AviationQueryV2.aspx`
- Reviewed official NTSB data download entry points:
  - `https://www.ntsb.gov/safety/data/pages/Data_Stats.aspx`
  - `https://app.ntsb.gov/avdata/`

### Findings

- **Public API mapping (`AccidentNumber` -> `ev_id`)**:
  - No documented/public endpoint was found that directly returns legacy `ev_id` given `cm_ntsbNum`/accident number.
  - Aviation query pages are ASP.NET form-driven; page-source inspection showed autocomplete web-service calls but no clear investigation-ID mapping API.
- **Bulk mapping source**:
  - NTSB does provide official downloadable aviation datasets via `app.ntsb.gov/avdata/`.
  - Available files include full snapshots (`avall.zip`, `PRE1982.zip`, `Pre2008.zip`) and recurring update drops (`up*.zip`), plus coding/data-definition documents.
  - These bulk products are the viable path for constructing an offline mapping table needed by remediation.

### Decision for Phase 2 Planning

- Treat **bulk download datasets** as the mapping source of truth for deriving legacy `ev_id` relationships at scale.
- Treat **public API mapping** as unavailable for this use case unless NTSB provides a private/undocumented endpoint through support.

## Task 1.5: Remediation Decision (Scope + URL Targets)

### Scope Count (from Task 1.2 baseline)

- Total NTSB `IncidentSource` rows in scope: `82,664`.
- Rows currently using one URL pattern (`https://carol.ntsb.gov/investigations/detail/{cm_mkey}`): `82,664/82,664`.

### URL Pattern Decision

- **Legacy-routed records (when mapping yields `ev_id`)**:
  - Target `source_url`: `https://www.ntsb.gov/Pages/brief.aspx?ev_id={ev_id}&key=0`
- **CAROL-routed records (when no legacy `ev_id` mapping is found and CAROL is authoritative)**:
  - Target `source_url`: `https://carol.ntsb.gov/investigations/detail/{cm_mkey}`

### Concrete Re-pointing Decision

- Re-pointing action is required for the NTSB population currently stored with a single default pattern: `82,664` rows must be evaluated and assigned to the correct route.
- Deterministic legacy re-pointing is **blocked** until the offline mapping table (`cm_ntsbNum`/`cm_mkey` -> `ev_id`) is built from the NTSB bulk datasets.
- Execution decision for Phase 2:
  - Build mapping table first (one-time data prep).
  - Run one-time remediation script (`--dry-run` then `--apply`) to rewrite `source_url` for mapped legacy rows.
  - Update ingestion to stop defaulting all new NTSB records to CAROL and instead apply the same routing rule.
