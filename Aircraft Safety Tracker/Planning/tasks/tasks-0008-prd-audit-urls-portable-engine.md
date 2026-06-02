# Task List: PRD 0008 — `/audit-urls` Portable URL Audit Engine (Scaffold + Run)

**PRD Reference:** `Planning/tasks/0008-prd-audit-urls-portable-engine.md`  
**Target:** Python-only v1, config-driven via `audit_urls.yaml`  

---

## Relevant Files

### New files to create (scaffold targets)
- `scripts/audit_urls.py` — Thin CLI wrapper to run the engine (FR-1, FR-6).
- `audit_urls.yaml` — Repo-local YAML config for sources and markers (FR-2).
- `url_audit/__init__.py` — Module entrypoint for `python -m url_audit` (FR-6.1).
- `url_audit/__main__.py` — Implements `python -m url_audit ...` CLI (FR-6.1).
- `url_audit/config.py` — YAML parsing + validation (FR-2).
- `url_audit/engine.py` — Core loop: liveness, concurrency, jitter, retry, JSONL IO (FR-3).
- `url_audit/classify.py` — Marker-based classification to buckets/reasons (FR-3.7).
- `url_audit/merge.py` — Retry/merge logic + safe output naming (FR-4).
- `url_audit/io.py` — JSONL/CSV input reading + JSONL output writing (FR-2.2, FR-3.7).
- `url_audit/http.py` — Fetcher: timeout, body cap (64KB), UA header, retry-on-transient (FR-3.2–FR-3.5).
- `url_audit/db_writeback.py` — Optional write-back interface + at least one implementation (FR-5).

### New tests to create
- `tests/test_url_audit_config.py` — YAML schema validation + error messages (FR-2).
- `tests/test_url_audit_merge.py` — Merge naming rules, no clobber (FR-4.3).
- `tests/test_url_audit_classify.py` — Bucket classification from markers + status codes (FR-3.7).
- `tests/test_url_audit_engine.py` — Liveness gate behavior + output schema smoke (FR-3, FR-6).

### Existing files to reference (do not change)
- `scripts/audit_faa_aids_urls.py` — Current repo-specific audit CLI; use as behavioral reference only.
- `app/ingestion/url_builders/faa_aids_viability.py` — Marker-based viability style; reference only.
- `.cursor/skills/audit-urls/SKILL.md` — Runbook semantics that the portable tool must encode.

### Notes
- **Ask-before-write** must be enforced for any DB mutation path (FR-5.2).
- Default workflow must be **audit-only** unless user explicitly enables write-back (FR-5.1).
- Default performance knobs: concurrency 16, timeout 15s, jitter 50–200ms, retry once, body cap 64KB (FR-3).

---

## Tasks

- [x] 1.0 Detect + scaffold missing tooling (idempotent, ask-before-write)
  - [x] 1.1 Implement detection: check for `scripts/audit_urls.py` and/or `python -m url_audit` importability (FR-1.1).
  - [x] 1.2 Implement scaffolding generator that creates: `scripts/audit_urls.py`, `url_audit/`, `audit_urls.yaml`, and minimal tests (FR-1.2).
  - [x] 1.3 Enforce **ask-before-write** for scaffolding (do not create files without explicit confirmation) (FR-1.2).
  - [x] 1.4 Ensure scaffolding is **idempotent**:
    - If a target file exists, do not overwrite it by default.
    - Print a clear “already exists, skipping” message for each file (FR-1.3).
  - [x] 1.5 Add a “scaffold-only” mode (e.g., `--scaffold-only`) that creates files but does not run an audit.

- [ ] 2.0 YAML rules format + validation (config-driven adapter)
  - [ ] 2.1 Define the `audit_urls.yaml` schema:
    - `sources[]`: `name`, `liveness_url`, `url_modes[]` (at least `brief`, `search`), optional `url_templates[]`.
    - Marker lists: `brief_markers[]`, `search_markers[]`, `not_working_markers[]` (or equivalent).
    - Retryable status codes and body markers (e.g. 503/504, CDN error) (FR-2.1).
  - [ ] 2.2 Implement `url_audit/config.py` YAML parser + validator using PyYAML:
    - Fail fast with actionable error messages for missing keys, wrong types, empty lists (FR-2).
    - Validate every `source.name` is unique.
  - [ ] 2.3 Implement `--config audit_urls.yaml` defaulting to repo root `audit_urls.yaml` (FR-6.2).
  - [ ] 2.4 Add support for “URL list input mode”:
    - Accept `--input <jsonl|csv>` and interpret as list of `url` + optional metadata fields (FR-2.2).
    - Allow selecting source + mode via flags (e.g. `--source FAA_ASIAS --url-mode brief`) even in list-input mode.
  - [ ] 2.5 Add unit tests in `tests/test_url_audit_config.py` for valid config, invalid config, and clear error messages.

