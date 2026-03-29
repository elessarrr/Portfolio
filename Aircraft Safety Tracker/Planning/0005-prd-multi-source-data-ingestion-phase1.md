# PRD 0005: Multi-Source Aviation Safety Data Ingestion (Phase 1 - US Public Sources)

**Status:** Draft\
**Author:** Product Team\
**Date:** 2026-03-29\
**Version:** 1.0\
**Related PRDs:** 0003 (Aircraft Safety Lookup v2.0)

***

## 1. Introduction/Overview

The Aircraft Safety Lookup Tool currently relies exclusively on Aviation Safety Network (ASN) data scraped from their public website. While ASN provides excellent global airliner coverage, it lacks the depth, structured causal analysis, incident-level granularity, and mechanical defect tracking that aviation safety regulators require for comprehensive trend analysis.

This PRD specifies the integration of three authoritative US public data sources—**NTSB Aviation Database, FAA Accident/Incident Data System (AIDS), and FAA Service Difficulty Reports (SDR)**—to transform the tool from a single-source accident lookup into a multi-source aviation safety intelligence platform.

**Problem Statement:** Regulators like DASA (military equivalent of CASA) need to cross-reference accident investigations (NTSB) with sub-accident incidents (FAA AIDS) and mechanical defect trends (FAA SDR) to identify systemic safety issues before they escalate to accidents. Currently, this requires manually querying 3+ separate databases and reconciling overlapping records.

**Goal:** Enable users to search once and see a unified view of all available safety data—accidents, incidents, and mechanical reports—for any aircraft type, with clear source attribution and automatic duplicate detection.

***

## 2. Goals

1. **Expand data coverage** from \~23,000 ASN records to **150,000+ records** spanning accidents (NTSB), incidents (FAA AIDS), and mechanical defects (FAA SDR) over the past 40 years (1985-2025)
2. **Provide authoritative US data** with structured probable cause, findings, and JASC-coded mechanical failures that ASN cannot offer
3. **Enable cross-source analysis** by automatically linking the same event reported in multiple databases (e.g., an NTSB accident that also appears in FAA AIDS)
4. **Maintain data provenance** so users always know which organization provided each piece of information and can assess source authority accordingly
5. **Achieve 95%+ deduplication accuracy** to prevent users from seeing the same accident 3 times as separate records
6. **Build extensible architecture** that supports adding CADORS, TSB Canada, NASA ASRS, and international sources in Phase 2 without major refactoring

***

## 3. User Stories

**As a** aviation safety regulator,\
**I want to** search for "Boeing 737 MAX" and see all NTSB accidents, FAA incidents, AND mechanical defect reports in one place,\
**So that** I can identify patterns across accident investigations, operational incidents, and maintenance issues without querying 3 separate databases.

**As a** safety analyst,\
**I want to** filter incidents by aircraft system (hydraulics, electrical, flight controls) using JASC codes from FAA SDR data,\
**So that** I can track mechanical failure trends over time and predict which systems pose the highest risk.

**As a** airline fleet manager,\
**I want to** see the NTSB probable cause for an accident alongside the FAA AIDS incident report and related SDR mechanical defect reports,\
**So that** I understand the complete causal chain from initial defect through incident to final accident.

**As a** data quality manager,\
**I want to** see clear source badges ("NTSB - Authoritative", "FAA AIDS - Incident-level", "FAA SDR - Mechanical") on each record,\
**So that** I can assess the reliability and scope of the information presented.

**As a** system administrator,\
**I want to** the data import process to log errors and continue processing other sources when one source fails,\
**So that** a temporary NTSB API outage doesn't prevent users from accessing FAA AIDS and SDR data.

***

## 4. Functional Requirements

### 4.1 Data Source Integration

**FR-4.1.1:** The system MUST integrate data from three US public sources:

- NTSB Aviation Database (API + bulk downloads)
- FAA Accident/Incident Data System (AIDS) via ASIAS portal
- FAA Service Difficulty Reports (SDR) annual CSV downloads

**FR-4.1.2:** The system MUST import 40 years of historical data (1985-01-01 to 2025-12-31) from each source during initial setup.

