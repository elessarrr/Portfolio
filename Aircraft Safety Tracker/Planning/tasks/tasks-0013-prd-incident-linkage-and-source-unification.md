# tasks-0013-prd-incident-linkage-and-source-unification

## Overall Progress: 0% complete (0/4 phases done)

| Phase | Status | Description |
|---|---|---|
| 1 | 🔲 Pending | Recreate backfill script |
| 2 | 🔲 Pending | Harden resolve_aircraft() fix-forward |
| 3 | 🔲 Pending | Fix FAA_SDR zero-records pipeline |
| 4 | 🔲 Pending | Unify ASN into IncidentSource |

---

## Relevant Files

- `app/ingestion/importers/base.py` — `resolve_aircraft()` lives here; Phases 1 & 2
- `app/ingestion/importers/ntsb_importer.py` — calls `resolve_aircraft()`; Phase 2
- `app/ingestion/importers/faa_aids_importer.py` — calls `resolve_aircraft()`; Phase 2
- `app/ingestion/importers/faa_sdr_importer.py` — zero-records pipeline; Phase 3
- `app/ingestion/bulk/faa_sdr_bulk.py` — bulk processing for FAA_SDR; Phase 3
- `scripts/import_data.py` — legacy ASN ingestion path; Phase 4
- `app/models.py` — `Incident`, `IncidentSource`, `Aircraft` models; all phases (read)
- `app/ingestion/canonical.py` — canonicalization rules; Phase 2 reference
- `scripts/backfill_aircraft_ids.py` — to be created in Phase 1
- `tests/test_importer_base.py` — Phase 2 tests
- `tests/test_faa_sdr_importer.py` — Phase 3 tests
- `tests/test_faa_sdr_bulk.py` — Phase 3 tests
- `tests/test_asn_sync.py` — Phase 4 tests

---

## Notes

- **Boeing/Airbus only.** Do not attempt to link general aviation (Cessna, Piper, etc.)
  incidents. The resolver intentionally ignores non-Boeing/Airbus make_model strings.
- **Idempotency is mandatory.** Every script and migration must be safe to re-run without
  creating duplicate rows or corrupting existing data.
- **No UI changes.** PRD-0012 already handles display and source prioritization.
- **Status reports required.** After each phase, Cursor must return a status report
  (see template at bottom of each phase prompt).

---

## Phase 1 Prompt — Recreate the Backfill Script

> **Copy this entire block and paste it to Cursor.**

---

### Context

We have ~236,000 incidents in the database where `incident.aircraft_id IS NULL`. These
incidents are invisible to all aircraft detail pages because the routes filter by the
`aircraft.incidents` SQLAlchemy relationship, which requires a non-null `aircraft_id`.

The incidents do have `IncidentSource` rows attached (source_name = 'NTSB' or 'FAA_AIDS'),
and those `IncidentSource` rows contain the raw source payload in the `source_data` JSON
column. The raw payload includes make/model fields that can be fed back into the existing
`resolve_aircraft()` method in `app/ingestion/importers/base.py`.

A backfill script (`scripts/backfill_aircraft_ids.py`) previously existed but was deleted.
We need to recreate it.

### Task

Create `scripts/backfill_aircraft_ids.py`. This script must:

1. **Query in batches** (batch size 500) all `Incident` rows where `aircraft_id IS NULL`
   and that have at least one attached `IncidentSource` row.
2. **For each incident**, iterate its `IncidentSource` rows and attempt to extract a
   make/model string. The extraction logic should try these fields in order from
   `source_data` JSON:
   - `make_model`
   - `make` + `" "` + `model` (concatenated)
   - `acft_make` + `" "` + `acft_model` (NTSB field names)
3. **Feed the extracted make_model string into `resolve_aircraft()`** from
   `app/ingestion/importers/base.py`. This method already handles Boeing/Airbus
   auto-creation and exact ilike matching — do not duplicate its logic.
4. **If `resolve_aircraft()` returns a non-null ID**, update `incident.aircraft_id` with
   that ID.
