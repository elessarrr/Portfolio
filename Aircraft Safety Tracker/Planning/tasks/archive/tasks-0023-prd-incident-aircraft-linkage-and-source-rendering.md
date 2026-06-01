## Relevant Files

- `app/ingestion/cli.py` - Two changes: (1) aircraft_id null guard in the `enrich-wa-incidents` write path; (2) new `reconcile-aircraft-mapping` CLI command.
- `app/ingestion/importers/base.py` - Extract `resolve_aircraft_for_incident` as a standalone function so it can be called outside an active importer instance.
- `app/templates/components/incident_list.html` - Minor: update "No sources" empty-state text to "No source links available".
- `app/routes.py` - Optional: add route-level `is_active=True` pre-filter on incident sources.
- `tests/test_ingestion_cli.py` - New or extended: tests for the aircraft_id guard and the reconcile command.

### Notes

- Run tests with `python -m pytest tests/test_ingestion_cli.py`.
- `incident_list.html` already filters to `is_active=True` sources at line 21 (`selectattr('is_active')`). PRD-0023 requirement 9 is already implemented — task 3.0 is a text/style verification, not a build.
- The empty-state "No sources" badge already exists at line 94–96. Task 3.0 updates text only.
- `resolve_aircraft` on `DataSourceImporter` (line 404, `base.py`) has three steps: (1) exact case-insensitive match, (2) prefix-match fallback, (3) auto-create for Boeing/Airbus only. Steps 1–2 are safe to extract; step 3 calls `self._log_model_creation()` which is instance-bound and must stay in the importer method. Task 2.2 extracts steps 1–2 only into `resolve_aircraft_for_incident` and has the importer delegate to it — **step 3 must not be moved or removed from the importer method**. The reconcile command calls the standalone function only.
- Task 4.0 (route-level pre-filter) is optional hardening; implement after tasks 1–3 are complete and tests pass.
- PRD-0023 depends on PRD-0022's `validate-ntsb-links` job having run at least once before the UI guard has its full effect on NTSB broken links.
- `list_scheduled_jobs.py` does not exist yet — it is being built in tasks-0022 (task 5.2–5.5). Until then, the three known scheduled jobs are: daily 02:00 `enrich_wa_incidents.sh`, Monday 09:00 `update_data.sh`, and Sunday 02:00 `validate_incident_links.py` (plist pending tasks-0022).

## Tasks

- [ ] 1.0 Guard MEDIA source write path against null `aircraft_id`
  - [ ] 1.1 In `enrich_wa_incidents` (`app/ingestion/cli.py`), add an `aircraft_id` null check immediately before the `IncidentSource` creation block (~line 322): if `incident.aircraft_id is None`, increment a new `aircraft_null_skip_count` counter, log `WARNING: "Skipping MEDIA source save for incident {incident.id} ({event_id}): aircraft_id is NULL — article would be unreachable from card"`, and `continue`.
  - [ ] 1.2 Do NOT write a `MEDIA_NO_RESULT` record for aircraft_id-null skips. Add an inline comment explaining this is intentional: once `reconcile-aircraft-mapping` resolves `aircraft_id`, the incident will be re-targeted by the enrichment job.
  - [ ] 1.3 Add `aircraft_null_skip_count` to the enrichment summary `click.echo` block so the operator sees how many incidents were skipped for this reason.
  - [ ] 1.4 Also add a `MEDIA_NO_RESULT` exclusion to the target-incident query (the subquery block around line 205): add a subquery that excludes incidents where an `IncidentSource` with `source_name='MEDIA_NO_RESULT'` exists, mirroring the existing `media_source_sub` exclusion pattern.

