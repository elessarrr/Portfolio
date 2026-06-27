# Task List — PRD 0011: Compound Engineering Knowledge System

**Source PRD:** `Planning/tasks/0011-prd-compound-engineering-knowledge-system.md`  
**Created:** 2026-06-06  
**Status:** Complete (pending manual User Rule — Task 3.4)  
**Depends on:** Nothing (greenfield infra within AST repo + global Cursor skills)

## Current State Assessment

| Asset | Status |
|-------|--------|
| `docs/solutions/` | **Done** — categories + 6 solution docs (5 pilot + smoke) |
| `CONCEPTS.md` | **Done** — 10 seeded terms |
| `.compound/` | **Done** — schema, template, validator |
| `AGENTS.md` compound discoverability | **Done** |
| `~/.cursor/skills/learnings-researcher/` | **Done** |
| `.cursor/skills/compound/` | **Done** — symlink to gstack |
| `Planning/runbooks/` | **Done** |
| `~/dev-templates/compound-repo/` | **Done** |

---

## Relevant Files

### New — AST repo

- `docs/solutions/README.md` — Store index
- `docs/solutions/conventions/compound-store-smoke-test.md` — Validator smoke doc
- `docs/solutions/integration-issues/asias-liveness-gate-false-positive-audit.md` — Pilot 1
- `docs/solutions/integration-issues/ntsb-carol-empty-spa-shell.md` — Pilot 2
- `docs/solutions/database-issues/sqlite-single-writer-bulk-jobs.md` — Pilot 3
- `docs/solutions/integration-issues/faa-brief-report-vs-search-prefill.md` — Pilot 4
- `docs/solutions/logic-errors/ntsb-dedupe-fatalities-null-as-zero.md` — Pilot 5
- `CONCEPTS.md` — Domain glossary
- `.compound/schema.yaml` — Frontmatter contract
- `.compound/resolution-template.md` — Bug/knowledge templates
- `.compound/scripts/validate-frontmatter.py` — Parser-safety validator (Py3.8 fix)
- `Planning/runbooks/compound-knowledge-global-setup.md` — Global setup runbook
- `.claude/gstack/compound/SKILL.md.tmpl` + `SKILL.md` — Capture skill
- `.claude/gstack/compound-refresh/SKILL.md.tmpl` + `SKILL.md` — Refresh skill
- `tests/test_compound_validate_frontmatter.py` — Validator tests

### New — Global

- `~/.cursor/skills/learnings-researcher/SKILL.md` — Read-path skill
- `~/dev-templates/compound-repo/` — Repo template

### Modified

- `AGENTS.md` — Compound read/write + skills list
- `LEARNINGS.md` — Proactive prevention links to pilot docs
- `JOURNAL.md` — Implementation entries
- `tests/test_faa_aids_importer.py` — Page-18 assertion (LEARNINGS §51 fix)
- `.claude/gstack/plan-eng-review/SKILL.md.tmpl` + `SKILL.md` — Learnings search step
- `.claude/gstack/review/SKILL.md.tmpl` + `SKILL.md` — Compound recommendation step
- `.claude/gstack/scripts/gen-skill-docs.ts` — compound skill templates registered
- `~/.cursor/skills/context-distillation/SKILL.md` — Complements docs/solutions note
- `~/.cursor/skills/errors-audit-deep/SKILL.md` — Backfill → docs/solutions
- `.cursor/skills/compound` + `compound-refresh` — Symlinks

---

## Tasks

- [x] 1.0 Phase 1 — Knowledge store structure (AST repo)
  - [x] 1.1 Create `docs/solutions/` category subdirectories
  - [x] 1.2 Fork CE `schema.yaml` → `.compound/schema.yaml`
  - [x] 1.3 Fork resolution template
  - [x] 1.4 Fork validate-frontmatter.py (Py3.8 `from __future__ import annotations`)
  - [x] 1.5 Add validator unit tests
  - [x] 1.6 Write `docs/solutions/README.md`
  - [x] 1.7 Smoke test doc at `conventions/compound-store-smoke-test.md`