**FR-4.1.3:** The system MUST support hybrid data refresh: bulk import for historical data, then incremental updates on a configurable schedule (daily/weekly/monthly per source).

**FR-4.1.4:** The system MUST track the last successful import timestamp per source and display "Data freshness: Last updated YYYY-MM-DD" on the UI.

**FR-4.1.5:** The system MUST continue processing remaining sources if one source fails, logging errors for manual review.

### 4.2 Data Schema & Storage

**FR-4.2.1:** The system MUST use the `IncidentSource` linking table architecture from PRD 0003 v2.0:

```sql
IncidentSource:
  - id (primary key)
  - incident_id (foreign key → Incident)
  - source_name (enum: 'ASN', 'NTSB', 'FAA_AIDS', 'FAA_SDR')
  - source_record_id (external ID from source system)
  - source_url (link to original record)
  - source_data (JSON blob for source-specific fields)
  - last_updated (timestamp)
  - confidence_level (enum: 'Authoritative', 'Preliminary', 'Unverified')
```

**FR-4.2.2:** The system MUST store the following structured fields from NTSB data:

- NTSB investigation number (primary key)
- Event date, location (lat/lon), city, state, country
- Aircraft make, model, registration, serial number
- Operator name, operator type (Part 121, Part 135, Part 91, etc.)
- Phase of flight (takeoff, cruise, landing, etc.)
- Injury counts (fatal, serious, minor, uninjured)
- Aircraft damage level (destroyed, substantial, minor, none)
- **Probable cause** (structured text field)
- **Findings** (structured array)
- Investigation status (preliminary, final)
- Link to full PDF report

**FR-4.2.3:** The system MUST store the following structured fields from FAA AIDS data:

- AIDS report number (primary key)
- Event date, location, city, state
- Aircraft make, model, registration
- Operator name
- Event type (incident vs accident)
- Phase of flight
- Findings (investigator observations)
- Narrative summary

**FR-4.2.4:** The system MUST store the following structured fields from FAA SDR data:

- SDR report number (primary key)
- Report date, aircraft registration
- Aircraft make, model, serial number
- Engine make, model (if applicable)
- **JASC code** (system/component code, e.g., "29-51-00" for Hydraulic Power—Engine Driven Pump)
- Part name, manufacturer part number
- Part condition (failed, malfunctioning, serviceable, etc.)
- Defect description (narrative)
- Service information reference

**FR-4.2.5:** The system MUST normalize JASC codes from FAA SDR data to the SystemTag taxonomy used in PRD 0003:

- Build a JASC → SystemTag mapping table (e.g., JASC 29-XX-XX → "Hydraulics")
- Apply mapping during SDR import to auto-tag incidents with system categories
- Support multiple system tags per incident (e.g., JASC "29-51" hydraulics + "24-XX" electrical if multiple systems involved)

### 4.3 Deduplication & Cross-Referencing

**FR-4.3.1:** The system MUST automatically detect duplicate records using composite matching rules:

**Exact match criteria:**

- Aircraft registration (N-number) + event date (same day) → Probable duplicate
- NTSB investigation number present in FAA AIDS "related investigations" field → Confirmed duplicate

**Fuzzy match criteria:**

- Aircraft make/model + location (within 50km) + date (±1 day) → Possible duplicate
- Operator name (normalized) + flight number + date → Probable duplicate

**FR-4.3.2:** The system MUST flag duplicates with confidence levels:

- **High confidence** (exact match): Auto-merge into single canonical record
- **Medium confidence** (fuzzy match): Flag for manual review
- **Low confidence** (weak signals): Keep separate but display "Possibly related" link

**FR-4.3.3:** When duplicates are detected, the system MUST:

- Designate NTSB as the canonical source (authoritative)
- Attach FAA AIDS and FAA SDR as linked sources
- Display "Also reported by: FAA AIDS, FAA SDR" with clickable badges
- Preserve all source-specific fields in `IncidentSource.source_data` JSON

**FR-4.3.4:** The system MUST track deduplication accuracy:

- Log all auto-merge decisions for audit
- Provide admin interface to review and override merge decisions
- Report monthly metric: "95% of duplicates correctly identified"

