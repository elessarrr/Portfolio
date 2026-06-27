# Concepts

> Shared domain vocabulary for this project — entities, named processes, and status concepts with project-specific meaning. Seeded with core domain vocabulary, then accretes as compound learnings are written; direct edits are fine. Glossary only, not a spec or catch-all.

## Entities

### Aircraft

Catalog row representing an aircraft make/model (or variant). Incident statistics roll up to this entity. Used for search, detail pages, and source linkage.

### Incident

A single safety event in the database. May have multiple sources (ASN, NTSB, FAA AIDS). Display logic deduplicates and picks primary outbound links.

### IncidentSource

Per-source row for an incident. Holds `source_url`, `is_active`, and source-specific metadata. URL viability audits write back to this table.

## Status concepts

### is_active

Database flag on `IncidentSource`. When false, `link_picker` hides the outbound Details link so users never hit dead ASIAS/CAROL URLs.

### working_brief_report

FAA URL audit bucket: ASIAS page-18 brief report URL returns product-ready content. Required for shippable FAA links in the app.

### working_search_prefill

FAA URL audit bucket: ASIAS page-12 search prefill may HTTP OK but is not product-ready (user must click Search again).

### carol_empty_spa

NTSB CAROL status: HTTP 200 with empty React shell (`<main id="root"></main>`) and no investigation text. Must reject; fall back to docket URL when available.

## Named processes

### ASIAS liveness gate

Before bulk FAA URL audit, require ASIAS homepage HTTP 2xx. Site-wide CDN outage (503 on homepage) would false-positive every per-record check.

### FAA dedupe pass

Score-based overlap detection vs existing ASN/NTSB incidents. Uses lookup-only during dedupe; separate bootstrap for approved aircraft pages. One event → one visible row.

### NTSB make/model map

Normalize NTSB aircraft strings to catalog `Aircraft.id` before bulk import. Prevents auto-create bloat and unknown_aircraft rows in audit exports.

### ASRS aggregate profile

Aircraft-type-level rollup of NASA ASRS coded fields (contributing factors, event types, phase of flight) plus report count (`n`). Not joined to individual `Incident` rows — complementary to official ASN/NTSB/FAA records.

### DBOL export cap

ASRS Database Online limit on CSV/Excel exports per download (UI enforced ~5,000 records; NASA docs cite up to 10,000). Large model families require per-model queries or date-range sharding; no public bulk API.
