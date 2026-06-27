# Documented Solutions

Searchable institutional knowledge for this project. Each file documents one solved problem or durable pattern.

**Schema:** `.compound/schema.yaml`  
**Templates:** `.compound/resolution-template.md`  
**Validate:** `python3 .compound/scripts/validate-frontmatter.py <path>`

## Categories

Bug-shaped: `build-errors/`, `test-failures/`, `runtime-errors/`, `performance-issues/`, `database-issues/`, `security-issues/`, `ui-bugs/`, `integration-issues/`, `logic-errors/`

Knowledge-shaped: `architecture-patterns/`, `design-patterns/`, `tooling-decisions/`, `conventions/`, `workflow-issues/`, `developer-experience/`, `documentation-gaps/`, `best-practices/`, `patterns/`

## Frontmatter (required)

`module`, `date`, `problem_type`, `component`, `severity` — plus bug-track `symptoms`, `root_cause`, `resolution_type` when applicable.

Optional: `title`, `tags`, `applies_when`, `last_updated`

## When to search

Relevant when implementing or debugging in documented areas (FAA, NTSB, URL audit, Flask UI, ingestion). Also read `CONCEPTS.md` for domain vocabulary.

## Capture

After non-trivial fixes: `/compound mode:headless` (or `/ce-compound` if CE plugin installed).