### 4.4 User Interface Enhancements

**FR-4.4.1:** The system MUST display source badges on each incident record:

- "NTSB" badge (blue) with tooltip "Authoritative - Formal investigation with probable cause"
- "FAA AIDS" badge (yellow) with tooltip "Incident-level - FAA investigator findings"
- "FAA SDR" badge (orange) with tooltip "Mechanical defect report - JASC coded"
- "ASN" badge (green) with tooltip "Global accident database - Curated"

**FR-4.4.2:** The system MUST add a "Data Sources" filter to the sidebar:

- Checkboxes: ☑ NTSB, ☑ FAA AIDS, ☑ FAA SDR, ☑ ASN
- Default: All checked (show all sources)
- User can uncheck to filter, e.g., "Show only NTSB authoritative investigations"

**FR-4.4.3:** When displaying incident details, the system MUST show:

- **Primary source** section at top (e.g., NTSB data with probable cause)
- **Additional sources** accordion below (e.g., "FAA AIDS Report" expandable section)
- **Mechanical history** section if FAA SDR reports exist for same aircraft registration

**FR-4.4.4:** The system MUST display "Last updated: YYYY-MM-DD" timestamp per source in the footer, e.g.:

```
Data sources: NTSB (updated 2026-03-28), FAA AIDS (updated 2026-03-25), FAA SDR (updated 2026-03-20), ASN (updated 2026-03-29)
```

### 4.5 Data Import Pipeline

**FR-4.5.1:** The system MUST implement separate importer classes for each source:

- `NTSBImporter` - Queries NTSB API + processes bulk ZIP downloads
- `FAAAIDSImporter` - Downloads tab-delimited text files from ASIAS portal
- `FAASDRImporter` - Downloads annual CSV files from FAA website
- Each importer extends a base `DataSourceImporter` class with common methods

**FR-4.5.2:** The system MUST support command-line execution:

```bash
flask import-data ntsb --start-date 1985-01-01 --end-date 2025-12-31
flask import-data faa-aids --year 2024
flask import-data faa-sdr --year 2024
flask import-data all --incremental  # Only new records since last import
```

**FR-4.5.3:** The system MUST log import progress and errors:

- Create `data/logs/import_YYYYMMDD_HHMMSS.log` per import run
- Log: Records processed, duplicates detected, errors encountered, time elapsed
- Example: "NTSB import: 23,456 records processed, 1,234 duplicates merged, 12 errors, 45min elapsed"

**FR-4.5.4:** The system MUST handle API rate limiting:

- NTSB API: Implement exponential backoff if 429 errors received
- Batch requests: Max 100 records per API call
- Sleep 1 second between bulk download requests

**FR-4.5.5:** The system MUST validate imported data before storage:

- Required fields check (date, aircraft registration, location)
- Date range validation (reject records outside 1985-2025)
- JASC code validation (must match known JASC taxonomy)
- Log validation errors without crashing import

### 4.6 JASC Code Mapping

**FR-4.6.1:** The system MUST create a `JASCMapping` table:

```sql
JASCMapping:
  - id (primary key)
  - jasc_code (string, e.g., "29-51-00")
  - jasc_description (string, e.g., "Hydraulic Power—Engine Driven Pump")
  - system_tag_id (foreign key → SystemTag)
  - confidence (enum: 'High', 'Medium', 'Low')
```

**FR-4.6.2:** The system MUST seed the mapping table with common JASC → System mappings:

- JASC 21-XX-XX → "Air Conditioning & Pressurization"
- JASC 24-XX-XX → "Electrical Power"
- JASC 27-XX-XX → "Flight Controls"
- JASC 29-XX-XX → "Hydraulics"
- JASC 32-XX-XX → "Landing Gear"
- JASC 71-XX-XX → "Powerplant"
- JASC 79-XX-XX → "Engine Oil"
- (Full mapping table documented in `docs/JASC_MAPPING.md`)

**FR-4.6.3:** The system MUST apply JASC mapping during FAA SDR import:

