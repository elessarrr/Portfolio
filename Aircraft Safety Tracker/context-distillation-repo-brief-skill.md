***

name: Context Distillation/Repo Brief
description: "Use this:

> When the user wants to document or understand their codebase, prepare context for a senior AI model, debug a bug cost-efficiently, or run a project health check. Trigger when the user says things like "document my project", "summarise my codebase", "explain how my app works", "I have a bug I want Claude to fix", "create a repo brief", "update my project docs", or asks about project structure, file relationships, or architecture."

***

***

name: context-distillation
description: >
Generates a comprehensive, token-efficient "Master Context Document" for a codebase by
producing an architecture overview, data flow diagram, file map, bug report template, and
relevant code snippet extraction. Use this skill whenever the user wants to document how
their project works, prepare a codebase summary for a senior AI model (like Claude Sonnet/Opus),
debug a bug cost-efficiently by pre-processing with a cheaper model, or run a regular
"health check" to keep project documentation up to date. Trigger this skill when the user says
things like "document my project", "summarise my codebase", "prepare context for Claude",
"I have a bug I want Claude to fix", "create a repo brief", or "update my project docs".
----------------------------------------------------------------------------------------

# Context Distillation Skill

A workflow for transforming a raw codebase into a dense, structured **Master Context Document**
that allows a senior AI model (e.g. Claude Sonnet) to understand the project and solve problems
without reading the full codebase — minimising token spend while maximising solution quality.

***

## When to Use This Skill

- **Bug fixing**: Before escalating a bug to a more powerful (expensive) model
- **Regular project health checks**: Run periodically to keep architecture docs current
- **Onboarding**: When a new developer or AI agent needs to understand the project quickly
- **Pre-sprint planning**: Before generating a PRD or task list, to ground the AI in current state

***

## Overview of the Pipeline

```
Raw Codebase
     │
     ▼
[Cheap Model: GPT-4o mini / Gemini Flash / Claude Haiku]
     │
     ├── Architecture Overview
     ├── Data Flow Diagram (Mermaid)
     ├── File Map
     └── Relevant Code Snippets
     │
     ▼
[You: write the Bug Report]
     │
     ▼
Master Context Document (.md)
     │
     ▼
[Claude Sonnet / Opus]
     │
     ▼
Diagnosis + Fix
```

**Key principle**: Cheap models act as pre-processors. They translate code into structured prose
that Claude can reason over at a fraction of the token cost of reading raw files.

***

## Output

- **Format**: Markdown (`.md`)
- **Location**: `/docs/` or `/context/` or `/context_distillation/` in your project root
- **Filename**: `context-[YYYY-MM-DD].md` (e.g. `context-2025-04-20.md`)
- **Target size**: Under 8,000 words / \~10,000 tokens

***

## Step-by-Step Process

***

### Step 1 — Architecture Overview

**Who runs this**: Cheap model (pointed at full codebase or key entry-point files)

**Prompt to use**:

```
You are a senior software engineer. Analyze this codebase and produce a concise
Architecture Overview document in Markdown.

Include:
1. What this application does (2-3 sentences max)
2. Tech stack — languages, frameworks, databases, third-party APIs
3. High-level component breakdown (e.g. frontend, backend, DB layer, external services)
4. How components communicate (REST, WebSockets, direct function calls, queues, etc.)
5. Key design patterns in use (MVC, event-driven, repository pattern, etc.)
6. Any known constraints or non-obvious architectural decisions

Be precise and concise. Do not include code. Maximum 500 words.
Output as a Markdown section with the heading: ## Architecture Overview
```

***

### Step 2 — Data Flow Diagram

**Who runs this**: Cheap model

**Prompt to use**:

````
You are a senior software engineer. Analyze this codebase and produce a
Data Flow Diagram in Mermaid.js syntax.

Show:
- User interactions and entry points
- How data flows from input → processing → storage → output
- External API calls and third-party services
- Key data transformation points
- Error paths if clearly visible in code

Use `graph TD` (top-down flowchart) or `sequenceDiagram` — whichever better
represents this application's behaviour.

Output ONLY the Mermaid code block. No prose explanation.
Wrap in: ```mermaid ... ```
````

***

### Step 3 — File Map

**Who runs this**: Cheap model (pointed at directory tree + file list)

**Prompt to use**:

```
You are a senior software engineer. Produce a File Map for this codebase.

For every meaningful file, write ONE sentence describing its single responsibility.
Group files by directory or architectural layer (e.g. routes/, models/, utils/, components/).
Exclude boilerplate: .gitignore, package-lock.json, .env.example, migration files, etc.

Format as a Markdown table:

| File Path | Responsibility |
|-----------|----------------|

If a file is particularly important or frequently referenced by others, add a ⭐ before the path.
```

***

### Step 4 — Bug Report

**Who writes this**: YOU (the developer). No model can know what the bug is.

**Template to fill in**:

```markdown
## Bug Report

### Summary
[One sentence: what is broken]

### Expected Behaviour
[What should happen]

### Actual Behaviour
[What actually happens]

### Steps to Reproduce
1.
2.
3.

### Error Messages / Stack Traces
[Paste exact errors — do not paraphrase]

### Environment
- OS:
- Runtime/language version:
- Browser (if applicable):
- Deployment context (local / staging / prod):

### What I've Already Tried
- [Attempt 1 and outcome]
- [Attempt 2 and outcome]

### Suspected Area of Code
[File names, functions, or modules you believe are involved — even if unsure]

### Relevant Recent Changes
[Any recent commits, dependency updates, or config changes that preceded the bug]
```