5. **Commit in batches** of 500 to avoid holding a long transaction.
6. **Be idempotent** — safe to re-run. Already-linked incidents (aircraft_id IS NOT NULL)
   must be skipped entirely.
7. **Print a summary** at the end: total processed, total newly linked, total skipped
   (already linked), total unresolved (Boeing/Airbus string found but no match created),
   total ignored (non-Boeing/Airbus — expected and fine).

### Constraints

- Do NOT modify `resolve_aircraft()` in this phase. Use it as-is.
- Do NOT touch any importer files in this phase.
- The script must import the Flask app context correctly (follow the pattern used in
  other scripts in `scripts/` — check `scripts/import_data.py` for the app context
  bootstrap pattern).
- Add a `--dry-run` flag that prints what would be linked without committing anything.
- Add comprehensive comments explaining what the script does and why, suitable for a
  junior engineer reading it for the first time.

### Tests

Add a test in `tests/test_importer_base.py` (or a new `tests/test_backfill.py` if more
appropriate) that:
- Creates an unlinked `Incident` with an `IncidentSource` row containing a Boeing
  make_model in `source_data`.
- Runs the backfill logic (not the full script, but the core linking function).
- Asserts the incident now has a non-null `aircraft_id`.
- Asserts re-running is idempotent (no duplicate Aircraft rows created).

### Status Report Required

After completing this phase, return a status report with:
```
## Phase 1 Status Report
- Files created: [list]
- Files modified: [list]
- Incidents linked (dry-run count if available): [number]
- Aircraft rows auto-created (dry-run count if available): [number]
- Tests added: [list test names]
- Tests passing: [yes/no]
- Any blockers or unexpected findings: [description]
```

---

## Phase 2 Prompt — Harden resolve_aircraft() Fix-Forward

> **Copy this entire block and paste it to Cursor. Run AFTER Phase 1 is complete.**

---

### Context

Phase 1 fixed the historical backlog. Phase 2 ensures future ingestion runs link
Boeing/Airbus incidents correctly on first import, so the backfill script never needs
to be run again for newly ingested data.

The current `resolve_aircraft()` in `app/ingestion/importers/base.py` has two weaknesses:

**Weakness 1 — Exact ilike match only.**
NTSB/FAA data arrives with strings like `"BOEING 737"` or `"BOEING 737-800"`. The DB
may already have `"Boeing 737-800"` (from ASN). The `.ilike()` match handles
case-insensitivity but requires an exact string match. A record arriving as
`"BOEING 737 800"` (space instead of hyphen) or `"BOEING B737"` will miss the match
and fall through to auto-create a duplicate generic Aircraft row.

**Weakness 2 — No fuzzy/prefix fallback before auto-create.**
Before auto-creating a new `Aircraft` row, the resolver should check whether an
existing Aircraft row's `model_name` starts with the same Boeing/Airbus prefix (e.g.,
`"BOEING 737"` should match `"Boeing 737-800"` as a fallback rather than creating a
new generic `"BOEING 737"` row).

### Task

Modify `resolve_aircraft()` in `app/ingestion/importers/base.py`:

1. **Keep the existing exact ilike match as Step 1** — no change here.
2. **Add Step 2: prefix match fallback.** Before auto-creating, query for any existing
   `Aircraft` where `model_name` starts with the incoming `make_model` string
   (case-insensitive). If exactly one match is found, use it. If multiple matches are
   found, use the one with the highest `total_incidents` (most data-rich record).
3. **Add Step 3: normalise the make_model string before matching.** Apply these
   normalizations before Steps 1 and 2:
   - Strip leading/trailing whitespace (already done via `.strip()`).
   - Collapse multiple internal spaces to one.
   - Replace `" - "` and `"_"` with `"-"` for hyphen consistency.
   - Uppercase the entire string for comparison only (do not change the stored value).
4. **Keep the existing Boeing/Airbus auto-create as Step 4** (the final fallback).
5. **Keep the existing `return None` for non-Boeing/Airbus** — do not expand scope.

