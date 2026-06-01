# Cursor skills (gstack)

Project skills symlinked from [`.claude/gstack/`](../.claude/gstack/).

## One-time setup

From the repo root:

```bash
cd ".claude/skills/gstack" && ./setup
```

This builds the `browse` binary and ensures Playwright Chromium is installed.

## Invoke in Cursor

Type `/` plus the skill name (same as Claude Code), for example:

| Skill | Use for |
|-------|---------|
| `/browse` | Headless browser QA, screenshots, DOM checks |
| `/qa` | Systematic QA pass on a branch or full app |
| `/review` | Pre-merge PR review |
| `/ship` | Merge, test, version bump, changelog, PR |
| `/setup-browser-cookies` | Import Chrome/Arc cookies into browse session |
| `/plan-ceo-review` | CEO-style plan review |
| `/plan-eng-review` | Engineering plan review |
| `/retro` | Weekly retro |
| `/gstack-upgrade` | Update gstack |
| `/gstack` | Browse CLI overview (same as browse workflows) |

Browse binary path (after setup):

`Aircraft Safety Tracker/.claude/gstack/browse/dist/browse`
