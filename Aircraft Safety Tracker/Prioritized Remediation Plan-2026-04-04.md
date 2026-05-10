# Prioritized Remediation Plan

**Version Date:** 2026-04-04  
**Status:** Active Master Execution Document  
**Scope:** Security, performance, scalability, reliability, and engineering quality remediation for Aircraft Safety Tracker

## Execution Notes
- Owners are role-based and can be mapped to individuals during sprint planning.
- Estimated completion time is calendar time from task start under normal team capacity.
- Dependencies must be completed or explicitly waived before marking a task done.
- Completion status uses checkbox tracking in the table.

## Priority: Critical

| Done | Task ID | Task Description | Assigned Owner | Estimated Completion Time | Dependencies |
|---|---|---|---|---|---|
| [ ] | C-01 | Add request body limits (`MAX_CONTENT_LENGTH`) and endpoint-level payload validation for `/api/analyze-report` to prevent abuse and memory pressure. | Backend Engineer | 1 day | None |
| [ ] | C-02 | Enforce strict rate-limiting policy for AI analysis endpoint with shared backend semantics and per-client burst caps. | Backend Engineer | 1 day | C-01 |
| [ ] | C-03 | Add regression tests for oversize payloads, malformed JSON, and rapid request bursts (expect 413/429). | QA Engineer | 1 day | C-01, C-02 |
| [ ] | C-04 | Add production safeguards for Flask startup path to avoid runtime schema mutation failures under multi-worker boot. | Platform Engineer | 1 day | None |

## Priority: High

| Done | Task ID | Task Description | Assigned Owner | Estimated Completion Time | Dependencies |
|---|---|---|---|---|---|
| [ ] | H-01 | Replace daemon-thread summary generation with durable background jobs (RQ/Celery) and retry semantics. | Backend Engineer | 4 days | C-01, C-02 |
| [ ] | H-02 | Provision Redis for caching/rate limiting/job queue backend and wire environment-specific configuration. | Platform Engineer | 2 days | H-01 |
| [ ] | H-03 | Migrate production storage from SQLite to PostgreSQL with migration runbook and rollback plan. | Platform Engineer | 4 days | C-04 |
| [ ] | H-04 | Create end-to-end job reliability tests (worker restart, retry, idempotency, stale-job cleanup). | QA Engineer | 2 days | H-01, H-02 |
| [ ] | H-05 | Define and deploy production observability dashboards for queue depth, task failures, p95 endpoint latency, and DB lock/error rates. | Platform Engineer | 2 days | H-01, H-02, H-03 |

## Priority: Medium

| Done | Task ID | Task Description | Assigned Owner | Estimated Completion Time | Dependencies |
|---|---|---|---|---|---|
| [ ] | M-01 | Refactor global incident chart computation to SQL aggregate queries to avoid full in-memory scans for large filters. | Backend Engineer | 2 days | H-03 |
| [ ] | M-02 | Optimize CSV export relationship loading strategy to reduce N+1 query overhead while preserving dynamic relationship behavior. | Backend Engineer | 2 days | H-03 |
| [ ] | M-03 | Expand automated tests for `DeepSeekService` and analyzer failure paths (timeouts, provider errors, malformed AI output). | QA Engineer | 2 days | C-03 |
| [ ] | M-04 | Add CI quality gates for linting/type checks (`ruff`, `mypy`) with baseline configuration and progressive enforcement. | Platform Engineer | 2 days | None |
| [ ] | M-05 | Align README and runbooks with current ingestion/AI architecture and deprecate outdated setup paths. | Tech Lead | 1 day | H-01, H-03 |

## Priority: Low

| Done | Task ID | Task Description | Assigned Owner | Estimated Completion Time | Dependencies |
|---|---|---|---|---|---|
| [ ] | L-01 | Introduce targeted type hints in core services and ingestion modules to improve maintainability and static analysis quality. | Backend Engineer | 3 days | M-04 |
| [ ] | L-02 | Add architecture decision records (ADRs) for background jobs, cache backend, and database strategy. | Tech Lead | 1 day | H-01, H-02, H-03 |
| [ ] | L-03 | Standardize code style and module documentation conventions across routes/services/ingestion packages. | Tech Lead | 2 days | M-04 |

## Tracking Checklist by Milestone

### Milestone 1: Security Stabilization
- [ ] Complete all Critical tasks (C-01 through C-04).
- [ ] Confirm 413/429 controls in staging with automated tests and manual validation.
- [ ] Sign off on endpoint abuse-resistance acceptance criteria.

### Milestone 2: Reliability and Scale Foundation
- [ ] Complete all High tasks (H-01 through H-05).
- [ ] Validate durable job execution across deploy/restart scenarios.
- [ ] Validate Redis-backed shared rate limiting and caching behavior across multiple workers.
- [ ] Validate PostgreSQL migration and rollback in staging.

### Milestone 3: Efficiency and Engineering Quality
- [ ] Complete all Medium tasks (M-01 through M-05).
- [ ] Confirm measurable reduction in query counts and endpoint latency for incident analytics/export paths.
- [ ] Enable CI quality gates with agreed failure policy.

### Milestone 4: Long-Term Maintainability
- [ ] Complete all Low tasks (L-01 through L-03).
- [ ] Confirm architectural docs and standards are discoverable and adopted by the team.

## Success Metrics

| Area | Metric | Target |
|---|---|---|
| API Abuse Resistance | Oversized analyze payload requests rejected | 100% rejected with 413 |
| Rate Limiting | Analyze endpoint burst overflow blocked | 100% overflow blocked with 429 |
| Reliability | Background summary tasks lost during deploy/restart | 0 lost tasks |
| Scalability | Multi-worker cache/rate-limit consistency | No cross-worker bypass observed |
| Database Stability | SQLite lock incidents in production path | 0 (post PostgreSQL migration) |
| Performance | p95 latency for `/incidents` and export paths | ≥30% improvement from baseline |
| Test Quality | AI service and analyzer branch coverage | ≥85% module coverage |
| Engineering Hygiene | CI lint/type check pass rate on main | 100% passing |

## Update Protocol
- Update task status by checking the `Done` column item (`[ ]` → `[x]`) as work completes.
- Record date, owner, and relevant PR/commit in sprint notes when closing each task.
- Re-prioritize only in a weekly remediation review led by Tech Lead and Platform Engineer.