Also update `ntsb_importer.py` and `faa_aids_importer.py`:
- After calling `resolve_aircraft()`, if the returned `aircraft_id` is `None` AND the
  `make_model` string starts with `"boeing"` or `"airbus"` (case-insensitive), log a
  WARNING with the make_model string. This creates an observable signal for any future
  resolver gaps.

### Tests

In `tests/test_importer_base.py`, add tests covering:
- Exact ilike match (existing behaviour, regression test).
- Prefix match: `"BOEING 737"` resolves to existing `"Boeing 737-800"` Aircraft row.
- Normalisation: `"BOEING  737-800"` (double space) resolves correctly.
- Auto-create: `"BOEING 999"` (no existing match) creates a new Aircraft row.
- Non-Boeing/Airbus: `"CESSNA 172"` returns `None` (no auto-create).
- Idempotency: calling auto-create twice for the same model_name does not create
  duplicate Aircraft rows.

### Status Report Required

After completing this phase, return a status report with:
```
## Phase 2 Status Report
- Files modified: [list]
- Changes made to resolve_aircraft(): [bullet summary]
- Changes made to importers: [bullet summary]
- Tests added: [list test names]
- Tests passing: [yes/no]
- Any edge cases found: [description]
```

---

## Phase 3 Prompt — Fix FAA_SDR Zero-Records Pipeline

> **Copy this entire block and paste it to Cursor. Run AFTER Phase 2 is complete.**

---

### Context

The FAA_SDR data source shows `last_records_processed = 0` in the import log, despite
the import job completing with a "completed" status. This means either:
- (a) The FAA_SDR API is returning empty or malformed responses.
- (b) The parser in `faa_sdr_importer.py` or `faa_sdr_bulk.py` is silently discarding
  all records (e.g., a field validation check that always fails).
- (c) The importer is not being called at all, or is being called with wrong parameters.
- (d) The API endpoint or authentication has changed.

### Task

**Step 1 — Diagnose first, fix second.**

Before writing any fix, read the following files in full and report findings:
- `app/ingestion/importers/faa_sdr_importer.py`
- `app/ingestion/bulk/faa_sdr_bulk.py`
- Any FAA_SDR client file in `app/ingestion/clients/` if one exists
- The relevant section of `app/ingestion/cli.py` that invokes the FAA_SDR importer
- The `ImportLog` model in `app/models.py`

In the status report (see below), describe exactly which of (a)/(b)/(c)/(d) is the
cause before making any code changes.

**Step 2 — Fix the identified root cause.**

Apply the minimal fix needed to make FAA_SDR process > 0 records per run. Do not
refactor unrelated code.

**Step 3 — Verify linkage.**

After the pipeline fix, confirm that `resolve_aircraft()` (now hardened in Phase 2)
is being called correctly for FAA_SDR records, and that Boeing/Airbus FAA_SDR incidents
will receive a non-null `aircraft_id` on import.

**Step 4 — Add a synthetic data test.**

In `tests/test_faa_sdr_importer.py` or `tests/test_faa_sdr_bulk.py`, add a test that:
- Uses synthetic/mock FAA_SDR API response data (clearly commented as fake/synthetic).
- Asserts that the importer processes > 0 records from that mock response.
- Asserts that a Boeing/Airbus record in the mock response results in an `Incident`
  with a non-null `aircraft_id`.

### Constraints

- If the FAA_SDR API requires credentials that are not available in the test environment,
  mock the HTTP client call using the existing test patterns in `tests/conftest.py`.
- Do not change the `ImportLog` model schema.

### Status Report Required

After completing this phase, return a status report with:
```
## Phase 3 Status Report
- Root cause identified (a/b/c/d): [answer + explanation]
- Files modified: [list]
- Fix applied: [description]
- FAA_SDR records processed in test run (or mock assertion): [number/result]
- Tests added: [list test names]
- Tests passing: [yes/no]
- Any blockers: [description]
```

---

## Phase 4 Prompt — Unify ASN into IncidentSource

> **Copy this entire block and paste it to Cursor. Run AFTER Phase 3 is complete.**

---

### Context

