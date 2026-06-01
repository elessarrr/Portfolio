# PRD: Incident-to-Aircraft Linkage & Source Link Integrity

## 1. Introduction/Overview

Two classes of data integrity failure are currently degrading the aircraft card experience:

1. **Orphaned MEDIA sources:** 23 of 26 MEDIA `IncidentSource` records are attached to incidents where `aircraft_id=NULL`. Since the aircraft card page (`/aircraft/<id>`) queries incidents via `aircraft.incidents` (a relationship keyed on `aircraft_id`), these articles are permanently invisible to card-page visitors.

2. **Broken source links rendered in UI:** NTSB docket and report PDF links that are known-broken (`docket_not_released`, HTTP 404) are still rendered as clickable buttons on incident cards, misleading users who click them and find no usable content.

This PRD resolves both problems: it prevents future orphaned MEDIA sources at the ingestion write path, backfills the existing 23 orphaned incidents with correct `aircraft_id` values, and adds a UI guard so that only `is_active=True` source links are rendered on aircraft cards. It depends on PRD-0022's `validate-ntsb-links` command having deactivated broken NTSB sources before the UI guard takes effect.

## 2. Goals

* **No future orphans:** The MEDIA source write path in `enrich-wa-incidents` rejects any incident with `aircraft_id=NULL` rather than silently saving an unreachable record.
* **Existing orphans resolved:** A backfill CLI command resolves `aircraft_id` for the 23 existing orphaned incidents using the same aircraft-resolution logic already available in the importer base.
* **Clean card rendering:** Aircraft card incident tables only display source links for sources where `is_active=True`.
* **Transparent broken-link state:** Incidents with no active source links show a neutral "No source links available" state rather than rendering nothing or broken buttons.

## 3. User Stories

* **As an end-user**, when I open an aircraft card page, I want every "Details" and "NTSB Docs" link I see to lead to a real, accessible page — not a 404 or an unreleased docket.
* **As an end-user**, when I open an aircraft card page for an aircraft that has press coverage, I want to see a link to that article — even if it was ingested via a WA-coded incident.
* **As the system operator**, I want to run a single CLI command that resolves `aircraft_id` for all orphaned MEDIA-linked incidents, so the backlog of 23 invisible articles becomes visible on their correct aircraft cards.
* **As a developer**, I want the `enrich-wa-incidents` write path to log a clear warning and skip saving if it would create an orphaned MEDIA source, so the problem never recurs silently.

## 4. Functional Requirements

### 4A. Prevent Future Orphans (Ingestion Write Path)

1. **Pre-save aircraft_id guard:** In `app/ingestion/cli.py`, before creating a new `IncidentSource` record with `source_name='MEDIA'`, assert that `incident.aircraft_id` is not `None`. If it is `None`, log a `WARNING`: `"Skipping MEDIA source save for incident {incident.id} ({event_id}): aircraft_id is NULL — article would be unreachable from card"` and continue to the next incident without saving.
2. **MEDIA_NO_RESULT on guard skip:** When an incident is skipped due to the null `aircraft_id` guard, do **not** write a `MEDIA_NO_RESULT` record. The skip reason is a linkage gap, not a search gap; writing `MEDIA_NO_RESULT` would permanently block re-enrichment after the backfill resolves `aircraft_id`.

### 4B. Backfill Existing Orphans (New CLI Command)

3. **`reconcile-aircraft-mapping` command:** A new command `flask import-data reconcile-aircraft-mapping` must query all `IncidentSource` rows where `source_name='MEDIA'` and `incident.aircraft_id IS NULL`.
4. **Resolution logic — match-only standalone function:** A new module-level function `resolve_aircraft_for_incident(raw_model_variant: str) -> Optional[int]` must be extracted from `DataSourceImporter.resolve_aircraft` in `app/ingestion/importers/base.py`. This function must implement only the two matching steps of the original method: (1) exact case-insensitive lookup against `Aircraft.model_name`, (2) prefix-match fallback selecting the highest-incident-count candidate. It must **not** auto-create new `Aircraft` rows — auto-creation belongs to the importer pipeline and risks producing duplicate rows during backfill. The existing `DataSourceImporter.resolve_aircraft` method must delegate to this function for steps 1–2 and retain step 3 (auto-create) locally, so no existing importer behaviour changes.
5. **Write on success:** If `resolve_aircraft_for_incident` returns a non-null aircraft ID, set `incident.aircraft_id` to that value and commit.
6. **Log on failure:** If `resolve_aircraft_for_incident` returns `None`, log a `WARNING`: `"Could not resolve aircraft for incident {incident.id} ({event_id}): raw_model_variant='{raw_model_variant}'"` and leave the row unchanged. Collect all unresolved incidents and print them in the final summary so sparse variants can be addressed manually.
7. **Summary output:** On completion, the command must print a summary: total orphaned incidents found, resolved count, unresolved count (including `raw_model_variant` for each unresolved row).
8. **Dry-run mode:** The command must support `--dry-run` to log what would be changed without committing.
9. **Daily cron integration:** `reconcile-aircraft-mapping` must be added to `scripts/enrich_wa_incidents.sh` to execute immediately before the existing `flask import-data enrich-wa-incidents` call. This ensures that on every daily run (02:00 via `com.aircraftsafetytracker.wa-enrichment.daily.plist`), aircraft linkage is resolved first so newly-linked incidents are picked up by enrichment in the same run without needing a manual re-trigger.

### 4C. UI Source Link Guard (Template)

