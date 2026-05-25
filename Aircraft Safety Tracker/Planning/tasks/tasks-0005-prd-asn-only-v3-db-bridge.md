## Relevant Files

- `scripts/copy_v2_to_v3.py` - New raw SQLite copy script for moving all aircraft and ASN-linked incidents from the v2 DB into the clean v3 DB.
- `data/aircraft_safety.db` - Local v2 source database; read-only input, never committed.
- `data/aircraft_safety_v3.db` - Local clean v3 target database; generated/updated locally, never committed.
- `app/models.py` - Defines the v3-compatible `Aircraft`, `Incident`, and `IncidentSource` columns used by the copy script.
- `app/link_picker.py` - Existing ASN-first link picker that should render all copied incidents as working Details links.
- `app/templates/components/incident_list.html` - Existing incident list template to verify no copied ASN incident renders `N/A` or `href=""`.
- `tests/test_link_picker.py` - Existing link rendering tests; may be extended if needed for ASN-only bridge guarantees.
- `JOURNAL.md` - Engineering log to document the ASN-only DB bridge decision and resulting counts.

### Notes

- This PRD intentionally does not copy `incident_source` rows.
- SQLite DB files must remain gitignored and uncommitted.
- Run tests from `Aircraft Safety Tracker/` with `PYTHONPATH=. pytest -q`.
- App smoke tests should run against `DATABASE_URL=sqlite:////Users/Bhavesh/Documents/GitHub/Portfolio/Aircraft Safety Tracker/data/aircraft_safety_v3.db`.

## Tasks

- [x] 1.0 Confirm clean v3 database preconditions
  - [x] 1.1 Confirm current git branch is `v3-boeing-airbus-links` and do not switch branches.
  - [x] 1.2 Confirm `data/aircraft_safety.db` exists and is treated as the immutable v2 source DB.
  - [x] 1.3 Confirm `data/aircraft_safety_v3.db` exists or create/recreate it from clean v3 migrations only.
  - [x] 1.4 Verify the v3 target schema has `aircraft`, `incident`, and empty `incident_source` tables.
  - [x] 1.5 Record baseline source counts from v2 DB: expected `1,266` aircraft and `1,796` ASN-linked incidents.
- [x] 2.0 Implement ASN-only v2-to-v3 copy script
  - [x] 2.1 Create `scripts/copy_v2_to_v3.py` using Python standard-library `sqlite3`.
  - [x] 2.2 Open `data/aircraft_safety.db` read-only so the v2 source cannot be mutated accidentally.
  - [x] 2.3 Open `data/aircraft_safety_v3.db` as the writable target.
  - [x] 2.4 Copy all `aircraft` rows using only v3-compatible columns and preserving original `id` values.
  - [x] 2.5 Copy only `incident` rows where `asn_url IS NOT NULL AND asn_url != ''`.
  - [x] 2.6 Copy only these incident columns: `id`, `aircraft_id`, `date`, `operator`, `location`, `fatalities`, `description`, `asn_url`, `incident_type`.
  - [x] 2.7 Do not copy any `incident_source` rows.
  - [x] 2.8 Make the script idempotent so reruns do not duplicate rows.
  - [x] 2.9 Print verification counts and exit non-zero if expected counts fail.
- [x] 3.0 Run the copy and verify database counts
  - [x] 3.1 Run the copy script against the clean v3 target DB.
  - [x] 3.2 Verify target `aircraft` count is `1,266`.
  - [x] 3.3 Verify target `incident` count is `1,796`.
  - [x] 3.4 Verify target `incident_source` count is `0`.
  - [x] 3.5 Verify copied incidents with missing/empty `asn_url` count is `0`.
  - [x] 3.6 Verify copied incident manufacturer breakdown is `312` Boeing and `1,484` Airbus.
  - [x] 3.7 Re-run the copy script once and confirm counts remain unchanged.
- [x] 4.0 Smoke test app behavior against ASN-only v3 DB
  - [x] 4.1 Start Flask with `DATABASE_URL` pointing to `data/aircraft_safety_v3.db`.
  - [x] 4.2 Confirm homepage returns HTTP 200.
  - [x] 4.3 Confirm search returns representative Boeing and Airbus aircraft.
  - [x] 4.4 Open representative Boeing and Airbus aircraft pages and confirm they return HTTP 200.
  - [x] 4.5 Confirm rendered incident rows show working `Details` links.
  - [x] 4.6 Confirm no copied incident row renders `href=""`.
  - [x] 4.7 Confirm no copied incident row renders `N/A` in the Details column.
  - [x] 4.8 Run `PYTHONPATH=. pytest -q`.
- [x] 5.0 Document and commit the bridge artifact
  - [x] 5.1 Update `JOURNAL.md` with the ASN-only bridge decision, final counts, and DB policy.
  - [x] 5.2 Ensure no SQLite DB files are staged.
  - [x] 5.3 Review `git diff` for the task script, task list, PRD, and journal changes.
  - [x] 5.4 Commit only relevant markdown/script changes with a conventional commit message.
  - [x] 5.5 Note in the final status report that NTSB/FAA imports remain deferred future phases.
