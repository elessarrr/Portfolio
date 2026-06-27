# Red/Green TDD Cheat Sheet

Agents follow `.cursor/rules/tdd-red-green.mdc` + `AGENTS.md` automatically. This page is for you.

## The loop

```
Write test → pytest (RED) → implement → pytest (GREEN) → full suite
```

## Commands (AST)

From **`Aircraft Safety Tracker/`** directory:

```bash
# Single file (during TDD)
PYTHONPATH=. pytest tests/test_foo.py -q

# Full suite (before done / commit)
PYTHONPATH=. pytest -q
```

Use the conda/venv Python that has Flask installed if bare `python3` fails imports.

## When TDD applies

| Applies | Skip (`skip TDD`) |
|---------|-------------------|
| New/changed behavior in `app/` or `scripts/` | Docs, PRDs, runbooks, skills |
| Bug fix with regression test | One-line typos |
| Refactor (tests must stay green first) | Spikes / throwaway experiments |

## Task list shape (from generate-tasks prompt)

Each coding feature should have:

1. Write failing test(s)
2. Run pytest — confirm **RED**
3. Implement — confirm **GREEN**
4. Full suite

## Override

Say **`skip TDD`** in Agent chat for that session.

## Related

- `Planning/runbooks/compound-cheat-sheet.md` — compound after non-trivial fixes
- `AGENTS.md` — Core Workflows