- [ ] 2.0 Extract aircraft-resolution logic and implement `reconcile-aircraft-mapping` CLI command
  - [ ] 2.1 The design for `resolve_aircraft_for_incident` is already confirmed: extract steps 1 and 2 from `DataSourceImporter.resolve_aircraft` (line 404, `base.py`) — both steps require only `current_app` context and DB session. Step 3 (auto-create) calls `self._log_model_creation()` and must stay in the importer method. Proceed directly to task 2.2.
  - [ ] 2.2 Create a new module-level function `resolve_aircraft_for_incident(raw_model_variant: str) -> Optional[int]` in `app/ingestion/importers/base.py` containing **steps 1–2 only**: (1) exact case-insensitive match against `Aircraft.model_name`; (2) prefix-match fallback ordered by `total_incidents.desc()`. Do **not** include step 3 (auto-create) — it must remain in `DataSourceImporter.resolve_aircraft` to avoid duplicate rows during backfill. Update `DataSourceImporter.resolve_aircraft` to delegate steps 1–2 to `resolve_aircraft_for_incident(parsed_record["make_model"])` and retain step 3 locally, so no existing importer behaviour changes.
  - [ ] 2.3 Register a new CLI command `@import_data.command('reconcile-aircraft-mapping')` in `app/ingestion/cli.py` with `--dry-run` (flag) and `--batch-size` (int, default 100) options.
  - [ ] 2.4 Inside the command: query all `IncidentSource` rows where `source_name='MEDIA'`; join to their parent `Incident`; filter where `Incident.aircraft_id IS NULL`.
  - [ ] 2.5 For each matched incident, call `resolve_aircraft_for_incident(incident.raw_model_variant)`; if a non-null `aircraft_id` is returned, set `incident.aircraft_id` and commit (in batches of `batch_size`); otherwise log the failure and add to an `unresolved` list.
  - [ ] 2.6 Wrap each batch update in a `try/except IntegrityError`; on error, roll back the batch and log which incident IDs failed.
  - [ ] 2.7 Print a completion summary: total orphaned incidents found, resolved count, unresolved count. For each unresolved incident, print `incident.id`, `event_id`, and `raw_model_variant` so they can be addressed manually.
  - [ ] 2.8 Add `flask import-data reconcile-aircraft-mapping` as the first command in `scripts/enrich_wa_incidents.sh`, before the existing `flask import-data enrich-wa-incidents` call. This ensures that on every daily run, aircraft linkage is resolved before enrichment attempts, so newly-linked incidents are picked up in the same run.

- [ ] 3.0 Verify and update "No source links available" empty state in `incident_list.html`
  - [ ] 3.1 Confirm the `is_active` filter at line 21 (`selectattr('is_active')`) and the `sorted_sources` variable are correctly scoping the badge loop — no code change expected.
  - [ ] 3.2 Update the empty-state text at line 95 from `"No sources"` to `"No source links available"`. Adjust the span's classes from the current badge style (`bg-gray-100 text-gray-700`) to a lower-key inline text style (`text-xs text-gray-400`) consistent with the `"No tags"` and `"No external link"` patterns already in the template.
  - [ ] 3.3 Verify the `"No external link"` fallback at lines 124–125 renders correctly when there is no active primary source with a valid URL — no code change expected, just a visual check.

- [ ] 4.0 Add route-level `is_active` pre-filter for incident sources (optional hardening)
  - [ ] 4.1 In `app/routes.py`, locate the aircraft detail route where `incident.sources.all()` is called or where the sources list is built for template context.
  - [ ] 4.2 Add `.filter(IncidentSource.is_active == True)` to the sources query so the template receives only active sources, removing the need for the template's own `selectattr('is_active')` pass. Import `IncidentSource` in the route file if not already imported.
  - [ ] 4.3 Leave the template's `selectattr('is_active')` filter in place as a belt-and-suspenders guard — it is a no-op if the route pre-filters correctly but provides safety if other routes render the same partial without pre-filtering.

- [ ] 5.0 Tests and validation
  - [ ] 5.0a Add unit tests for `resolve_aircraft_for_incident` in `tests/test_ingestion_cli.py`: (1) seed an `Aircraft` row with a known `model_name`, call `resolve_aircraft_for_incident` with an exact-match variant, assert the correct `aircraft_id` is returned; (2) call `resolve_aircraft_for_incident` with an unrecognised variant, assert `None` is returned and no new `Aircraft` rows exist in the DB after the call.
  - [ ] 5.1 Add a unit test in `tests/test_ingestion_cli.py` for the aircraft_id null guard: mock an incident with `aircraft_id=None` and a valid search result; assert no `IncidentSource` record is created and the `WARNING` log is emitted.
  - [ ] 5.2 Add a unit test for `reconcile-aircraft-mapping --dry-run`: seed an `Incident` with `aircraft_id=None` and a linked MEDIA `IncidentSource`; run the command in dry-run mode; assert `incident.aircraft_id` is still `None` after the run.
  - [ ] 5.3 Add a unit test for `reconcile-aircraft-mapping` (live mode): seed the same incident; run the command; assert `incident.aircraft_id` is set correctly when `resolve_aircraft_for_incident` finds a match.
  - [ ] 5.4 Run `flask import-data enrich-wa-incidents --dry-run` manually after deploying task 1.0; confirm the `aircraft_null_skip_count` appears in summary output for known-null incidents.
  - [ ] 5.5 Run `flask import-data reconcile-aircraft-mapping --dry-run` after deploying task 2.0; review the unresolved list to identify which `raw_model_variant` values need manual `Aircraft` row additions.