- Parse JASC code from SDR record
- Look up corresponding SystemTag in JASCMapping table
- Create SystemTag association via `incident_system_tags` linking table
- If JASC code not found in mapping, log warning and tag as "Unknown System"

**FR-4.6.4:** The system MUST support manual JASC mapping overrides:

- Admin interface to view unmapped JASC codes
- Admin can assign SystemTag to unmapped JASC code
- New mapping saved to JASCMapping table for future imports

***

## 5. Non-Goals (Out of Scope for Phase 1)

The following are explicitly **excluded** from this PRD and deferred to future phases:

**Phase 2 scope (PRD 0005):**

- NASA ASRS voluntary report integration
- Transport Canada CADORS/TSB dataset integration
- FAA Wildlife Strike Database integration
- Aviation Safety Network (ASN) paid API upgrade
- Real-time data streaming / WebSocket updates
- User engagement metrics ("Regulator users query 3+ sources per search")

**Phase 3 scope (PRD 0006):**

- UK AAIB investigation report scraping
- EASA Safety Recommendations Information System (SRIS) integration
- BEA France investigation reports
- ATSB Australia database integration
- NLP-powered causal factor extraction from narrative reports

**Future versions (v3.0+ backlog):**

- Comprehensive retry logic with exponential backoff (FR-4.5.4 implements basic version only)
- Advanced error handling with alerting and circuit breakers
- Real-time data freshness monitoring with SLA alerting
- Automated data quality scoring and anomaly detection
- Cross-source trend analysis dashboards
- ADS-B flight trajectory integration
- ICAO ADREP taxonomy normalization
- Safety recommendations tracking across NTSB/EASA/TAIC

***

## 6. Design Considerations

### 6.1 Database Schema Extensions

Extend the existing v2.0 schema from PRD 0003 with:

**New tables:**

- `JASCMapping` (JASC code → SystemTag mappings)
- `ImportLog` (tracks import runs, timestamps, record counts, errors)

**Modified tables:**

- `IncidentSource.source_name` enum: Add 'NTSB', 'FAA\_AIDS', 'FAA\_SDR' values
- `IncidentSource.confidence_level` enum: Add 'Authoritative', 'Preliminary', 'Unverified' values
- `SystemTag`: Ensure JASC-derived tags are clearly marked (e.g., `tag_source` field: 'JASC', 'ASN', 'AI', 'Manual')

### 6.2 UI/UX Mockups

**Incident detail page:**

```
┌─────────────────────────────────────────────────────────────┐
│ Boeing 737-800, N12345, 2024-03-15                          │
│ [NTSB] [FAA AIDS] [FAA SDR]  ← Source badges                │
├─────────────────────────────────────────────────────────────┤
│ PRIMARY SOURCE: NTSB Investigation                          │
│ Probable Cause: Hydraulic system failure during approach... │
│ Findings: (1) Inadequate maintenance, (2) Component fatigue │
│ [View Full NTSB Report PDF]                                 │
├─────────────────────────────────────────────────────────────┤
│ ▼ ADDITIONAL SOURCES                                        │
│   ▶ FAA AIDS Incident Report (Click to expand)             │
│   ▶ FAA SDR Mechanical Defect History (3 reports)          │
└─────────────────────────────────────────────────────────────┘
```

**Sidebar filters:**

```
┌──────────────────────┐
│ DATA SOURCES         │
│ ☑ NTSB (23,456)      │
│ ☑ FAA AIDS (45,678)  │
│ ☑ FAA SDR (89,012)   │
│ ☑ ASN (23,000)       │
│                      │
│ AIRCRAFT SYSTEM      │
│ ☑ Hydraulics (1,234) │
│ ☑ Electrical (567)   │
│ ☐ Flight Controls    │
└──────────────────────┘
```

### 6.3 Error Handling & Logging

**Import error categories:**

1. **Network errors** - API timeout, DNS failure, connection refused
   - Action: Log error, continue with next source
   - Example: "NTSB API timeout after 30s - skipping batch, will retry on next run"
2. **Data validation errors** - Missing required fields, invalid date format, unknown JASC code
   - Action: Log warning with record ID, skip record, continue processing
   - Example: "FAA SDR record 2024-12345 missing aircraft registration - skipped"
