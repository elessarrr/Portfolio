---
title: SQLite single-writer constraint during bulk ingestion jobs
date: 2026-05-27
category: database-issues
module: ingestion-core
problem_type: database_issue
component: sqlite_db
symptoms:
  - "database is locked errors during parallel reads/writes"
  - "Corruption risk or hung bulk import when second process touches same .db"
  - "Flask dev server concurrent requests during backfill"
root_cause: thread_violation
resolution_type: workflow_improvement
severity: high
tags: [sqlite, single-writer, bulk-import, concurrency]
---

# SQLite single-writer constraint during bulk ingestion jobs

## Problem

SQLite allows only one writer at a time. Concurrent access during long bulk jobs causes lock errors, failed writes, or unpredictable partial state.

## Symptoms

- `database is locked` during FAA backfill (~25 min) or NTSB full link audit (~35–40 min)
- Second Flask instance, manual `sqlite3` CLI, or pytest touching same DB during bulk write

## What Didn't Work

- Running audit HTTP workers with DB writes from multiple threads without batching on main thread (FAA audit pattern: workers return tuples, main thread writes in batches of 500 — that part is OK)
- Starting Flask on same `data/aircraft_safety_v3.db` during bulk import

## Solution

**Operational rule:** one writer process per DB file during bulk jobs.

- Do not run concurrent `sqlite3` reads or second Flask/backfill against `data/*.db`
- FAA audit: ThreadPoolExecutor for HTTP only; DB writes on main thread in batches
- Schedule long jobs when dev server is stopped or on clone DB

## Why This Works

SQLite write lock is process-wide; parallel writers block or fail regardless of ORM layer.

## Prevention

- Document expected job duration in PRDs (FAA ~25 min, NTSB audit ~35–40 min)
- Use `--dry-run` and clone DB for pilot imports
- `DevelopmentConfig` points at v3 DB — do not mix v2 `aircraft_safety.db` by mistake

## Related Issues

- `LEARNINGS.md` proactive bullet (linked)
- PRD 0007 FAA bulk import
