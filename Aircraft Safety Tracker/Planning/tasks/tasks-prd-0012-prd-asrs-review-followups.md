## Relevant Files

- `Planning/tasks/prd-0012-prd-asrs-review-followups.md` - Source PRD (multi-model review actions).
- `Planning/tasks/0010-prd-asrs-contributing-factors-layer.md` - Parent ASRS feature PRD.
- `app/ingestion/asrs_aircraft_match.py` - Matcher logic hardened (substring min length, tie-break).
- `app/ingestion/asrs_import.py` - Import pipeline; `require_asrs_table()` guard.
- `app/ingestion/asrs_remap.py` - Remap `aircraft_id` from stored raw strings after matcher fix.
- `app/ingestion/asrs_coverage.py` - Coverage summary for before/after comparison.
- `app/templates/components/asrs_profile_card.html` - Factor % copy / disclaimer.
- `scripts/import_asrs.py` - Migration guard; no `db.create_all()`.
- `scripts/remap_asrs_aircraft_ids.py` - CLI for `--dry-run` / `--apply` remap.
- `scripts/README_asrs_refresh.md` - Migrate prerequisite + remap workflow.
- `migrations/versions/d4e5f6a7b8c9_add_asrs_report.py` - ASRS table migration.
- `migrations/versions/be4e7bb8751a_add_index_to_incidentsource_source_name.py` - Sibling head (merged).
- `migrations/versions/e5f6a7b8c9d0_merge_incident_source_and_asrs_heads.py` - Merge migration (single head).
- `tests/test_asrs.py` - Import guard, remap, route/UI assertions.
- `tests/test_asrs_matcher_adversarial.py` - Adversarial matcher tests (Boeing 40/80, A380, tie-break).
- `data/logs/asrs_coverage_summary.json` - Post-remap coverage (matched 13,544; Boeing 40/80 removed).
- `data/config/asrs_make_model_to_aircraft.jsonl` - Overrides for edge cases after matcher fix.
- `docs/solutions/architecture-patterns/asrs-aggregate-layer-dbol-acquisition.md` - Matcher rules + remap workflow.

### Notes

- **Post-fix coverage:** matched_rows 13,544 (was 17,226); 3,682 false positives cleared; Boeing 40/80 gone; 737-800/A320 stable.
- **Tests:** `PYTHONPATH=. pytest -q` — 172 green at sign-off.
- **Matcher policy:** generic `B737` → family rollup; ambiguous equal-score ties → `None`.
- **Remap:** `scripts/remap_asrs_aircraft_ids.py --apply` on existing rows; no HF re-download needed.
- **Alembic:** single head `e5f6a7b8c9d0`; run `flask db upgrade head` before import.

## Tasks

- [x] 1.0 Matcher hardening — eliminate false positives (critical)
  - [x] 1.1 **RED:** Add `tests/test_asrs_matcher_adversarial.py` (or extend `test_asrs.py`) with multi-aircraft catalog fixture including `Boeing 40`, `Boeing 80`, `Boeing 737`, `Boeing 737-400`, `Boeing 737-800` — assert `B737-400` / `737-400` does **not** match Boeing 40 or Boeing 80
  - [x] 1.2 **RED:** Assert ambiguous tie (two candidates same top score) returns `None`; run `PYTHONPATH=. pytest tests/test_asrs_matcher_adversarial.py -q` — confirm fail
  - [x] 1.3 **GREEN:** Update `asrs_aircraft_match.py` — min `series_key` length ≥4 for substring `in` checks; prefer exact match > longest variant > family-only; return `None` on score ties at top rank
  - [x] 1.4 **GREEN:** Document generic `B737` rollup rule in module docstring; re-run adversarial tests — confirm pass
  - [x] 1.5 **GREEN:** Keep existing `test_match_asrs_make_model` green; run `PYTHONPATH=. pytest tests/test_asrs.py -q`

- [x] 2.0 Alembic — single migration head (critical deploy)
  - [x] 2.1 Run `flask db heads` — confirm two heads (`c8f1a2b3d4e5` / `be4e7bb8751a` branch + `d4e5f6a7b8c9`)
  - [x] 2.2 Add merge migration revising both heads → one revision (e.g. `e5f6a7b8c9d0_merge_incident_source_and_asrs_heads.py`)
  - [x] 2.3 Verify `flask db upgrade head` on fresh test DB and on existing v3 SQLite copy

- [x] 3.0 Import script — schema via migrations only (critical deploy)
  - [x] 3.1 **RED:** Test that `import_asrs` raises clear error when `asrs_report` table missing (mock or temp DB without migration)
  - [x] 3.2 **RED:** Run pytest — confirm fail
  - [x] 3.3 **GREEN:** Remove `db.create_all()` from `scripts/import_asrs.py`; add `_require_asrs_table()` guard with actionable message (`flask db upgrade head`)
  - [x] 3.4 **GREEN:** Update `scripts/README_asrs_refresh.md` — migrate before `--apply`
  - [x] 3.5 **GREEN:** Re-run import guard tests — confirm pass

- [x] 4.0 UI copy — honest factor percentages (warning)
  - [x] 4.1 **RED:** Extend `test_aircraft_page_shows_asrs_card` (or new template test) to assert copy includes “% of reports mentioning” (or equivalent disclaimer text)
  - [x] 4.2 **RED:** Run pytest — confirm fail
  - [x] 4.3 **GREEN:** Update `asrs_profile_card.html` — relabel contributing factors section; add note that percentages may sum above 100%
  - [x] 4.4 **GREEN:** Re-run test — confirm pass

- [x] 5.0 Data remediation — remap aircraft_id + refresh coverage (required after 1.0)
  - [x] 5.1 **GREEN:** Add `scripts/remap_asrs_aircraft_ids.py` — `--dry-run` / `--apply`; recompute `aircraft_id` from `aircraft_make_model_raw` using fixed matcher; log changed / cleared / unchanged counts
  - [x] 5.2 **RED:** Test remap on small in-memory DB with intentionally wrong assignments (Boeing 40 row with raw `B737-400`)
  - [x] 5.3 **GREEN:** Implement remap logic; confirm test pass
  - [x] 5.4 Run `remap_asrs_aircraft_ids.py --apply` on local v3 DB; then `scripts/export_asrs_coverage.py`
  - [x] 5.5 **Acceptance:** Boeing 40 / Boeing 80 `n` drop to plausible levels; top models (737-800, A320) stable or increased; save updated `data/logs/asrs_coverage_summary.json`
  - [x] 5.6 Manual spot-check: Boeing 737-800 and Airbus A320 aircraft pages — card visible, `n=` credible, factor bars render

- [x] 6.0 Sign-off — docs + full test suite
  - [x] 6.1 Update `docs/solutions/architecture-patterns/asrs-aggregate-layer-dbol-acquisition.md` — matcher rules + remap workflow
  - [x] 6.2 Append JOURNAL entry with before/after coverage counts
  - [x] 6.3 Run `PYTHONPATH=. pytest -q` — all green
  - [x] 6.4 Mark PRD 0012 / review follow-ups complete in task list
