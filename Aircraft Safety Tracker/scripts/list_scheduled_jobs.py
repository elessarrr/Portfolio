#!/usr/bin/env python
"""
Inventory scheduled project jobs from launchd plists and cron.

This script is built incrementally under tasks-0022:
- Task 5.2 defines the IMPACT_REGISTRY used for human-readable impact notes.
- Task 5.3 parses launchd plist jobs from scripts/*.plist.

Launchd note:
- After creating a new plist, copy it to `~/Library/LaunchAgents/`.
- Load it with `launchctl load ~/Library/LaunchAgents/<label>.plist`.
- If running directly from this scripts directory, you may load by path too, but
  LaunchAgents is required for login-time activation.
"""

from pathlib import Path
import plistlib
import subprocess
from typing import Dict, List, Optional

IMPACT_REGISTRY = {
    "com.aircraftsafetytracker.weeklyupdate": "Runs Boeing/Airbus scrapers and data import",
    "update_data.sh": "Runs Boeing/Airbus scrapers and data import",
    "com.aircraftsafetytracker.wa-enrichment.daily": "Runs WA press enrichment pipeline",
    "enrich_wa_incidents.sh": "Runs WA press enrichment pipeline",
    "com.aircraftsafetytracker.linkvalidation.weekly": "Runs weekly incident link validation and NTSB cleanup",
    "validate_incident_links.py": "Revalidates incident source/report links and logs outcomes",
}

_WEEKDAY_NAME = {
    0: "Sunday",
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
}


def _format_launchd_schedule(interval: Optional[Dict]) -> str:
    if not isinstance(interval, dict):
        return "Unknown schedule"

    weekday = interval.get("Weekday")
    hour = interval.get("Hour")
    minute = interval.get("Minute")

    if hour is None or minute is None:
        return "Unknown schedule"

    try:
        hour_int = int(hour)
        minute_int = int(minute)
    except (TypeError, ValueError):
        return "Unknown schedule"

    time_part = f"{hour_int:02d}:{minute_int:02d}"
    if isinstance(weekday, int) and weekday in _WEEKDAY_NAME:
        return f"Every {_WEEKDAY_NAME[weekday]} at {time_part}"
    return f"Daily at {time_part}"


def collect_launchd_jobs(scripts_dir: Path) -> List[Dict[str, str]]:
    jobs: List[Dict[str, str]] = []
    for plist_path in sorted(scripts_dir.glob("*.plist")):
        with plist_path.open("rb") as handle:
            payload = plistlib.load(handle)

        label = payload.get("Label", plist_path.stem)
        schedule = _format_launchd_schedule(payload.get("StartCalendarInterval"))
        program_args = payload.get("ProgramArguments") or []
        command = program_args[0] if program_args else ""

        jobs.append(
            {
                "job_name": str(label),
                "schedule": schedule,
                "command": str(command),
            }
        )
    return jobs


def _format_cron_schedule(minute: str, hour: str, dom: str, month: str, dow: str) -> str:
    if minute.isdigit() and hour.isdigit() and dom == "*" and month == "*" and dow.isdigit():
        dow_int = int(dow)
        if dow_int in _WEEKDAY_NAME:
            return f"Every {_WEEKDAY_NAME[dow_int]} at {int(hour):02d}:{int(minute):02d}"
    if minute.isdigit() and hour.isdigit() and dom == "*" and month == "*" and dow == "*":
        return f"Daily at {int(hour):02d}:{int(minute):02d}"
    return f"Cron {minute} {hour} {dom} {month} {dow}"


def collect_cron_jobs(project_root: Path) -> List[Dict[str, str]]:
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []

    if result.returncode != 0:
        return []

    jobs: List[Dict[str, str]] = []
    project_root_str = str(project_root)
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if project_root_str not in line:
            continue

        parts = line.split()
        if len(parts) < 6:
            continue

        minute, hour, dom, month, dow = parts[:5]
        command = " ".join(parts[5:])
        schedule = _format_cron_schedule(minute, hour, dom, month, dow)

        jobs.append(
            {
                "job_name": "crontab",
                "schedule": schedule,
                "command": command,
            }
        )
    return jobs


def _impact_description(job_name: str, command: str) -> str:
    command_basename = Path(command.split()[0]).name if command else ""
    return (
        IMPACT_REGISTRY.get(job_name)
        or IMPACT_REGISTRY.get(command_basename)
        or "(no description)"
    )


def print_jobs_table(jobs: List[Dict[str, str]]) -> None:
    headers = ["Job Name", "Schedule", "Script / Command", "Impact Description"]
    rows = []
    for job in jobs:
        job_name = job.get("job_name", "")
        schedule = job.get("schedule", "")
        command = job.get("command", "")
        rows.append(
            [
                job_name,
                schedule,
                command,
                _impact_description(job_name, command),
            ]
        )

    if not rows:
        print("No scheduled jobs found.")
        return

    widths = [len(h) for h in headers]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def _fmt(values: List[str]) -> str:
        return " | ".join(value.ljust(widths[i]) for i, value in enumerate(values))

    print(_fmt(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(_fmt(row))


def main() -> int:
    scripts_dir = Path(__file__).resolve().parent
    project_root = scripts_dir.parent
    launchd_jobs = collect_launchd_jobs(scripts_dir)
    cron_jobs = collect_cron_jobs(project_root)
    print_jobs_table(launchd_jobs + cron_jobs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