- [ ] 3.0 Core audit engine (liveness + concurrency + retry + output schema)
  - [ ] 3.1 Implement HTTP fetcher in `url_audit/http.py`:
    - Timeout default 15s (override `--timeout`) (FR-3.2).
    - Body cap 64KB (FR-3.4).
    - User-Agent header default (configurable).
    - Follow redirects to final URL.
  - [ ] 3.2 Implement jitter in `url_audit/engine.py`:
    - Default 50–200ms, disable via `--no-jitter` (FR-3.3).
  - [ ] 3.3 Implement retry-on-transient once by default (disable via `--no-retry`) (FR-3.5).
  - [ ] 3.4 Implement required liveness probe (FR-3.6):
    - Fetch `liveness_url`, require HTTP 2xx.
    - If not 2xx, abort before bulk audit unless `--skip-liveness` is set.
  - [ ] 3.5 Implement concurrency default 16 via `ThreadPoolExecutor` (override `--concurrency`) (FR-3.1).
  - [ ] 3.6 Implement classification in `url_audit/classify.py`:
    - Compute `link_viable`, `product_viable`, `bucket`, `reason` using HTTP status + body markers.
    - Must support the 3 buckets: `working_brief_report`, `working_search_prefill`, `not_working` (FR-3.7, FR-6).
  - [ ] 3.7 Implement JSONL output rows (FR-3.7):
    - Required fields: `url`, `http_status`, `link_viable`, `product_viable`, `bucket`, `reason`, `checked_at`, `url_mode`.
    - Preserve any input metadata fields where possible (e.g. `source_record_id` if provided in input).
  - [ ] 3.8 Add a basic engine test in `tests/test_url_audit_engine.py` with a stubbed fetcher to verify:
    - Liveness abort behavior.
    - Output schema includes all required fields.

- [ ] 4.0 Retry + merge behavior (safe by default)
  - [ ] 4.1 Implement `--retry-failures-from <jsonl>`:
    - Load prior results, filter to `bucket=not_working`, re-check only those (FR-4.1).
  - [ ] 4.2 Implement `--merge-into <jsonl>`:
    - Merge new results into a full export, matching by `url` (and optionally `url_mode`) (FR-4.2).
  - [ ] 4.3 Enforce safe merge naming (FR-4.3):
    - If `--merge-into` equals `--retry-failures-from`, write to `{stem}_merged.jsonl` **next to that file**.
    - Never overwrite input files by default.
  - [ ] 4.4 Add `tests/test_url_audit_merge.py` to lock in the merge naming + no-clobber guarantees.

- [ ] 5.0 Optional DB write-back (ask-before-write, dry-run semantics)
  - [ ] 5.1 Decide and implement **one** supported write-back path for v1 (FR-5.3):
    - Option A: built-in SQLite mode targeting a simple schema, OR
    - Option B: hooks/adapters (repo provides a small adapter module).
  - [ ] 5.2 Implement `--write-back` as opt-in; default is audit-only (FR-5.1).
  - [ ] 5.3 Implement ask-before-write policy (FR-5.2):
    - Prompt must include: DB target, table, fields, bucket→active mapping.
    - Abort if user does not confirm.
  - [ ] 5.4 Implement `--dry-run` semantics for write-back (FR-6.3): generate a change plan and counters, do not write.
  - [ ] 5.5 Add unit tests for “write-back requires confirmation” and “dry-run performs zero writes” using a temporary SQLite DB.

- [ ] 6.0 CLI UX + module entrypoints
  - [ ] 6.1 Implement `scripts/audit_urls.py` as a thin wrapper around `python -m url_audit` (FR-6.1).
  - [ ] 6.2 Implement `url_audit/__main__.py` with argparse supporting:
    - `--config`, `--input`, `--concurrency`, `--timeout`, `--no-jitter`, `--no-retry`, `--skip-liveness`
    - `--retry-failures-from`, `--merge-into`
    - optional `--write-back`, `--dry-run` (FR-6.2–FR-6.3).
  - [ ] 6.3 Add `--help` text that explains the three-tier buckets and the liveness gate briefly.
  - [ ] 6.4 Run full test suite (`PYTHONPATH=. pytest -q`) and ensure all existing repo tests remain green.

