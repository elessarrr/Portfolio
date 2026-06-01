# Phase 2.4: NTSB Manual Verification Checklist (50 Records)

## Purpose

Use this runbook after a non-zero NTSB remediation apply run to manually verify that updated `IncidentSource.source_url` values resolve to real investigation content.

## Preconditions

- [ ] `data/ntsb_legacy_mapping.csv` has real rows (`cm_ntsbNum/cm_mkey -> ev_id`).
- [ ] Remediation script dry-run completed and output reviewed.
- [ ] Remediation script apply run completed with `rows_updated > 0`.

## Step 1: Capture Before Snapshot

Run before apply:

```bash
PYTHONPATH=. ./.venv/bin/python - <<'PY'
import csv
from app import create_app
from app.models import IncidentSource

app = create_app()
with app.app_context():
    rows = (
        IncidentSource.query
        .filter(IncidentSource.source_name == "NTSB")
        .all()
    )
    with open("data/logs/ntsb_source_urls_before.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "source_record_id", "source_url"])
        for r in rows:
            w.writerow([r.id, r.source_record_id, r.source_url or ""])
print("wrote data/logs/ntsb_source_urls_before.csv")
PY
```

## Step 2: Capture After Snapshot

Run immediately after apply:

```bash
PYTHONPATH=. ./.venv/bin/python - <<'PY'
import csv
from app import create_app
from app.models import IncidentSource

app = create_app()
with app.app_context():
    rows = (
        IncidentSource.query
        .filter(IncidentSource.source_name == "NTSB")
        .all()
    )
    with open("data/logs/ntsb_source_urls_after.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "source_record_id", "source_url"])
        for r in rows:
            w.writerow([r.id, r.source_record_id, r.source_url or ""])
print("wrote data/logs/ntsb_source_urls_after.csv")
PY
```

## Step 3: Build Exact Updated Set

```bash
PYTHONPATH=. ./.venv/bin/python - <<'PY'
import csv

before = {}
with open("data/logs/ntsb_source_urls_before.csv", newline="") as f:
    for row in csv.DictReader(f):
        before[row["id"]] = row

updated = []
with open("data/logs/ntsb_source_urls_after.csv", newline="") as f:
    for row in csv.DictReader(f):
        old = before.get(row["id"])
        if old and old["source_url"] != row["source_url"]:
            updated.append({
                "id": row["id"],
                "source_record_id": row["source_record_id"],
                "old_source_url": old["source_url"],
                "new_source_url": row["source_url"],
            })

with open("data/logs/ntsb_source_urls_updated.csv", "w", newline="") as f:
    w = csv.DictWriter(
        f,
        fieldnames=["id", "source_record_id", "old_source_url", "new_source_url"],
    )
    w.writeheader()
    w.writerows(updated)

sample = updated[:50]
with open("data/logs/ntsb_source_urls_updated_sample50.csv", "w", newline="") as f:
    w = csv.DictWriter(
        f,
        fieldnames=["id", "source_record_id", "old_source_url", "new_source_url"],
    )
    w.writeheader()
    w.writerows(sample)

print(f"updated_total={len(updated)}")
print("wrote data/logs/ntsb_source_urls_updated.csv")
print("wrote data/logs/ntsb_source_urls_updated_sample50.csv")
PY
```

## Step 4: Manual URL Validation (Sample of 50)

- [ ] Open each `new_source_url` from `data/logs/ntsb_source_urls_updated_sample50.csv`.
- [ ] Confirm page resolves (no 404/no generic "record not found" page).
- [ ] Confirm page content corresponds to the incident identifier/date/location where available.
- [ ] Record pass/fail per row in a copy of the sample CSV (add columns `status`, `notes`).

## Step 5: Acceptance Criteria

- [ ] At least 48/50 sample URLs resolve to correct investigation content (>=96%).
- [ ] Any failures are cataloged with root-cause notes (`bad mapping`, `legacy page missing`, etc.).
- [ ] If failures >2, stop rollout and fix mapping data before any follow-up remediation run.

## Artifacts

- `data/logs/ntsb_source_urls_before.csv`
- `data/logs/ntsb_source_urls_after.csv`
- `data/logs/ntsb_source_urls_updated.csv`
- `data/logs/ntsb_source_urls_updated_sample50.csv`
