---
title: pg_trgm was enabled but /search was plain ILIKE — wire similarity + GIN index
date: 2026-07-17
module: search
problem_type: logic_error
component: development_workflow
severity: medium
related_components: [database]
tags: [pg_trgm, search, ilike, gin-index, flask, postgres, fail-soft]
symptoms:
  - "Docs claim fuzzy / trigram search is shipped, but /search uses ILIKE '%query%'"
  - "CREATE EXTENSION pg_trgm exists in a migration, but no GIN index and no similarity() call"
  - "Typo queries like 'boieng' return zero results despite Boeing 737 existing"
root_cause: incomplete_implementation
resolution_type: code_fix
applies_when:
  - "An extension or library is migrated/imported but the call site still uses the naive path"
  - "Wiring Postgres-only features while the default test suite runs on SQLite"
---

# pg_trgm was enabled but /search was plain ILIKE

## Problem

Migration `7272cefb04d4` enabled `pg_trgm` on Postgres, and project docs described fuzzy
search as shipped. The live `/search` route was still:

```python
Aircraft.query.filter(Aircraft.model_name.ilike(f'%{query}%'))
```

No GIN index, no `similarity()` call. `thefuzz` was imported in `routes.py` but unused —
real fuzzy matching lived only in the offline NTSB↔ASN dedupe pipeline. Typo queries
(`boieng`) returned empty results.

## Resolution

1. **GIN index migration** `c3d4e5f6a7b8` — dialect-guarded
   `CREATE INDEX ... USING gin (model_name gin_trgm_ops)` (no-op on SQLite).
2. **`_search_aircraft()`** on Postgres uses
   `greatest(similarity(model_name, q), word_similarity(q, model_name)) >= 0.2`
   OR substring `ILIKE`, ordered by similarity desc. Threshold tuned empirically:
   `similarity('Boeing 737','boieng') == 0.2` (default 0.3 misses real typos).
3. **Fail-soft:** any trigram error → `rollback()` + ILIKE fallback so search never 500s.
4. **Tests:** SQLite suite keeps the ILIKE path + a mocked fail-soft test; Postgres-gated
   test (`AST_FUZZY_TEST_DATABASE_URL`) asserts `q=boieng` returns Boeing 737. Patch
   `TestingConfig.SQLALCHEMY_DATABASE_URI` *before* `create_app` — a late
   `app.config[...]` override does not rebind Flask-SQLAlchemy's engine.

## Where

- `app/routes.py` (`_search_aircraft`)
- `migrations/versions/c3d4e5f6a7b8_add_trgm_index_aircraft_model_name.py`
- `tests/test_routes.py`