- [x] 2.0 Phase 1 — CONCEPTS.md + AGENTS.md discoverability
  - [x] 2.1 Create `CONCEPTS.md` with preamble
  - [x] 2.2 Seed 10 AST glossary entries
  - [x] 2.3 Update AGENTS.md discoverability lines
  - [x] 2.4 Update AGENTS.md compound write rules
  - [x] 2.5 Update AGENTS.md compound read rule
  - [x] 2.6 Add compound skills to Available Skills

- [x] 3.0 Phase 1 — Global setup (runbook + repo template + User Rule)
  - [x] 3.1 Create `Planning/runbooks/compound-knowledge-global-setup.md`
  - [x] 3.2 Create `~/dev-templates/compound-repo/` scaffold
  - [x] 3.3 Copy `.compound/` into template
  - [ ] 3.4 **Manual (Bhavesh):** Apply global User Rule in Cursor Settings — see runbook
  - [x] 3.5 Document template copy workflow in runbook

- [x] 4.0 Phase 2 — Read path (`learnings-researcher` + skill integrations)
  - [x] 4.1 Create `~/.cursor/skills/learnings-researcher/SKILL.md`
  - [x] 4.2 Invocation triggers in skill doc
  - [x] 4.3 Update context-distillation skill
  - [x] 4.4 Edit plan-eng-review tmpl (Step 0.5)
  - [x] 4.5 Run gen:skill-docs
  - [x] 4.6 Agent-verified: grep path documented; manual `/learnings-researcher` smoke optional

- [x] 5.0 Phase 3 — Write path (`compound` + `compound-refresh` skills)
  - [x] 5.1 Create compound SKILL.md.tmpl
  - [x] 5.2 References to `.compound/` paths in skill
  - [x] 5.3 Create compound-refresh SKILL.md.tmpl
  - [x] 5.4 Run gen:skill-docs
  - [x] 5.5 Symlink compound + compound-refresh in `.cursor/skills/`
  - [x] 5.6 Agent-verified: pilot docs + validator pass; manual `/compound mode:headless` optional

- [x] 6.0 Phase 3 — Integrate existing skills (errors-audit-deep + review)
  - [x] 6.1 Update errors-audit-deep for docs/solutions backfill
  - [x] 6.2 Frontmatter guidance in output contract
  - [x] 6.3 Edit review tmpl (Step 6 compound recommendation)
  - [x] 6.4 Run gen:skill-docs
  - [x] 6.5 gstack `/review` default confirmed in runbook + AGENTS.md

- [x] 7.0 Phase 4 — AST pilot migration (5 learnings)
  - [x] 7.1 Extract from LEARNINGS.md
  - [x] 7.2 ASIAS liveness doc
  - [x] 7.3 CAROL empty SPA doc
  - [x] 7.4 SQLite single-writer doc
  - [x] 7.5 FAA brief vs search doc
  - [x] 7.6 Dedupe fatalities doc
  - [x] 7.7 Validator exit 0 on all five + smoke doc
  - [x] 7.8 LEARNINGS proactive links added
  - [x] 7.9 Index note at top of Proactive Prevention (full § trim deferred)

- [x] 8.0 Phase 4 — Pilot validation + sign-off
  - [x] 8.1 pytest: **157 passed**
  - [x] 8.2 Pilot: implementation session used CONCEPTS.md + cross-linked solution docs
  - [x] 8.3 Acceptance checklist — see PRD §11 (3.4 pending user)
  - [x] 8.4 JOURNAL entry appended
  - [x] 8.5 FAA pilot docs reviewed; page-12 guidance consolidated in brief-vs-search doc

---

## Acceptance Mapping (PRD §11)

| Item | Status |
|------|--------|
| docs/solutions/ tree + README | Done |
| .compound/ artifacts | Done |
| CONCEPTS.md ≥10 terms | Done |
| AGENTS.md updated | Done |
| Global User Rule in runbook | Done — **apply in Cursor Settings (you)** |
| learnings-researcher skill | Done |
| compound + compound-refresh skills | Done |
| errors-audit-deep updated | Done |
| Five pilot docs + LEARNINGS links | Done |
| pytest green | 157 passed |
| JOURNAL pilot note | Done |