9. **Active-only source rendering:** In `app/templates/components/incident_list.html`, filter the sources loop to only iterate sources where `source.is_active == True`. Sources where `is_active=False` must not render any link or button.
10. **Empty-source state:** If an incident has no `is_active=True` sources after filtering, render a neutral inline text element: `No source links available` (unstyled, not a button or link).
11. **No behavior change for active sources:** The existing rendering logic for NTSB `Details` / `NTSB Docs` buttons and MEDIA article links must be unchanged for `is_active=True` sources.

### 4D. Route-Level Source Filtering (Optional Hardening)

12. **Source pre-filter in route:** In `app/routes.py`, the aircraft detail query may optionally pre-filter `IncidentSource` rows to `is_active=True` at the SQLAlchemy level before passing incident data to the template. This reduces template complexity and avoids the template needing to evaluate `is_active` per-row. If implemented, requirement 9 becomes a no-op guard.

## 5. Non-Goals (Out of Scope)

* **NTSB link deactivation:** Marking broken NTSB sources `is_active=False` is handled in PRD-0022. This PRD only consumes that state via the UI guard.
* **Aircraft auto-creation in reconcile command:** `resolve_aircraft_for_incident` intentionally excludes auto-creation. Creating new `Aircraft` rows during backfill is out of scope — unresolved variants are logged for manual follow-up in a future PRD.
* **Aircraft auto-creation:** If `resolve_aircraft` cannot find a match, this PRD does not attempt to create a new `Aircraft` record. Auto-creation risk (duplicate aircraft) is out of scope.
* **Global incidents dashboard:** The `global_incident_list.html` partial is out of scope; the active-only guard applies to aircraft card rendering only in this PRD.

## 6. Design Considerations

* The `is_active=False` guard in the template is a one-line Jinja2 change (`{% if source.is_active %}`). Implement the route-level pre-filter (requirement 12) if the template is already complex; otherwise the template guard alone is sufficient.
* The "No source links available" empty state should be visually low-key — a small grey text span, not a card or alert — so it doesn't draw attention on incident rows where no sources are expected.
* The `reconcile-aircraft-mapping` command should run after `validate-ntsb-links` (from PRD-0022) has completed, so `aircraft_id` resolution happens on a clean, deactivated-links-aware dataset.

## 7. Technical Considerations

* **Dependency on PRD-0022:** The UI guard in requirement 9 depends on broken NTSB sources already being marked `is_active=False`. Run `validate-ntsb-links` before deploying the template change, or the guard will have no effect on NTSB broken links until that job has been run.
* **`resolve_aircraft_for_incident` design:** The method requires only Flask app context and DB session — no importer instance state. However, its step 3 (auto-create) calls `self._log_model_creation()` which is instance-bound. The solution is to extract steps 1–2 into the standalone `resolve_aircraft_for_incident(raw_model_variant: str) -> Optional[int]` function, have the importer method delegate to it, and keep step 3 in the instance method only. The reconcile command calls the standalone function exclusively.
* **WA-coded incidents:** Many of the 23 orphaned MEDIA incidents are likely WA-coded. WA incidents often have `aircraft_id=NULL` because their raw model variant is sparse or non-standard. The reconcile command's failure logs will surface which variants need manual aircraft-row additions.
* **Transaction safety:** The reconcile command must wrap each incident update in a try/except for `IntegrityError` and roll back individual failures without aborting the entire batch.

## 8. Success Metrics

* **Zero new orphans:** After deploying requirement 1, zero new `MEDIA` sources are written with `aircraft_id=NULL` (verifiable by DB query after next enrichment run).
* **Backfill coverage:** `reconcile-aircraft-mapping` resolves `aircraft_id` for at least 50% of the 23 current orphaned incidents (the remainder may have genuinely unresolvable `raw_model_variant` values and will be logged for manual follow-up).
* **Card link accuracy:** A manual spot-check of 10 aircraft card pages shows zero broken "Details" or "NTSB Docs" links after the UI guard and NTSB deactivation job have both been deployed.
* **Article visibility:** At least one aircraft card page that previously showed no press articles now shows a valid MEDIA link as a result of the backfill.

## 9. Open Questions

_All original open questions resolved:_

* **`resolve_aircraft` standalone usage:** The method is safe to call outside an active importer run (it only requires Flask app context and DB session, not importer instance state). However, step 3 auto-creates `Aircraft` rows for Boeing/Airbus and calls `self._log_model_creation()`, which is an instance method. The extracted standalone function (`resolve_aircraft_for_incident`) must skip auto-creation to avoid producing duplicate rows during backfill. Match-only (steps 1 and 2) is the correct behaviour for the reconcile command.
* **Manual aircraft row additions:** Deferred to a future PRD. The `reconcile-aircraft-mapping` command will log all unresolved incidents with their `raw_model_variant` values so they can be addressed manually in the interim.
* **Global incident list scope:** Aircraft card is the only surface that matters for now. `global_incident_list.html` is explicitly out of scope for this PRD.
* **Re-enrichment trigger:** Automatic re-targeting is the intended behaviour — once `reconcile-aircraft-mapping` sets `aircraft_id`, the next `enrich-wa-incidents` run naturally picks up those incidents (they still have no `MEDIA` source). To maximise this, `reconcile-aircraft-mapping` will be added to `scripts/enrich_wa_incidents.sh` to run immediately before `enrich-wa-incidents` in the same daily job (daily at 02:00, via `com.aircraftsafetytracker.wa-enrichment.daily.plist`).
