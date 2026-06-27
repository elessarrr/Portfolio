# Resolution Templates

Choose the template matching the problem_type track (see `.compound/schema.yaml`).

---

## Bug Track Template

Use for: `build_error`, `test_failure`, `runtime_error`, `performance_issue`, `database_issue`, `security_issue`, `ui_bug`, `integration_issue`, `logic_error`

```markdown
---
title: [Clear problem title]
date: YYYY-MM-DD
category: [docs/solutions subdirectory]
module: [module-name]
problem_type: [schema enum]
component: [schema enum]
symptoms:
  - "[Observable symptom 1]"
root_cause: [schema enum]
resolution_type: [schema enum]
severity: [schema enum]
tags: [keyword-one, keyword-two]
---

# [Clear problem title]

## Problem
[1-2 sentence description]

## Symptoms
- [Observable symptom or error]

## What Didn't Work
- [Attempted fix and why it failed]

## Solution
[The fix that worked, with code snippets when useful]

## Why This Works
[Root cause explanation]

## Prevention
- [Concrete practice, test, or guardrail]

## Related Issues
- [Related docs or PRDs]
```

---

## Knowledge Track Template

Use for: `convention`, `workflow_issue`, `best_practice`, `documentation_gap`, `architecture_pattern`, `design_pattern`, `tooling_decision`, `developer_experience`

```markdown
---
title: [Clear, descriptive title]
date: YYYY-MM-DD
category: [docs/solutions subdirectory]
module: [module-name]
problem_type: [schema enum]
component: [schema enum]
severity: [schema enum]
applies_when:
  - "[Condition where this applies]"
tags: [keyword-one, keyword-two]
---

# [Clear, descriptive title]

## Context
[What situation prompted this guidance]

## Guidance
[The practice or recommendation with examples]

## Why This Matters
[Rationale and impact]

## When to Apply
- [Conditions where this applies]

## Examples
[Before/after or usage examples]

## Related
- [Related docs or PRDs]
```
