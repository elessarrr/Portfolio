# Compound Cheat Sheet

One page. **You don't run this manually** — agents follow `AGENTS.md` + `.cursor/rules/compound-loop.mdc` + your global User Rule. This doc is for you when you want to understand or override.

**Full setup:** `compound-knowledge-global-setup.md`

---

## The loop (agents run this; you don't memorize it)

```
START substantive work
  → search docs/solutions/ + read CONCEPTS.md
  → do the work
  → if non-trivial fix/review: write docs/solutions/ doc
  → append JOURNAL.md
  → optional LEARNINGS bullet (link only, repeat patterns)
END
```

---

## What lives where

| File | Role |
|------|------|
| `docs/solutions/` | **Canonical** — one doc per learning (searchable) |
| `CONCEPTS.md` | Domain glossary — where things belong |
| `LEARNINGS.md` | Index + one-line proactive bullets (links to solutions) |
| `JOURNAL.md` | What we did today (1–2 sentences) |
| `context/` | Architecture snapshot (periodic, not per-task) |
| `.compound/schema.yaml` | Frontmatter contract |
| `.compound/resolution-template.md` | Bug vs knowledge doc shape |

---

## Skills (agents invoke; you rarely type these)

| Skill | When |
|-------|------|
| `/learnings-researcher [context]` | **Start** of bug/feature work |
| `/compound mode:headless` | **End** of non-trivial fix |
| `/compound-refresh [scope]` | After migration/refactor invalidates old docs |
| `/review` | Before landing PR-sized changes |
| `/context-distillation` | When `context/` snapshot >2 days old |
| `/errors-audit-deep` | Quarterly backfill only |

**Alias:** `/ce-compound mode:headless` if CE plugin installed.

---

## Pilot docs (already in the store)

| Topic | Path |
|-------|------|
| ASIAS liveness gate | `docs/solutions/integration-issues/asias-liveness-gate-false-positive-audit.md` |
| CAROL empty SPA | `docs/solutions/integration-issues/ntsb-carol-empty-spa-shell.md` |
| SQLite single-writer | `docs/solutions/database-issues/sqlite-single-writer-bulk-jobs.md` |
| FAA brief vs search | `docs/solutions/integration-issues/faa-brief-report-vs-search-prefill.md` |
| NTSB dedupe fatalities | `docs/solutions/logic-errors/ntsb-dedupe-fatalities-null-as-zero.md` |

---

## Validator (agents run after every new solution doc)

```bash
python3 .compound/scripts/validate-frontmatter.py docs/solutions/<category>/<file>.md
```

---

## What counts as "non-trivial" (compound required)

- Bug took >15 min or had dead ends
- New convention or pipeline step
- Review surfaced reusable pattern
- Data/schema learning (FAA/NTSB/SQLite pairs)

**Skip compound:** typos, one-line fixes, pure renames with no learning.

---

## Your one-time setup

1. **User Rule** (Cursor Settings → Rules → **User** tab) — paste block from `compound-knowledge-global-setup.md` § "Agent-enforced compound loop"
2. **Project rule** — already at `.cursor/rules/compound-loop.mdc` (always on for this repo)
3. **New repos** — `cp -R ~/dev-templates/compound-repo/ ./new-project/`

---

## Override phrases (when you want control)

| You say | Agent does |
|---------|------------|
| "skip compound this time" | No `/compound` this session |
| "compound only" | Capture only, no new code |
| `/learnings-researcher X` | Read path only, explicit |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Agent didn't search past learnings | Remind: "follow compound-loop rule" or `@.cursor/rules/compound-loop.mdc` |
| Duplicate LEARNINGS prose | Point to canonical doc; trim duplicate; link only |
| Validator fails | Quote YAML values containing `#` or `: ` |
| Stale FAA/NTSB advice after migration | `/compound-refresh faa-aids` |
