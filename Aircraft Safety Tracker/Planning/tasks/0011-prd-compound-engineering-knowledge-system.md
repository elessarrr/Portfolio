# PRD 0011 — Compound Engineering Knowledge System

**Status:** Draft — ready for implementation  
**Created:** 2026-06-06  
**Author:** Bhavesh (Product) / AI (CTO assist)  
**Scope:** Global workflow (all repos) · Pilot on Aircraft Safety Tracker (AST)  
**Branch policy:** Implement on current feature branch; merge to `main` when Phase 4 pilot passes  

**Inspired by:** [Every Compound Engineering plugin](https://github.com/EveryInc/compound-engineering-plugin) — specifically the **Compound** step (structured capture + automatic retrieval), not the full CE skill/agent bundle.

**Related files (current state):**
- `AGENTS.md` — mandates `JOURNAL.md` / `LEARNINGS.md` writes; no read-path for institutional knowledge
- `LEARNINGS.md` — flat ~600-line knowledge dump; high-value proactive-prevention bullets; poor selective retrieval
- `JOURNAL.md` — chronological task log (audit trail)
- `context/context-*.md` — periodic architecture snapshots via `/context-distillation`
- `~/.cursor/skills/context-distillation/SKILL.md` — global context pipeline
- `~/.cursor/skills/errors-audit-deep/SKILL.md` — batch harvest into `LEARNINGS.md`
- `.claude/gstack/` — `/review`, `/ship`, `/qa`, `/plan-eng-review`, etc.

**Reference artifacts to adapt (CE repo):**
- `plugins/compound-engineering/skills/ce-compound/references/schema.yaml`
- `plugins/compound-engineering/skills/ce-compound/assets/resolution-template.md`
- `plugins/compound-engineering/skills/ce-compound/scripts/validate-frontmatter.py`
- `plugins/compound-engineering/agents/ce-learnings-researcher.md`
- `CONCEPTS.md` pattern from CE root

---

## 1. Introduction / Overview

### Problem statement

We already **capture** engineering knowledge (`LEARNINGS.md`, `JOURNAL.md`, `/errors-audit-deep`, `/context-distillation`). What we lack is what makes Compound Engineering actually **compound**:

1. **Structured write** — one learning per file with YAML frontmatter (`module`, `tags`, `problem_type`, `symptoms`, `root_cause`) instead of an ever-growing flat file
2. **Automatic read** — agents grep/search the knowledge store **before** planning or implementing (“have we solved this before?”)
3. **Discoverability** — `AGENTS.md` (and global Cursor User Rules) tell every agent the store exists and when to consult it
4. **Fresh capture** — document while context is hot (post-fix, post-review), not only in batch retrospective audits
5. **Stale-doc hygiene** — update or refresh learnings when refactors invalidate them (e.g. FAA page-12 → page-18 migration)

Without the read path, knowledge is written but not retrieved. New sessions and new hires repeat the same mistakes despite `LEARNINGS.md` existing.

### Goal

Introduce a **Compound Knowledge System** that:

- Stores durable learnings in `docs/solutions/[category]/` with a project-adapted YAML schema
- Maintains `CONCEPTS.md` as shared domain vocabulary (primes “where does this belong?” decisions)
- Wires retrieval into planning, review, and implementation workflows
- Integrates with — but does not replace — existing `JOURNAL.md`, `LEARNINGS.md`, and `/context-distillation`
- Rolls out **globally** (Cursor User Rule + repo template) with **AST as pilot**

---

## 2. Goals

1. **Searchable knowledge store:** Every non-trivial bug fix or convention gets a `docs/solutions/` doc with valid YAML frontmatter.
2. **Pre-work retrieval:** Before substantive implementation or debugging, agents search `docs/solutions/` frontmatter and read `CONCEPTS.md` when present.
3. **Discoverability:** Every repo’s `AGENTS.md` surfaces `docs/solutions/` and `CONCEPTS.md` in a form agents will actually find.
4. **No duplicate learnings:** Overlap detection updates existing docs when the same problem is solved again (high overlap), rather than creating drift-prone duplicates.
5. **Fresh capture loop:** Post-fix and post-review compound step runs in headless/lightweight mode by default.
6. **Preserve existing assets:** `LEARNINGS.md` “Proactive Prevention” remains a curated cheat sheet; `JOURNAL.md` remains the chronological audit trail.
7. **Global portability:** A repo template + Cursor User Rule makes new projects compound-ready without re-deciding structure.
8. **Pilot validation on AST:** Five FAA/NTSB learnings migrated; agents cite prior docs unprompted in one full feature cycle.

---

## 3. User Stories

| # | As a… | I want to… | So that… |
|---|-------|-----------|---------|
| US-1 | Developer (or Cursor agent) | Search past solutions by module/tags before implementing | I reuse proven fixes instead of rediscovering them |
| US-2 | Developer | See domain terms defined in one glossary (`CONCEPTS.md`) | I place new code in the right subsystem (FAA vs NTSB vs UI) |
| US-3 | Product owner | Know learnings are captured right after a fix or review | Context-fresh docs include “what didn’t work” |
| US-4 | New contributor (human or agent) | Read `AGENTS.md` and find the knowledge store | I’m as well-armed as someone who lived through past bugs |
| US-5 | Developer | Avoid duplicate `LEARNINGS.md` entries for the same root cause | One canonical solution doc per problem |
| US-6 | Developer | Refresh stale guidance after a migration | Old page-12 FAA advice doesn’t mislead post page-18 cutover |
| US-7 | Developer on any repo | Clone a template with compound structure pre-wired | I don’t bootstrap knowledge infra from scratch each project |

---

## 4. Functional Requirements

### FR-0: Directory structure and schema (Phase 1 — Structure)

**FR-0.1** — Create the following paths in AST (and in the global repo template):

```
docs/solutions/
  build-errors/
  test-failures/
  runtime-errors/
  performance-issues/
  database-issues/
  security-issues/
  ui-bugs/
  integration-issues/
  logic-errors/
  architecture-patterns/
  design-patterns/
  tooling-decisions/
  conventions/
  workflow-issues/
  developer-experience/
  documentation-gaps/
  best-practices/
  patterns/                    # optional: critical-patterns.md when warranted
CONCEPTS.md                    # repo root
```

**FR-0.2** — Add project-adapted schema at `.compound/schema.yaml` (forked from CE `references/schema.yaml`) with **AST-specific** `component` enum values, including at minimum:

| Value | Meaning |
|-------|---------|
| `flask_app` | Flask routes, templates, app factory |
| `sqlite_db` | SQLite schema, migrations, single-writer constraints |
| `faa_ingestion` | FAA AIDS import, dedupe, URL builders, ASIAS |
| `ntsb_ingestion` | NTSB/CAROL enrichment, ASN mapping |
| `url_audit` | `/audit-urls`, JSONL buckets, httpx audit CLI |
| `link_picker` | `pick_primary_href`, `is_active`, UI link gating |
| `llm_integration` | DeepSeek summaries, `.env` key handling |
| `gstack_qa` | browse binary, Playwright sandbox, `/qa` |
| `development_workflow` | Cursor agent, git, pytest, ports |
| `documentation` | PRDs, context snapshots, skills |

Retain CE’s two **tracks** (bug vs knowledge) and shared required fields: `module`, `date`, `problem_type`, `component`, `severity`, plus bug-track `symptoms`, `root_cause`, `resolution_type`.

**FR-0.3** — Add resolution templates at `.compound/resolution-template.md` (fork CE `assets/resolution-template.md`):

- **Bug track sections:** Problem → Symptoms → What Didn’t Work → Solution → Why This Works → Prevention → Related Issues
- **Knowledge track sections:** Context → Guidance → Why This Matters → When to Apply → Examples → Related

**FR-0.4** — Copy and adapt CE `scripts/validate-frontmatter.py` to `.compound/scripts/validate-frontmatter.py` (Python 3 stdlib only). All new/updated solution docs must pass validation before a compound step is considered complete.

**FR-0.5** — Add `docs/solutions/README.md` (≤30 lines): purpose, category list, frontmatter field summary, link to `.compound/schema.yaml`.

---

### FR-1: CONCEPTS.md bootstrap (Phase 1)

**FR-1.1** — Create `CONCEPTS.md` at repo root with CE-standard preamble:

> Shared domain vocabulary for this project — entities, named processes, and status concepts with project-specific meaning. Seeded with core domain vocabulary, then accretes as compound learnings are written; direct edits are fine. Glossary only, not a spec or catch-all.

**FR-1.2** — Seed AST entries (minimum set for pilot):

| Term | Type | Definition (summary) |
|------|------|----------------------|
| `Aircraft` | Entity | Catalog row; make/model; incident rollup target |
| `Incident` | Entity | Single safety event; links to sources |
| `IncidentSource` | Entity | Per-source row; holds `source_url`, `is_active` |
| `is_active` | Status | DB flag; `link_picker` hides inactive outbound links |
| `working_brief_report` | Status | FAA URL audit bucket; page-18 brief viable |
| `working_search_prefill` | Status | FAA page-12 search prefill; not product-ready |
| `carol_empty_spa` | Status | NTSB CAROL HTTP 200 with empty React shell |
| `ASIAS liveness gate` | Named process | Require ASIAS homepage 2xx before bulk URL audit |
| `FAA dedupe pass` | Named process | Score-based overlap vs ASN/NTSB; no auto-create pages |
| `NTSB make/model map` | Named process | Normalize strings before bulk import |

**FR-1.3** — Glossary entries must **not** embed file paths, class signatures, or config values that drift — those belong in solution docs. When a compound write touches a term, refresh its **coherence neighborhood** (sibling/cross-referenced terms) only on evidence in hand.

---

### FR-2: Discoverability in AGENTS.md (Phase 1)

**FR-2.1** — Update `AGENTS.md` **Core Workflows** (or nearest architecture/directory section) with informational lines (tone: awareness, not imperative “always search”):

```markdown
docs/solutions/  # documented solutions to past problems (bugs, conventions, workflow patterns); YAML frontmatter (module, tags, problem_type); relevant when implementing or debugging in documented areas
CONCEPTS.md      # shared domain vocabulary (entities, named processes, status concepts)
```

**FR-2.2** — Add compound **write** obligations alongside existing journal rules:

- After every **non-trivial** resolved bug or review with actionable findings → run compound capture (FR-5).
- Append **1–2 sentences** to `JOURNAL.md` (unchanged format).
- If the learning is a **repeat pattern** → add or refine one bullet under `LEARNINGS.md` § Proactive Prevention **pointing to** the canonical `docs/solutions/` file (not duplicating full content).

**FR-2.3** — Add compound **read** obligation:

- Before substantive implementation or debugging in a documented area → search `docs/solutions/` frontmatter (`title:`, `tags:`, `module:`, `problem_type:`) and read `CONCEPTS.md` when orienting to domain concepts.

---

### FR-3: Global Cursor User Rule (Phase 1 — Global)

**FR-3.1** — Add a **global User Rule** in Cursor Settings (applies to all projects):

```markdown
## Compound knowledge routing

Before implementing or debugging in a documented area:
- Grep docs/solutions/ YAML frontmatter (module, tags, problem_type, title)
- Read CONCEPTS.md at repo root if present

After a non-trivial fix or /review with findings:
- Write or update docs/solutions/[category]/[slug].md (see .compound/schema.yaml)
- Append JOURNAL.md (1–2 sentences)
- Add LEARNINGS.md proactive bullet only for repeat patterns (link to solution doc)

Skills:
- Compound capture: project /.cursor/skills/compound/ or /ce-compound mode:headless if CE plugin installed
- Deep retrospective harvest: /errors-audit-deep (quarterly backfill only)
- Architecture snapshot: /context-distillation when context/ snapshot >2 days old
- Review: gstack /review (not /ce-code-review unless explicitly requested)

Do not duplicate full learnings across LEARNINGS.md and docs/solutions/ — one canonical solution doc; LEARNINGS is index/cheat sheet only.
```

**FR-3.2** — Document the User Rule text in `Planning/runbooks/compound-knowledge-global-setup.md` so it can be re-applied on new machines.

---

### FR-4: Learnings researcher — read path (Phase 2)

**FR-4.1** — Create global skill `~/.cursor/skills/learnings-researcher/SKILL.md` adapted from CE `ce-learnings-researcher.md`:

- **Input:** free-form work context or structured `<work-context>` block
- **Search:** grep-first on `docs/solutions/` frontmatter; probe subdirectories dynamically; read frontmatter of candidates (first ~30 lines); full-read only strong/moderate matches
- **Output:** up to 5 distilled findings with file paths, problem_type, relevance, key insight
- **Grounding:** read `CONCEPTS.md` first when present
- **Empty store:** explicitly state no matches; note work may be worth compound capture after landing

**FR-4.2** — Wire invocation points (document in skill + `AGENTS.md`):

| Trigger | When |
|---------|------|
| `/plan-eng-review` | Before locking architecture |
| Start of substantive Cursor implementation prompt | When CTO hands off phased work |
| `/review` (optional pre-step) | When diff touches documented modules (FAA, NTSB, url_audit) |
| Manual | `/learnings-researcher [context]` |

**FR-4.3** — Update `~/.cursor/skills/context-distillation/SKILL.md` (or AST `AGENTS.md` only) to note: context snapshots **complement** but do not replace per-task `docs/solutions/` search.

---

### FR-5: Compound capture skill — write path (Phase 3)

**FR-5.1** — Create project skill `.cursor/skills/compound/SKILL.md` (symlinked via gstack setup if desired) adapted from CE `ce-compound` with these modes:

| Mode | Behavior |
|------|----------|
| **Full** | Parallel research: classify track/category, extract solution, find related docs + overlap score, optional session-history scan; write one file; vocabulary capture; discoverability check |
| **Lightweight** | Single-pass write; skip overlap subagent; update-only `CONCEPTS.md` |
| **Headless** (`mode:headless`) | Full without blocking questions; apply discoverability edit silently; end with structured terminal report — for post-review automation |

**FR-5.2** — **Single deliverable:** one file `docs/solutions/[category]/[slug].md` (create or update). Subagents return text only; orchestrator writes.

**FR-5.3** — **Overlap rules** (from CE):

| Overlap | Action |
|---------|--------|
| High (4–5 dimensions match) | Update existing doc; add `last_updated: YYYY-MM-DD` |
| Moderate (2–3) | Create new doc; flag for refresh review |
| Low/none | Create new doc |

**FR-5.4** — **Post-write side effects** (automatic):

1. Validate frontmatter via `.compound/scripts/validate-frontmatter.py`
2. Update `CONCEPTS.md` when qualifying domain terms surface (Phase 2.4 rules from CE)
3. Discoverability check on `AGENTS.md` — patch if knowledge store not surfaced
4. Append `JOURNAL.md` entry (1–2 sentences)
5. Optionally add `LEARNINGS.md` proactive bullet with link to solution doc

**FR-5.5** — **Capture triggers** (document in skill):

```
Fix verified → /compound mode:headless
/review complete with findings → /compound mode:headless "from review"
User says "that worked" / "problem solved" → /compound
Quarterly gap-fill → /errors-audit-deep (backfill only; writes docs/solutions/ for missed items)
```

**FR-5.6** — **Preconditions:** problem solved and verified; non-trivial (skip typos/obvious one-liners).

**FR-5.7** — Optional CE plugin path: if `/add-plugin compound-engineering` is installed globally, `/ce-compound mode:headless` is an acceptable alias; project skill must document routing to avoid duplicate capture.

---

### FR-6: Stale-doc refresh (Phase 3)

**FR-6.1** — Create `.cursor/skills/compound-refresh/SKILL.md` (narrow scope, adapted from CE `ce-compound-refresh`):

- **Invoke when:** refactor/migration/rename contradicts older solution docs; moderate overlap flagged; pattern doc overly broad
- **Argument:** narrow scope — module name, category, or specific file path (e.g. `faa-aids`, `integration-issues`, `docs/solutions/integration-issues/asias-liveness-gate.md`)
- **Do not invoke** for broad historical sweeps without explicit user request

**FR-6.2** — After FAA/NTSB URL migrations, run refresh scoped to affected module before closing related PRDs.

---

### FR-7: Migrate existing knowledge — AST pilot (Phase 4)

**FR-7.1** — Migrate these five AST learnings from `LEARNINGS.md` into canonical `docs/solutions/` docs (full bug/knowledge track format + frontmatter):

| # | Source topic | Target category | Slug (suggested) |
|---|--------------|-----------------|------------------|
| 1 | ASIAS global outage / liveness gate | `integration-issues` | `asias-liveness-gate-false-positive-audit.md` |
| 2 | CAROL empty SPA ≠ viable link | `integration-issues` | `ntsb-carol-empty-spa-shell.md` |
| 3 | SQLite single-writer during bulk jobs | `database-issues` | `sqlite-single-writer-bulk-jobs.md` |
| 4 | FAA page-18 brief vs page-12 search | `integration-issues` | `faa-brief-report-vs-search-prefill.md` |
| 5 | Dedupe fatalities null = 0 alignment | `logic-errors` | `ntsb-dedupe-fatalities-null-as-zero.md` |

**FR-7.2** — After migration, add proactive-prevention bullets in `LEARNINGS.md` that **link** to each doc (one line each), trim duplicated prose from `LEARNINGS.md` body sections where fully superseded (keep § history if referenced elsewhere).

**FR-7.3** — Run one full feature cycle (e.g. next AST task) with read → work → compound loop; record in `JOURNAL.md` whether agent cited `docs/solutions/` unprompted.

---

### FR-8: Global repo template (Phase 1 — Global)

**FR-8.1** — Create `~/dev-templates/compound-repo/` (or equivalent) containing:

```
AGENTS.md              # compound read/write + discoverability lines
JOURNAL.md             # empty scaffold
LEARNINGS.md           # Proactive Prevention scaffold only
CONCEPTS.md            # preamble only
docs/solutions/README.md
.compound/schema.yaml
.compound/resolution-template.md
.compound/scripts/validate-frontmatter.py
context/context-latest.md   # pointer stub
.cursor/skills/             # symlink instructions to gstack + compound
Planning/runbooks/compound-knowledge-global-setup.md
```

**FR-8.2** — Document “new repo bootstrap” in runbook: copy template → run `/context-distillation` → seed `CONCEPTS.md` on first domain learning.

**FR-8.3** — Optional: install CE plugin globally via `/add-plugin compound-engineering` and `/ce-setup` per repo — document as alternative path in runbook, not required for v1.

---

### FR-9: Integration with existing skills (all phases)

**FR-9.1** — **`/errors-audit-deep`:** Change primary role to **quarterly backfill**; new writes target `docs/solutions/` (create docs for harvested items not already in store). Keep de-dupe against both `LEARNINGS.md` and `docs/solutions/`.

**FR-9.2** — **`/context-distillation`:** Continue periodic architecture snapshots in `context/`; Section 4 Bug Reports may **link** to `docs/solutions/` entries rather than duplicating full write-ups.

**FR-9.3** — **`/review` (gstack):** Add optional final step in review report: “Compound recommendation: [scope hint]” when findings reveal reusable patterns. Does not auto-run compound — human or headless trigger follows.

**FR-9.4** — **`/plan-eng-review`:** Invoke `/learnings-researcher` (or inline equivalent) before finalizing plan.

**FR-9.5** — **Do not adopt** CE `/ce-code-review` multi-agent panel as default — gstack `/review` remains primary (SQL safety, LLM boundary checks already trusted).

---

## 5. Non-Goals (Out of Scope)

| # | Non-goal | Rationale |
|---|----------|-----------|
| NG-1 | Install all 37 CE skills + 51 agents | Overlap with gstack; token/cost overhead |
| NG-2 | Replace `LEARNINGS.md` entirely | Proactive Prevention cheat sheet stays valuable |
| NG-3 | Replace `JOURNAL.md` or `context/` snapshots | Different jobs: audit trail vs architecture handoff |
| NG-4 | Full `/ce-compound` with 4 subagents on every tiny fix | Use lightweight/headless for simple items |
| NG-5 | `/ce-strategy`, `/ce-ideate`, `/ce-product-pulse` in v1 | Optional later; AST has PRD process already |
| NG-6 | Rails-specific CE schema enums unchanged | Must customize `component` for Flask/SQLite/FAA/NTSB |
| NG-7 | Automated hooks firing compound on every commit | v2 consideration; v1 is manual/headless trigger |
| NG-8 | Migrating all 55+ LEARNINGS sections in one pass | Pilot five; backfill incrementally via audit skill |

---

## 6. Design Considerations

### Knowledge store vs existing files

| Artifact | Role after this PRD |
|----------|---------------------|
| `docs/solutions/` | **Canonical** per-problem/per-pattern docs (searchable) |
| `CONCEPTS.md` | Domain glossary (placement decisions) |
| `LEARNINGS.md` | Curated index + proactive one-liners linking to solution docs |
| `JOURNAL.md` | Chronological “what we did today” (1–2 sentences) |
| `context/context-*.md` | Periodic architecture + bug inventory snapshot |
| `Planning/tasks/*.md` | Feature specs (unchanged) |

### Filename convention

- Pattern: `[sanitized-problem-slug].md` — **no date suffix** in filename
- Canonical date: `date:` frontmatter field; use `last_updated:` on updates

### Overlap dimensions (for dedup)

1. Problem statement  
2. Root cause  
3. Solution approach  
4. Referenced files/modules  
5. Prevention rules  

### Headless terminal report (success)

```
✓ Documentation complete (headless mode)
File: docs/solutions/<category>/<filename>.md  (created | updated)
Track: <bug | knowledge>
Overlap: <none | moderate | high — existing doc updated>
CONCEPTS.md: <scanned | updated N entries>
JOURNAL.md: appended
Refresh recommendation: <none | scope hint>
```

---

## 7. Technical Considerations

### Dependencies

- Python 3 for `validate-frontmatter.py`
- `rg`/grep available to agents (standard in Cursor)
- Optional: CE plugin `/add-plugin compound-engineering` as alternate implementation of capture skill

### AST-specific schema notes

- `module` examples: `faa-aids`, `ntsb-enrichment`, `url-audit`, `flask-ui`, `ingestion-core`
- `problem_type` for knowledge track: prefer `convention`, `workflow_issue`, `architecture_pattern`, `tooling_decision` over generic `best_practice`
- Tag convention: lowercase, hyphen-separated (max 8 tags)

### Symlink / gstack setup

- Project skills live in `.cursor/skills/` symlinked from `.claude/gstack/` per existing setup
- Add `compound/` and `compound-refresh/` skill dirs to gstack or project `.cursor/skills/` directly
- Run `bun run gen:skill-docs` if skills are tmpl-backed in gstack

### Git

- Commit `docs/solutions/`, `CONCEPTS.md`, `.compound/`, updated `AGENTS.md`, skill files
- Do not gitignore knowledge store — it is team/agent distributed knowledge by design

### Rollback

- Removing compound system: delete `docs/solutions/`, `.compound/`, compound skills; revert `AGENTS.md` discoverability lines; `LEARNINGS.md` retains content

---

## 8. Success Metrics

| Metric | Target | How to measure |
|--------|--------|----------------|
| Pilot docs migrated | 5/5 with valid frontmatter | `validate-frontmatter.py` exit 0 on each |
| `AGENTS.md` discoverability | Lines present | Manual check |
| Global User Rule | Documented in runbook + applied in Cursor | Runbook exists; user confirms |
| Agent retrieval (pilot) | ≥1 unprompted citation of `docs/solutions/` in one feature cycle | `JOURNAL.md` pilot entry |
| Duplicate learnings | 0 new high-overlap duplicates in pilot month | Overlap check in compound skill |
| `CONCEPTS.md` seeded | ≥10 AST domain terms | File review |
| Regression | Existing pytest green | CI / local pytest |
| Backfill | `/errors-audit-deep` writes to `docs/solutions/` without duplicating store | Spot-check after one audit run |

---

## 9. Implementation Phases (Suggested Order)

| Phase | Name | Deliverables | Est. effort |
|-------|------|--------------|-------------|
| **1** | Structure | FR-0, FR-1, FR-2, FR-8 template, FR-3 runbook | 0.5–1 day |
| **2** | Read path | FR-4, FR-9.4 | 0.5 day |
| **3** | Write path | FR-5, FR-6, FR-9.1–FR-9.3 | 1 day |
| **4** | AST pilot | FR-7, success metrics validation | 0.5–1 day |

**Do not start Phase 4 until Phase 1–3 skills exist and validate.**

---

## 10. Open Questions

| # | Question | Owner | Default if unanswered |
|---|----------|-------|------------------------|
| OQ-1 | Install CE plugin globally (`/add-plugin compound-engineering`) or project-only custom skills? | Bhavesh | Custom skills v1; CE plugin optional alias |
| OQ-2 | Store `.compound/` at repo root vs `docs/solutions/.compound/`? | Engineering | Repo root `.compound/` (matches CE convention) |
| OQ-3 | Add `docs/solutions/patterns/critical-patterns.md` for FAA+NTSB must-know rules? | Bhavesh | Defer until ≥15 solution docs exist |
| OQ-4 | Automate headless compound via Cursor hook post-`/review`? | Engineering | Manual v1; hook v2 |
| OQ-5 | Migrate all `LEARNINGS.md` numbered sections or pilot-only + incremental backfill? | Bhavesh | Pilot 5 + incremental (per NG-8) |
| OQ-6 | Global template path: `~/dev-templates/compound-repo/` vs dotfiles repo? | Bhavesh | `~/dev-templates/compound-repo/` |

---

## 11. Acceptance Checklist (Definition of Done)

- [ ] `docs/solutions/` tree + README exist
- [ ] `.compound/schema.yaml`, `resolution-template.md`, `validate-frontmatter.py` exist and documented
- [ ] `CONCEPTS.md` seeded with ≥10 AST terms
- [ ] `AGENTS.md` updated with discoverability + read/write compound rules
- [ ] Global User Rule text saved in `Planning/runbooks/compound-knowledge-global-setup.md` and applied in Cursor
- [ ] `~/.cursor/skills/learnings-researcher/SKILL.md` exists
- [ ] `.cursor/skills/compound/SKILL.md` and `compound-refresh/SKILL.md` exist
- [ ] `/errors-audit-deep` updated to write `docs/solutions/` on backfill
- [ ] Five pilot solution docs migrated; `LEARNINGS.md` links added
- [ ] One feature cycle completed with pilot note in `JOURNAL.md`
- [ ] `JOURNAL.md` entry for PRD 0011 implementation
- [ ] No pytest regressions

---

## 12. Related Reading

- [Compound Engineering plugin README](https://github.com/EveryInc/compound-engineering-plugin)
- [Every — Compound step (article)](https://every.to/guides/compound-engineering) *(referenced in user brief)*
- AST `LEARNINGS.md` — source material for pilot migration
- CE `ce-compound` skill — full workflow reference for skill author
