# Compound Knowledge — Global Setup Runbook

**PRD:** `Planning/tasks/0011-prd-compound-engineering-knowledge-system.md`

## What this is

Structured institutional knowledge: `docs/solutions/` (searchable per-problem docs), `CONCEPTS.md` (domain glossary), capture via `/compound`, retrieval via `/learnings-researcher`.

## Global Cursor User Rule

Apply in **Cursor Settings → Rules → User tab** (not project-only — applies to all repos). Copy verbatim:

```markdown
## Agent-enforced compound loop

You MUST run this without the user asking. The human should not memorize these steps.

### Before substantive implement/debug
- Run /learnings-researcher or grep docs/solutions/ frontmatter (module, tags, problem_type, title)
- Read CONCEPTS.md at repo root if present
- If context/ has no snapshot within 2 days, run /context-distillation

### Before ending a non-trivial resolved session
- Run /compound mode:headless (or /ce-compound mode:headless if CE plugin installed)
- Validate: python3 .compound/scripts/validate-frontmatter.py on the new doc
- Append JOURNAL.md (1–2 sentences)
- LEARNINGS.md: link-only bullet for repeat patterns — never duplicate full content

Skip only if user says "skip compound" or change was trivial (typo, one-liner).

### Production code (all repos)
- Red/green TDD: write failing test first, run tests and confirm RED, implement minimal code, confirm GREEN — unless user says "skip TDD" or work is docs-only

Skills: /review (default, not /ce-code-review), /compound-refresh after migrations, /errors-audit-deep quarterly only.

Cheat sheet: Planning/runbooks/compound-cheat-sheet.md (path varies per repo)
```

### Manual checklist

- [x] User Rule pasted in Cursor Settings (**Bhavesh** — Task 3.4)
- [ ] Verified on a second machine if applicable

## New repo bootstrap

```bash
cp -R ~/dev-templates/compound-repo/ ./my-new-project/
cd my-new-project
# Customize AGENTS.md stack section
# Run /context-distillation for first context snapshot
# First non-trivial fix → /compound mode:headless seeds CONCEPTS.md terms
```

## Optional: Compound Engineering plugin

Alternative to custom `/compound` skill:

```
/add-plugin compound-engineering
/ce-setup
```

Use `/ce-compound mode:headless` as alias. Keep gstack `/review` as default review path.

## Review routing

- **Default:** gstack `/review` (SQL safety, LLM trust boundary)
- **Not default:** `/ce-code-review` unless explicitly requested

## Template location

`~/dev-templates/compound-repo/` — scaffold copied from AST `.compound/` + docs structure.

## Cheat sheet

`Planning/runbooks/compound-cheat-sheet.md` — one-page reference for humans; agents use `.cursor/rules/compound-loop.mdc` + AGENTS.md.
