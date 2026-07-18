---
title: Production SECRET_KEY must fail closed on None/empty/placeholder
date: 2026-07-18
module: app-factory
problem_type: security_issue
component: development_workflow
severity: medium
related_components: [deployment]
tags: [flask, secret-key, production, fail-closed, configuration]
symptoms:
  - "ProductionConfig.SECRET_KEY is None when env var unset, but create_app still boots"
  - "Guard only compared SECRET_KEY == 'you-will-never-guess'"
  - "Comment promised enforcement that None bypassed"
root_cause: incomplete_validation
resolution_type: code_fix
applies_when:
  - "Hardening Flask production config or session signing"
  - "A production guard only checks one known-bad string and ignores None/empty"
---

# Production SECRET_KEY must fail closed on None/empty/placeholder

## Problem

`ProductionConfig` sets `SECRET_KEY = os.environ.get('SECRET_KEY')` with **no fallback**,
so a missing env var yields `None`. The factory only rejected the development placeholder
string (`you-will-never-guess`), so production could boot with `SECRET_KEY=None` —
sessions/CSRF/signing undefined, contrary to the comment that promised enforcement.

Local `default`/`development` still using the public placeholder is intentional for solo
dev; the bug was silent production acceptance of a missing key.

## Resolution

`_assert_secure_production_secret()` in `create_app()` when `config_name == 'production'`:
reject `None`, blank/whitespace, and known placeholders (`you-will-never-guess`,
`.env.example`'s `your-secret-key-here`). TestingConfig uses an explicit test-only key.
`.env.example` documents that production refuses to boot without a real secret.

## Where

- `app/__init__.py` — `_assert_secure_production_secret` / `create_app`
- `config.py` — ProductionConfig (no fallback), TestingConfig explicit key
- `tests/test_secret_key.py`