***

### Step 5 — Relevant Code Snippets

**Who runs this**: Cheap model (pointed ONLY at files suspected to be related to the bug)

**Prompt to use**:

```
You are a senior software engineer helping debug the following issue:

[PASTE YOUR BUG SUMMARY HERE]

Review the files provided below. Extract ONLY the code sections most likely
related to this bug. Do not summarise or paraphrase — include the actual code.

For each snippet:
- Add the file path as a header (e.g. ### src/routes/auth.js)
- Add a one-line comment above the snippet explaining why it's relevant
- Include enough surrounding context (10-20 lines) that the reader understands the snippet

Files to review:
[PASTE FILE CONTENTS HERE]
```

***

### Step 6 — Error Log Summary

**Who runs this**: Cheap model or you manually

**Prompt to use** (if handing logs to a model):

```
Clean up and summarise the following error logs.
- Remove duplicate lines
- Group similar errors together
- Highlight the first occurrence of each unique error
- Preserve exact error messages, stack trace file paths, and line numbers
- Remove timestamps unless they show a meaningful sequence
- Output as clean Markdown with one section per unique error type

Logs:
[PASTE RAW LOGS HERE]
```

***

### Step 7 — Assemble the Master Context Document

Combine all outputs into a single `.md` file in this exact order:

```markdown
# Master Context Document
**Project**: [project name]
**Date**: [YYYY-MM-DD]
**Purpose**: [e.g. "Debug: login redirect loop" or "Regular health check"]

---

## 1. Architecture Overview
[Output from Step 1]

---

## 2. Data Flow Diagram
[Output from Step 2 — Mermaid block]

---

## 3. File Map
[Output from Step 3 — table]

---

## 4. Bug Report
[Your filled-in template from Step 4]

---

## 5. Relevant Code Snippets
[Output from Step 5]

---

## 6. Error Log Summary
[Output from Step 6]
```

Save as: `context/context-YYYY-MM-DD.md`

***

### Step 8 — The Claude Prompt

Open a new Claude chat. Paste the Master Context Document and use this prompt:

```
I'm giving you a compressed context document about my application.
It contains the architecture, data flow, file map, bug report, and relevant
code snippets. It was prepared by a cheaper model to save tokens — please treat
it as authoritative unless something seems contradictory.

After reading, please:
1. Confirm in 2-3 sentences what you understand this application to do
2. State your hypothesis about the root cause of the bug
3. Ask any clarifying questions you need before proposing a fix
4. Once confident, propose the specific fix — include exact file paths and code changes

Do not guess or propose partial solutions. If you need more information,
ask for it explicitly.

[PASTE MASTER CONTEXT DOCUMENT HERE]
```

**Why the confirm-first step matters**: It lets you catch misreadings before Claude goes down
a wrong path — saving you tokens on a bad fix.

***

## Running as a Regular Health Check (No Bug)

When using this skill for ongoing project documentation rather than debugging, skip Steps 4–6
and use this modified Claude prompt instead:

```
I'm giving you a compressed context document about my application.
Please review it and tell me:
1. Whether the architecture and file map look consistent with each other
2. Any components or patterns that seem overly complex or worth simplifying
3. Any obvious gaps or risks you can spot from the documented structure
4. Suggested improvements to the documentation itself for next time

[PASTE MASTER CONTEXT DOCUMENT HERE]
```

Run this workflow after every significant sprint, major refactor, or new module addition.

***

## Tips for Keeping Token Costs Low

| Practice                                               | Why it helps                                                                                     |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| Keep master doc under 8,000 words                      | \~10K tokens — a very cost-effective Claude session                                              |
| Use Mermaid for diagrams                               | Extremely token-efficient vs. prose descriptions of the same structure                           |
| Never paste full files into Claude                     | Always run Step 5 extraction first                                                               |
| Version your master doc by date                        | Diff between versions to see how architecture evolved                                            |
| Update bug report section iteratively                  | If Claude's first answer fails, update the doc and continue in the same chat (preserves context) |
| Use Claude Haiku or Gemini Flash for Steps 1–3 and 5–6 | These are mechanical extraction tasks — expensive models add no value here                       |

***

## Relevant Files Convention

When saving your master context document, also maintain a `/context/` directory:

```
/context/
├── context-2025-04-20.md       ← today's snapshot
├── context-2025-03-01.md       ← previous sprint
└── context-latest.md           ← symlink or copy of most recent (optional)
```

This gives you a cheap audit trail of how your architecture has changed over time.

***

## Notes

- The cheap model does not need to understand the bug — it only needs to extract and
  structure information faithfully. Keep its instructions mechanical and precise.
- If your codebase is very large (100+ files), run Step 3 (File Map) on the directory
  tree only, not file contents. Run Step 5 (snippets) only on the 3-5 most suspect files.
- For monorepos, run Steps 1–3 per service/package, then combine into one master doc with
  a top-level summary section.
- This workflow pairs well with the `generate-tasks` and `create-prd` skills — run context
  distillation first, then hand the master doc to those workflows as codebase context.