3. **Duplicate detection errors** - Conflicting merge decisions, circular references
   - Action: Log error with record IDs, flag for manual review, do not auto-merge
   - Example: "NTSB-2024-001 and FAA-AIDS-2024-567 possible duplicate (80% confidence) - flagged for review"

**Log format (JSON structured logging):**

```json
{
  "timestamp": "2026-03-29T14:30:00Z",
  "level": "ERROR",
  "source": "NTSBImporter",
  "message": "API rate limit exceeded - 429 response",
  "context": {
    "url": "https://developer.ntsb.gov/api/...",
    "batch": 45,
    "retry_in": "60s"
  }
}
```

***

## 7. Technical Considerations

### 7.1 Data Source APIs & Access Methods

**NTSB Aviation Database:**

- **API endpoint:** `https://developer.ntsb.gov/api/aviation/v1/`
- **Bulk downloads:** `https://data.ntsb.gov/avdata/avall.zip` (1982-present), `PRE1982.zip` (1962-1981)
- **Authentication:** Free registration at `developer.ntsb.gov`, API key in request headers
- **Rate limits:** Unknown - implement conservative 1 req/sec + exponential backoff on 429 errors
- **Data format:** JSON (API), ZIP of tab-delimited text files (bulk)

**FAA AIDS:**

- **Access method:** ASIAS portal downloads at `https://www.asias.faa.gov/apex/f?p=100:189`
- **Data format:** Tab-delimited text ZIP files, monthly refresh
- **Authentication:** None required for download
- **Update frequency:** Monthly (new data added \~15th of each month)

**FAA SDR:**