ASN incidents were ingested via a legacy path in `scripts/import_data.py` that writes
`incident.asn_url` and `incident.aircraft_id` directly onto the `Incident` row, without
creating any `IncidentSource` row. This creates a split data model:

- NTSB / FAA_AIDS / FAA_SDR incidents → have `IncidentSource` rows, `asn_url = NULL`
- ASN incidents → have `asn_url` set, NO `IncidentSource` row

This split causes inconsistencies in source filtering, source badge display, and any
future analytics that query `IncidentSource`. The goal of this phase is to unify the
model so all incidents have `IncidentSource` rows.

Current state (from DB diagnostics):
- 1,798 ASN incidents exist, all with `aircraft_id` set, none with an `IncidentSource` row.
- `IncidentSource.source_name` for ASN should be `'ASN'`.
- `IncidentSource.source_url` should be set to the value of `incident.asn_url`.
- `incident.asn_url` should be retained (do not remove the column — it may be used
  elsewhere in templates and routes).

### Task

**Step 1 — Write a one-time migration script.**

Create `scripts/migrate_asn_to_incident_source.py` that:
1. Queries all `Incident` rows where `asn_url IS NOT NULL` and that do NOT already have
   an `IncidentSource` row with `source_name = 'ASN'`.
2. For each such incident, creates an `IncidentSource` row:
   - `incident_id` = the incident's id
   - `source_name` = `'ASN'`
   - `source_url` = the incident's `asn_url`
   - `source_record_id` = the incident's `asn_url` (use as a stable dedup key)
   - `source_data` = `{"asn_url": incident.asn_url}` (minimal JSON)
3. Commits in batches of 500.
4. Is idempotent — safe to re-run.
5. Prints a summary: total processed, total created, total skipped (already had ASN
   IncidentSource row).

**Step 2 — Update `scripts/import_data.py` for future ASN imports.**

Modify the ASN ingestion path in `scripts/import_data.py` so that on every new or
updated ASN incident, it also upserts an `IncidentSource` row with `source_name = 'ASN'`
and `source_url = asn_url`. Use `source_record_id = asn_url` as the upsert key to
avoid duplicates on re-runs.

**Step 3 — Verify `incident_list.html` still works.**

The template currently has an `{% elif incident.asn_url %}` fallback for rendering the
ASN badge and link. After this migration, ASN incidents will have both `asn_url` AND an
`IncidentSource` row. Verify (read-only, no changes needed unless broken) that the
template's existing `primary_source` logic will now correctly pick up the ASN
`IncidentSource` row and render the badge via the standard path, not the fallback path.
If the template needs a minor fix to handle this correctly, apply it.

### Constraints

- Do NOT remove the `asn_url` column from the `Incident` model or any template.
- Do NOT create an Alembic migration — this is a data migration only, not a schema change.
- The migration script must be safe to run against the production database.

### Tests

In `tests/test_asn_sync.py` (or a new `tests/test_asn_migration.py`), add tests that:
- Assert that after running the migration logic, an ASN incident has an `IncidentSource`
  row with `source_name = 'ASN'`.
- Assert idempotency: running the migration twice does not create duplicate
  `IncidentSource` rows.
- Assert that the `scripts/import_data.py` ASN upsert path creates an `IncidentSource`
  row for a new incident.

### Status Report Required

After completing this phase, return a status report with:
```
## Phase 4 Status Report
- Files created: [list]
- Files modified: [list]
- ASN IncidentSource rows created (migration dry-run or test assertion): [number]
- Template changes needed: [yes/no + description]
- Tests added: [list test names]
- Tests passing: [yes/no]
- Any blockers: [description]
```

---

## Status Report Template (Master)

After ALL four phases are complete, return a final master status report:

```
## PRD-0013 Final Status Report
- Phase 1 complete: [yes/no]
- Phase 2 complete: [yes/no]
- Phase 3 complete: [yes/no]
- Phase 4 complete: [yes/no]
- Total incidents linked (before vs after): [X → Y]
- FAA_SDR records processing: [yes/no]
- ASN IncidentSource rows created: [number]
- All tests passing: [yes/no]
- Remaining known gaps: [description or "none"]
```
