## Relevant Files

- `Planning/tasks/prd-0012-prd-asrs-review-followups.md` - Source PRD (multi-model review actions).
- `Planning/tasks/0010-prd-asrs-contributing-factors-layer.md` - Parent ASRS feature PRD.
- `app/ingestion/asrs_aircraft_match.py` - Matcher logic to harden (substring false positives).
- `app/ingestion/asrs_import.py` - Import pipeline; dry-run stats (optional follow-up).
- `app/ingestion/asrs_coverage.py` - Coverage summary for before/after comparison.
- `app/templates/components/asrs_profile_card.html` - Factor % copy / disclaimer.
- `scripts/import_asrs.py` - Remove `db.create_all()`; add table guard.
- `scripts/remap_asrs_aircraft_ids.py` - **New** — recompute `aircraft_id` from stored raw strings (preferred over full HF re-download).
- `scripts/README_asrs_refresh.md` - Document migrate prerequisite + remap workflow.
- `migrations/versions/d4e5f6a7b8c9_add_asrs_report.py` - Existing ASRS migration (one Alembic head).
- `migrations/versions/be4e7bb8751a_add_index_to_incidentsource_source_name.py` - Sibling head to merge.
- `migrations/versions/*_merge_*heads*.py` - **New** — merge migration (single head).
- `tests/test_asrs.py` - Matcher adversarial tests, import guard tests, route/UI assertions.
- `tests/test_asrs_matcher_adversarial.py` - Adversarial matcher tests (Boeing 40/80, A380, tie-break).
- `data/logs/asrs_coverage_summary.json` - Baseline + post-fix coverage artifact.
- `data/config/asrs_make_model_to_aircraft.jsonl` - Overrides for edge cases after matcher fix.
- `docs/solutions/architecture-patterns/asrs-aggregate-layer-dbol-acquisition.md` - Update matcher guidance post-fix.

### Notes

- **Baseline (pre-fix):** Boeing 40 n=881, Boeing 80 n=570 in `asrs_coverage_summary.json` — treat as false-positive fingerprint until remediated.
- **Tests:** `PYTHONPATH=. pytest tests/test_asrs.py -q` from `Aircraft Safety Tracker/` — RED before prod code, GREEN after.
- **Matcher policy (document in code comment):** generic `B737` → prefer rollup `Boeing 737` when no variant digit; ambiguous equal-score ties → `None` (unmatched).
- **Remap vs re-import:** Prefer `remap_asrs_aircraft_ids.py --apply` on existing 47k rows; full HF re-import only if remap insufficient.
- **Alembic:** After merge, verify with `flask db heads` (single head) on dev DB.
- **TDD exempt:** Alembic merge migration file, manual browser spot-check, coverage JSON regeneration.

## Tasks

- [x] 1.0 Matcher hardening — eliminate false positives (critical)
  - [x] 1.1 **RED:** Add `tests/test_asrs_matcher_adversarial.py` (or extend `test_asrs.py`) with multi-aircraft catalog fixture including `Boeing 40`, `Boeing 80`, `Boeing 737`, `Boeing 737-400`, `Boeing 737-800` — assert `B737-400` / `737-400` does **not** match Boeing 40 or Boeing 80
  - [x] 1.2 **RED:** Assert ambiguous tie (two candidates same top score) returns `None`; run `PYTHONPATH=. pytest tests/test_asrs_matcher_adversarial.py -q` — confirm fail
  - [x] 1.3 **GREEN:** Update `asrs_aircraft_match.py` — min `series_key` length ≥4 for substring `in` checks; prefer exact match > longest variant > family-only; return `None` on score ties at top rank
  - [x] 1.4 **GREEN:** Document generic `B737` rollup rule in module docstring; re-run adversarial tests — confirm pass
  - [x] 1.5 **GREEN:** Keep existing `test_match_asrs_make_model` green; run `PYTHONPATH=. pytest tests/test_asrs.py -q`

- [ ] 2.0 Alembic — single migration head (critical deploy)
  - [ ] 2.1 Run `flask db heads` — confirm two heads (`c8f1a2b3d4e5` / `be4e7bb8751a` branch + `d4e5f6a7b8c9`)
  - [ ] 2.2 Add merge migration revising both heads → one revision (e.g. `e5f6a7b8c9d0_merge_incident_source_and_asrs_heads.py`)
  - [ ] 2.3 Verify `flask db upgrade head` on fresh test DB and on existing v3 SQLite copy

- [ ] 3.0 Import script — schema via migrations only (critical deploy)
  - [ ] 3.1 **RED:** Test that `import_asrs` raises clear error when `asrs_report` table missing (mock or temp DB without migration)
  - [ ] 3.2 **RED:** Run pytest — confirm fail
  - [ ] 3.3 **GREEN:** Remove `db.create_all()` from `scripts/import_asrs.py`; add `_require_asrs_table()` guard with actionable message (`flask db upgrade head`)
  - [ ] 3.4 **GREEN:** Update `scripts/README_asrs_refresh.md` — migrate before `--apply`
  - [ ] 3.5 **GREEN:** Re-run import guard tests — confirm pass

- [ ] 4.0 UI copy — honest factor percentages (warning)
  - [ ] 4.1 **RED:** Extend `test_aircraft_page_shows_asrs_card` (or new template test) to assert copy includes “% of reports mentioning” (or equivalent disclaimer text)
  - [ ] 4.2 **RED:** Run pytest — confirm fail
  - [ ] 4.3 **GREEN:** Update `asrs_profile_card.html` — relabel contributing factors section; add note that percentages may sum above 100%
  - [ ] 4.4 **GREEN:** Re-run test — confirm pass

- [ ] 5.0 Data remediation — remap aircraft_id + refresh coverage (required after 1.0)
  - [ ] 5.1 **GREEN:** Add `scripts/remap_asrs_aircraft_ids.py` — `--dry-run` / `--apply`; recompute `aircraft_id` from `aircraft_make_model_raw` using fixed matcher; log changed / cleared / unchanged counts
  - [ ] 5.2 **RED:** Test remap on small in-memory DB with intentionally wrong assignments (Boeing 40 row with raw `B737-400`)
  - [ ] 5.3 **GREEN:** Implement remap logic; confirm test pass
  - [ ] 5.4 Run `remap_asrs_aircraft_ids.py --apply` on local v3 DB; then `scripts/export_asrs_coverage.py`
  - [ ] 5.5 **Acceptance:** Boeing 40 / Boeing 80 `n` drop to plausible levels; top models (737-800, A320) stable or increased; save updated `data/logs/asrs_coverage_summary.json`
  - [ ] 5.6 Manual spot-check: Boeing 737-800 and Airbus A320 aircraft pages — card visible, `n=` credible, factor bars render

- [ ] 6.0 Sign-off — docs + full test suite
  - [ ] 6.1 Update `docs/solutions/architecture-patterns/asrs-aggregate-layer-dbol-acquisition.md` — matcher rules + remap workflow
  - [ ] 6.2 Append JOURNAL entry with before/after coverage counts
  - [ ] 6.3 Run `PYTHONPATH=. pytest -q` — all green
  - [ ] 6.4 Mark PRD 0012 / review follow-ups complete in task list