- **Access method:** Direct CSV downloads at `https://external-api.faa.gov/sdrs/retrieve/SDR-{YEAR}.csv`
- **Data format:** CSV, one file per year (1995-2026)
- **Authentication:** None required
- **Update frequency:** Annual (new year's file available in January)

### 7.2 Dependencies

**Python libraries:**

- `requests` - HTTP client for API calls and file downloads
- `pandas` - CSV/TSV parsing and data transformation
- `sqlalchemy` - ORM for database operations
- `zipfile` - Extract NTSB bulk downloads
- `python-dotenv` - Environment variable management for API keys

**Infrastructure:**

- Database: PostgreSQL or SQLite (existing v2.0 architecture)
- Storage: \~5GB estimated for 40 years of 3-source data (compressed)
- Compute: Batch import runs can take 2-4 hours for full 40-year load

### 7.3 Data Volume Estimates

**Historical import (1985-2025, 40 years):**

- NTSB: \~80,000 accident/incident records (avg 2,000/year)
- FAA AIDS: \~120,000 incident records (avg 3,000/year since 1978, subset from 1985)
- FAA SDR: \~1,600,000 defect reports (avg 40,000/year)
- **Total: \~1,800,000 records** (vs \~23,000 in ASN-only v1.0)

**Incremental updates (monthly):**

- NTSB: \~100 new records/month (preliminary + final reports)
- FAA AIDS: \~250 new records/month
- FAA SDR: \~3,300 new records/month
- **Total: \~3,650 new records/month**

**Database storage:**

- Incident table: \~500 bytes/row × 1.8M rows = \~900 MB
- IncidentSource linking table: \~200 bytes/row × 2.5M rows (multiple sources per incident) = \~500 MB
- SystemTag associations: \~100 bytes/row × 1M rows = \~100 MB
- JSON source\_data blobs: \~2 KB/row × 2.5M rows = \~5 GB
- **Total estimated: \~6.5 GB uncompressed, \~3 GB with compression**

### 7.4 Performance Considerations

**Import optimization:**

- Batch inserts: 1,000 records per database transaction (vs row-by-row)
- Parallel processing: Run NTSB, FAA AIDS, FAA SDR importers concurrently (separate threads)
- Incremental imports: Track `last_import_timestamp` per source, only fetch new records
- JASC mapping cache: Preload JASCMapping table into memory at import start (avoid repeated DB lookups)

**Query optimization:**

- Index `IncidentSource.source_name` for fast filtering by data source
- Index `IncidentSource.source_record_id` for deduplication lookups
- Composite index on `(incident_id, source_name)` for joining sources to incidents
- Index JASC codes in source\_data JSON (PostgreSQL GIN index on `source_data->>'jasc_code'`)

**Expected query performance:**

- Aircraft search (e.g., "Boeing 737"): < 200ms (indexed on aircraft\_model)
- Multi-source filter (e.g., "Show only NTSB + FAA AIDS"): < 100ms (indexed on source\_name)
- System tag filter (e.g., "Hydraulics"): < 150ms (indexed on system\_tags association table)

***

## 8. Success Metrics

This PRD prioritizes **technical coverage and deduplication accuracy** over user engagement metrics (which are deferred to Phase 2).

### 8.1 Data Coverage Metrics

**Target: 90% of NTSB accidents linked to FAA AIDS incidents**

Measurement:

- Query: `SELECT COUNT(*) FROM Incident WHERE ntsb_source_exists AND faa_aids_source_exists`
- Baseline (ASN-only): 0% (no FAA AIDS data)
- Phase 1 target: ≥90% of NTSB records have corresponding FAA AIDS record when applicable
- Tracking: Monthly report comparing NTSB accident count vs matched FAA AIDS incidents

**Target: 95% historical data coverage (1985-2025)**

Measurement:

- Total records imported vs expected records per source (based on source documentation)
- NTSB: 80,000 expected, ≥76,000 imported (95%)
- FAA AIDS: 120,000 expected, ≥114,000 imported (95%)
- FAA SDR: 1,600,000 expected, ≥1,520,000 imported (95%)
- Tracking: Import log summary reports "Records processed / Records available"

### 8.2 Deduplication Accuracy Metrics

**Target: 95% of duplicates correctly identified**

Measurement:

- Manual review of 1,000 randomly sampled incidents with multiple sources
- Count: (Correct auto-merges + Correct separate records) / Total sample
- Baseline (ASN-only): N/A (no duplicates possible)
- Phase 1 target: ≥950 correct decisions out of 1,000 samples
- Tracking: Monthly audit with report: "Precision: X%, Recall: Y%, F1-Score: Z%"

**Deduplication error categories:**

- **False positives** - System merged two distinct incidents (Type I error)
- **False negatives** - System kept duplicates separate (Type II error)

**Acceptable error rates:**

- False positive rate: ≤3% (30 out of 1,000 samples)
- False negative rate: ≤7% (70 out of 1,000 samples)
- Justification: False negatives (showing same incident twice) are less harmful than false positives (merging unrelated incidents)

### 8.3 Data Quality Metrics

**Target: 100% JASC code mapping for top 50 codes**

Measurement:

- Count: JASC codes in `JASCMapping` table / Top 50 most frequent JASC codes in FAA SDR data
- Baseline (ASN-only): 0% (no JASC codes)
- Phase 1 target: 100% of top 50 JASC codes mapped to SystemTag
- Tracking: Admin dashboard showing "48/50 top codes mapped (96%)" with list of unmapped codes

**Target: <5% import validation errors**

Measurement:

- Count: Validation errors / Total records processed
- Example: 100 errors out of 2,000 records processed = 5% error rate
- Phase 1 target: ≤5% of records rejected due to validation failures
- Tracking: Import log summary: "1,900 records imported, 100 skipped (5% error rate)"

### 8.4 System Reliability Metrics

**Target: 99% import success rate (at least one source succeeds)**

Measurement:

- Count: Successful import runs / Total import runs over 30 days
- Phase 1 target: If NTSB API is down, FAA AIDS and FAA SDR still import successfully
- Tracking: Monthly report: "29/30 daily imports had ≥1 successful source (97%)"

**Target: <7 days data staleness**

Measurement:

- Age of most recent record per source: `NOW() - MAX(last_updated)`
- Phase 1 target: All sources updated within 7 days
- Tracking: Dashboard shows "NTSB: 2 days ago, FAA AIDS: 5 days ago, FAA SDR: 20 days ago \[STALE]"

***

## 9. Open Questions

### 9.1 NTSB API Registration & Rate Limits

**Question:** Do we need formal approval for production use of NTSB API, or is free registration sufficient?

**Context:** NTSB developer portal requires registration but doesn't specify commercial use restrictions or rate limits.

**Impact:** If rate limits are strict (e.g., 100 req/day), we may need to rely primarily on bulk downloads instead of API for historical data.

**Decision needed by:** Week 1 of implementation (before writing NTSBImporter)

### 9.2 JASC Code Completeness

**Question:** FAA SDR documentation states JASC codes are "not consistently coded" - what % of records actually have usable JASC codes?

**Context:** If <50% of SDR records have JASC codes, the JASC → SystemTag mapping may not deliver expected value for system filtering.

**Impact:** May need fallback strategy: NLP extraction from defect description narratives if JASC codes are sparse.

**Decision needed by:** Week 2 of implementation (after initial SDR data exploration)

### 9.3 Deduplication Threshold Tuning

**Question:** What confidence threshold should trigger auto-merge vs manual review?

**Context:** Current spec says "High confidence (exact match): Auto-merge" but doesn't define exact thresholds.

**Proposed:**

- ≥95% confidence (exact registration + date match): Auto-merge
- 70-94% confidence (fuzzy match): Flag for manual review
- <70% confidence: Keep separate, show "Possibly related" link

**Impact:** Too aggressive merging → false positives (merging distinct incidents). Too conservative → false negatives (user sees duplicates).

**Decision needed by:** Week 3 of implementation (after deduplication algorithm testing)

### 9.4 FAA AIDS Update Frequency

**Question:** FAA AIDS is updated monthly - should we run incremental imports daily (checking for new data) or only once per month?

**Context:** Daily checks would be wasteful if data only updates monthly, but we don't want to miss a mid-month data drop.

**Proposed:** Check FAA AIDS weekly, import only if `last-modified` header indicates new data.

**Impact:** Minimal - FAA AIDS is incident-level data with weeks of reporting lag anyway.

**Decision needed by:** Week 1 of implementation (before writing scheduler)

### 9.5 Data Provenance Display

**Question:** Should we show "Imported from NTSB on 2026-03-28" at the record level, or just global "Last updated" footer?

**Context:** Per-record timestamps are more transparent but clutter the UI. Global footer is cleaner but less precise.

**Proposed:** Global footer for now (FR-4.4.4), add per-record timestamps in v3.0 if users request it.

**Impact:** Low - users primarily care that data is "recent" rather than exact import timestamps.

**Decision needed by:** Week 4 of implementation (UI design phase)

### 9.6 Import Rollback Strategy

**Question:** If an import job partially succeeds (e.g., NTSB imports 10,000 records, then crashes), should we commit partial results or rollback entire import?

**Context:** Partial commits mean users see some new data immediately. Full rollback means "all or nothing" consistency.

**Proposed:** Commit in batches of 1,000 records (database transactions), so a crash loses max 1,000 records worth of work.

**Impact:** Medium - affects import reliability and recovery time after failures.

**Decision needed by:** Week 2 of implementation (before writing import transaction logic)

***

## 10. Appendices

### 10.1 JASC Code Reference (Sample)

| JASC Code | Description                       | Mapped SystemTag      |
| --------- | --------------------------------- | --------------------- |
| 21-XX-XX  | Air Conditioning & Pressurization | Environmental Systems |
| 24-XX-XX  | Electrical Power                  | Electrical            |
| 27-XX-XX  | Flight Controls                   | Flight Controls       |
| 29-XX-XX  | Hydraulic Power                   | Hydraulics            |
| 32-XX-XX  | Landing Gear                      | Landing Gear          |
| 71-XX-XX  | Powerplant                        | Engine                |
| 79-XX-XX  | Engine Oil                        | Engine                |

**Full mapping:** See `docs/JASC_MAPPING.md` (to be created during implementation)

### 10.2 Data Source URLs (Quick Reference)

**NTSB:**

- API portal: `https://developer.ntsb.gov/`
- Bulk downloads: `https://data.ntsb.gov/avdata/avall.zip`
- Web interface: `https://data.ntsb.gov/carol-main-public/landing-page`

**FAA AIDS:**

- ASIAS portal: `https://www.asias.faa.gov/apex/f?p=100:189`
- Download page: Click "AIDS Download" → Select date range → Download ZIP

**FAA SDR:**

- Direct CSV: `https://external-api.faa.gov/sdrs/retrieve/SDR-{YEAR}.csv`
- Example: `https://external-api.faa.gov/sdrs/retrieve/SDR-2024.csv`

### 10.3 Estimated Timeline

**Weeks 1-2: Data Source Exploration & Architecture**

- Set up NTSB API access and test queries
- Download sample FAA AIDS and FAA SDR files
- Finalize database schema changes (IncidentSource, JASCMapping tables)
- Create base `DataSourceImporter` class

**Weeks 3-4: Importer Implementation**

- Build `NTSBImporter` class (API + bulk download support)
- Build `FAAAIDSImporter` class (tab-delimited parsing)
- Build `FAASDRImporter` class (CSV parsing + JASC mapping)
- Implement JASC → SystemTag mapping logic

**Weeks 5-6: Deduplication & Data Quality**

- Implement duplicate detection algorithm
- Build deduplication rules engine (exact + fuzzy matching)
- Create admin interface for reviewing merge decisions
- Test on sample data: 1,000 records from each source

**Weeks 7-8: Historical Data Import & Testing**

- Run full 40-year historical import (1985-2025)
- Monitor import logs for errors and validation issues
- Manual QA: Review 100 randomly sampled records per source
- Measure deduplication accuracy on 1,000-record sample

**Weeks 9-10: UI/UX Integration**

- Add source badges to incident detail pages
- Implement "Data Sources" sidebar filter
- Build "Additional Sources" accordion UI
- Add "Last updated" footer timestamps

**Weeks 11-12: Testing, Documentation & Launch**

- End-to-end testing: Search → Filter → View details → Export CSV
- Write admin documentation: "How to run manual imports"
- Write user documentation: "Understanding data sources"
- Deploy to staging, validate with domain expert (DASA acquaintance)
- Launch to production

**Total estimated: 12 weeks (3 months)**

### 10.4 Related Documentation

**To be created during implementation:**

- `docs/JASC_MAPPING.md` - Full JASC code → SystemTag mapping table
- `docs/DATA_SOURCES.md` - Detailed field mappings per source
- `docs/IMPORT_PROCEDURES.md` - Admin guide for running imports
- `docs/DEDUPLICATION_RULES.md` - Duplicate detection algorithm specification
- `README.md` section - "Multi-Source Data" explaining source badges and provenance

**Existing documentation (from PRD 0003):**

- `docs/ROLLBACK.md` - Version management and rollback procedures
- `0003-prd-aircraft-safety-lookup-v2.md` - v2.0 feature specifications

***

## 11. Acceptance Criteria

The Phase 1 multi-source integration is considered **complete and ready for production** when:

1. ✅ **All three sources imported:** NTSB, FAA AIDS, FAA SDR historical data (1985-2025) successfully loaded
2. ✅ **Data coverage target met:** ≥90% of NTSB accidents have corresponding FAA AIDS records
3. ✅ **Deduplication accuracy target met:** ≥95% correct merge decisions (measured on 1,000-record sample)
4. ✅ **JASC mapping complete:** Top 50 JASC codes mapped to SystemTag taxonomy
5. ✅ **UI displays source badges:** Users can see which organization(s) provided each data point
6. ✅ **Filtering works:** Users can filter by data source (NTSB, FAA AIDS, FAA SDR, ASN)
7. ✅ **Import logs functional:** Admin can review import history, error counts, and validation warnings
8. ✅ **Documentation complete:** Admin procedures, user guides, and JASC mapping table published
9. ✅ **Expert validation:** DASA acquaintance confirms tool meets regulatory analysis needs
10. ✅ **Performance acceptable:** Searches complete in <200ms even with 1.8M total records

***

**END OF PRD 0004**

***

## Revision History

| Version | Date       | Author       | Changes                                                     |
| ------- | ---------- | ------------ | ----------------------------------------------------------- |
| 1.0     | 2026-03-29 | Product Team | Initial draft based on aviation safety data source research |

