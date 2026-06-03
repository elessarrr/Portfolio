# Product Requirements Document: 0008 — `/audit-urls` Portable URL Audit Engine (Scaffold + Run)

**Project ID:** 0008  
**Created:** 02 June 2026  
**Author:** Product (with CTO)  
**Status:** Draft — ready for implementation  

---

## 1. Introduction / Overview

### Problem Statement

We have a strong URL audit workflow in **Aircraft Safety Tracker** (liveness → dry-run → retry/merge → review gate → optional DB write-back → optional URL migration). However, `/audit-urls` is currently a **runbook**, not a portable tool:

- In a new repo, `/audit-urls` cannot reliably run because the repo likely lacks an adapter script such as `scripts/audit_faa_aids_urls.py`.
- Product intent: `/audit-urls` should be **generic, portable, and effective** in a brand-new repo.

### Goal

When a user invokes `/audit-urls` in a new repo, it should:

1. **Detect missing audit tooling**
2. **Offer to scaffold** a generic Python audit engine + YAML rules (and a source “adapter” config)
3. **Run the audit** using safe defaults (concurrency 16, timeout 15s, jitter 50–200ms, retry once)
4. **Never modify a DB without explicit confirmation** (ask-before-write policy)

---

## 2. Goals

1. **Portability:** Works in repos that have no pre-existing audit scripts.
2. **Python-only v1:** Engine + rules + CLI implemented in Python.
3. **Config-driven:** Source rules defined primarily via **YAML** (no code required for basic sources).
4. **Three-tier buckets:** `working_brief_report`, `working_search_prefill`, `not_working`.
5. **Safe merges:** Retry/merge output naming avoids clobbering unrelated audit exports.
6. **Human-in-the-loop DB safety:** If DB write-back is supported, the workflow must **ask before writing**.

---

## 3. User Stories

1. **As a** developer in a new repo,  
   **I want** `/audit-urls` to create the missing audit scripts/config automatically,  
   **so that** I can audit thousands of stored URLs without hand-rolling infrastructure.

2. **As a** product owner,  
   **I want** audit outputs to clearly distinguish “HTTP works” vs “product works,”  
   **so that** we don’t ship search-form links as if they were real deep links.

3. **As a** developer,  
   **I want** retry/merge behavior that can’t overwrite unrelated logs,  
   **so that** audits are safe to run repeatedly during investigation.

4. **As a** product owner,  
   **I want** the tool to ask before any DB update,  
   **so that** we never accidentally deactivate thousands of rows during a flaky outage.

---

## 4. Functional Requirements

### FR-1: Detect + scaffold missing tooling (portable entry behavior)

1. **FR-1.1** When invoked, the workflow checks for a generic engine entrypoint:
   - `scripts/audit_urls.py` (primary) and/or
   - `python -m url_audit` (module entrypoint)
2. **FR-1.2** If missing, the workflow offers to scaffold (ask-before-write):
   - `scripts/audit_urls.py`
   - `url_audit/` module (shared engine code)
   - `audit_urls.yaml` (sample config)
   - minimal unit tests
3. **FR-1.3** Scaffolding must be idempotent (re-running does not destroy edits).

### FR-2: YAML rules format (source adapter without code)

1. **FR-2.1** `audit_urls.yaml` supports defining at least:
   - `sources[]`: name, liveness_url, url_mode(s), url_templates (optional), and body markers
   - retryable reasons (e.g. 503/504/timeout/CDN markers)
   - classification markers:
     - brief markers (e.g. `ap_brief`, `factual narrative`)
     - search/intermediate markers (e.g. `search`, `clear search`, known form fields)
2. **FR-2.2** YAML supports a simple “URL list input” mode:
   - audit a JSONL/CSV of URLs without needing DB access

### FR-3: Engine behavior (core audit loop)

