---
title: Compound store smoke test
date: 2026-06-06
category: conventions
module: compound-knowledge
problem_type: convention
component: documentation
severity: low
applies_when:
  - "Validating docs/solutions/ frontmatter parser safety"
tags: [compound, smoke-test, yaml]
---

# Compound store smoke test

## Context

Smoke document created during PRD 0011 implementation to verify the knowledge store and validator.

## Guidance

Run `python3 .compound/scripts/validate-frontmatter.py` on every new solution doc before marking compound capture complete.

## Why This Matters

Unquoted YAML values with ` #` or `: ` silently corrupt frontmatter in strict parsers.

## When to Apply

- After writing or updating any file under `docs/solutions/`

## Examples

```bash
python3 .compound/scripts/validate-frontmatter.py docs/solutions/conventions/compound-store-smoke-test.md
```

## Related

- `Planning/tasks/0011-prd-compound-engineering-knowledge-system.md`
