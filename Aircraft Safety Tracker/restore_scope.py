import subprocess
from pathlib import Path

ROOT = Path("/Users/Bhavesh/Documents/GitHub/Portfoilo")

KEEP = {
    "Aircraft Safety Tracker/.pre-commit-config.yaml",
    "Aircraft Safety Tracker/Planning/Reviews/Prioritised_remediation_plan_5Apr2026.md",
    "Aircraft Safety Tracker/app/__init__.py",
    "Aircraft Safety Tracker/app/models.py",
    "Aircraft Safety Tracker/app/routes.py",
    "Aircraft Safety Tracker/app/static/js/main.js",
    "Aircraft Safety Tracker/app/services/deepseek.py",
    "Aircraft Safety Tracker/app/services/gemini.py",
    "Aircraft Safety Tracker/app/services/report_analyzer.py",
    "Aircraft Safety Tracker/app/ingestion/bulk/faa_aids_bulk.py",
    "Aircraft Safety Tracker/app/ingestion/bulk/faa_sdr_bulk.py",
    "Aircraft Safety Tracker/app/ingestion/bulk/ntsb_bulk.py",
    "Aircraft Safety Tracker/app/ingestion/importers/faa_sdr_importer.py",
    "Aircraft Safety Tracker/app/ingestion/importers/ntsb_importer.py",
    "Aircraft Safety Tracker/config.py",
    "Aircraft Safety Tracker/learnings_from_errors.md",
    "Aircraft Safety Tracker/pyproject.toml",
    "Aircraft Safety Tracker/scripts/import_data.py",
    "Aircraft Safety Tracker/tests/test_deepseek.py",
    "Aircraft Safety Tracker/tests/test_faa_sdr_importer.py",
    "Aircraft Safety Tracker/tests/test_report_analyzer_service.py",
    "Aircraft Safety Tracker/tests/test_routes.py",
    "Aircraft Safety Tracker/tests/test_security.py",
    "Aircraft Safety Tracker/tests/test_summary.py",
}

status = subprocess.check_output(
    ["git", "status", "--porcelain", "-z"], cwd=ROOT, text=False
).split(b"\x00")

restore_paths = []
untracked_paths = []

i = 0
while i < len(status):
    entry = status[i]
    if not entry:
        i += 1
        continue

    rec = entry.decode("utf-8", errors="replace")
    code = rec[:2]
    path = rec[3:]

    if code.startswith("R") or code.startswith("C"):
        i += 1
        if i < len(status) and status[i]:
            path = status[i].decode("utf-8", errors="replace")

    if code == "??":
        if path not in KEEP:
            untracked_paths.append(path)
    else:
        if path not in KEEP:
            restore_paths.append(path)
    i += 1

for path in restore_paths:
    subprocess.run(
        ["git", "restore", "--worktree", "--staged", "--", path],
        cwd=ROOT,
        check=False,
    )

print("restored_tracked", len(restore_paths))
for path in untracked_paths:
    print("UNTRACKED", path)