1. **FR-3.1** Concurrency defaults to **16** workers.
2. **FR-3.2** Timeout default **15 seconds**.
3. **FR-3.3** Jitter default **50–200ms** before each request (disable flag `--no-jitter`).
4. **FR-3.4** Body read cap default **64KB**.
5. **FR-3.5** Retry once on transient failures by default (disable `--no-retry`).
6. **FR-3.6** Liveness probe required (HTTP 2xx) before bulk audit unless `--skip-liveness`.
7. **FR-3.7** Output JSONL includes at minimum:
   - `url`, `http_status`, `link_viable`, `product_viable`, `bucket`, `reason`, `checked_at`, `url_mode`

### FR-4: Retry + merge behavior (safe by default)

1. **FR-4.1** `--retry-failures-from <jsonl>` re-checks only `bucket=not_working`.
2. **FR-4.2** `--merge-into <jsonl>` merges retry results into a full export.
3. **FR-4.3** If `--merge-into` equals `--retry-failures-from`, the merged output must go to:
   - `{stem}_merged.jsonl` **next to that file**
   - never to a generic/global filename

### FR-5: DB write-back support (optional but supported)

**Decision:** Support write-back via hooks/adapters *or* built-in SQLite mode — whichever is easiest for the target repo. **But always ask before writing.**

1. **FR-5.1** Default behavior is **audit-only** (no DB writes).
2. **FR-5.2** If the user requests DB write-back, the workflow must prompt/confirm:
   - which DB to target
   - which table/fields are updated
   - which buckets map to “active”
3. **FR-5.3** Support at least one write-back mode:
   - **Built-in SQLite mode** (common table schema) OR
   - **Write-back hooks** (repo provides small adapter file)

### FR-6: CLI UX (script + module)

1. **FR-6.1** Support running as:
   - `PYTHONPATH=. python scripts/audit_urls.py ...`
   - `python -m url_audit ...`
2. **FR-6.2** Provide `--config audit_urls.yaml` and flags for concurrency/timeout/jitter/retry.
3. **FR-6.3** Provide `--dry-run` semantics for write-back modes.

---

## 5. Non-Goals (Out of Scope)

1. Multi-language engines (Node/TS) in v1.
2. Playwright/browser automation for bulk audits.
3. Fully automatic DB write-back without asking.
4. Perfect out-of-the-box adapters for every government source (YAML rules must be provided).

---

## 6. Design Considerations

### Buckets and meaning

- `working_brief_report`: primary document page (product OK)
- `working_search_prefill`: intermediate/search UI page (HTTP OK, product not OK)
- `not_working`: broken or empty (CDN error page, 404, timeout, etc.)

### Ask-before-write policy (critical safety)

If a repo has a DB adapter available, the engine can write back — but the workflow must confirm explicitly before any DB mutation.

---

## 7. Technical Considerations

### Proposed file layout (scaffolded)

- `scripts/audit_urls.py` — thin CLI wrapper
- `url_audit/__init__.py`
- `url_audit/engine.py` — concurrency, jitter, retry, JSONL IO
- `url_audit/config.py` — YAML parsing + validation
- `url_audit/classify.py` — marker-based classification
- `url_audit/db_writeback.py` — optional interfaces + sqlite mode
- `audit_urls.yaml` — repo-local source rules
- `tests/test_url_audit_engine.py` — basic unit tests for merge naming, buckets

---

## 8. Success Metrics

1. In a fresh repo with no scripts, user can run scaffold + audit in <10 minutes setup time.
2. Audit outputs include buckets + reasons and can be retried/merged safely.
3. No DB mutations occur without explicit confirmation.
4. At least one new repo can successfully audit a 1k+ URL corpus using YAML-only rules.

---

## 9. Open Questions

1. Should v1 include a built-in SQLite mode, or only hooks?
2. Should YAML support regex rules for “brief” vs “search” detection, or only substring markers?
3. Should we ship a “starter” config template for common sources (NTSB, FAA, etc.)?

