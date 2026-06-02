"""Optional SQLite DB write-back for URL audit results (PRD 0008, ask-before-write)."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from url_audit.classify import BUCKET_BRIEF, BUCKET_NOT_WORKING

ConfirmFn = Callable[[str], bool]


class WriteBackError(ValueError):
    pass


@dataclass(frozen=True)
class WriteBackTarget:
    """SQLite table/columns used for write-back."""

    table: str = "incident_source"
    source_name_column: str = "source_name"
    source_record_id_column: str = "source_record_id"
    is_active_column: str = "is_active"
    source_name: Optional[str] = None
    match_field: str = "source_record_id"


@dataclass
class WriteBackSummary:
    true_to_false: int = 0
    false_to_true: int = 0
    unchanged: int = 0
    skipped: int = 0
    matched: int = 0


def bucket_should_remain_active(bucket: str, url_mode: str) -> bool:
    """Map audit bucket + url_mode to ``is_active`` (generic-url-audit semantics)."""
    if bucket == BUCKET_NOT_WORKING:
        return False
    if url_mode == "brief":
        return bucket == BUCKET_BRIEF
    return True


def active_mapping_description(url_mode: str) -> str:
    if url_mode == "brief":
        return (
            f"is_active=True only when bucket={BUCKET_BRIEF!r}; "
            f"all other buckets → is_active=False"
        )
    return (
        f"is_active=True when bucket != {BUCKET_NOT_WORKING!r}; "
        f"{BUCKET_NOT_WORKING!r} → is_active=False"
    )


def parse_sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise WriteBackError(
            f"Unsupported database URL {database_url!r}; v1 write-back supports sqlite:/// only."
        )
    raw = database_url[len(prefix) :]
    if raw.startswith("/"):
        return Path(raw)
    return Path(raw)


def build_confirmation_message(
    *,
    database_url: str,
    target: WriteBackTarget,
    url_mode: str,
    summary: WriteBackSummary,
) -> str:
    lines = [
        "URL audit DB write-back confirmation",
        f"  Database:     {database_url}",
        f"  Table:        {target.table}",
        f"  Columns:      {target.is_active_column} (and match on {target.source_record_id_column})",
        f"  Source filter:{target.source_name or '(any)'}",
        f"  Match field:  audit row field {target.match_field!r}",
        f"  URL mode:     {url_mode}",
        f"  Active rule:  {active_mapping_description(url_mode)}",
        "",
        "Planned changes:",
        f"  is_active True → False:  {summary.true_to_false}",
        f"  is_active False → True:  {summary.false_to_true}",
        f"  unchanged:               {summary.unchanged}",
        f"  skipped (no DB row):     {summary.skipped}",
        "",
        "Proceed with these updates?",
    ]
    return "\n".join(lines)


def prompt_confirm(message: str, *, confirm: Optional[ConfirmFn] = None) -> bool:
    if confirm is not None:
        return confirm(message)
    while True:
        answer = input(f"{message}\nApply write-back? [y/N]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("", "n", "no"):
            return False


def plan_sqlite_writeback(
    conn: sqlite3.Connection,
    results: Sequence[Dict[str, object]],
    *,
    target: WriteBackTarget,
    url_mode: str,
) -> Tuple[WriteBackSummary, List[Tuple[str, bool, bool]]]:
    """Return summary and list of (source_record_id, current_active, new_active) changes."""
    summary = WriteBackSummary()
    changes: List[Tuple[str, bool, bool]] = []

    where = ""
    params: List[object] = []
    if target.source_name:
        where = f" WHERE {target.source_name_column} = ?"
        params.append(target.source_name)

    sql = (
        f"SELECT {target.source_record_id_column}, {target.is_active_column} "
        f"FROM {target.table}{where}"
    )
    cur = conn.execute(sql, params)
    by_id: Dict[str, bool] = {}
    for row in cur.fetchall():
        sid = str(row[0] or "")
        if not sid:
            continue
        by_id[sid] = bool(row[1])

    seen: set[str] = set()
    for result in results:
        sid = str(result.get(target.match_field) or "").strip()
        if not sid or sid in seen:
            continue
        seen.add(sid)
        bucket = str(result.get("bucket") or BUCKET_NOT_WORKING)
        new_active = bucket_should_remain_active(bucket, url_mode)
        current = by_id.get(sid)
        if current is None:
            summary.skipped += 1
            continue
        summary.matched += 1
        if current == new_active:
            summary.unchanged += 1
            continue
        if current and not new_active:
            summary.true_to_false += 1
        else:
            summary.false_to_true += 1
        changes.append((sid, current, new_active))

    return summary, changes


def apply_sqlite_writeback(
    conn: sqlite3.Connection,
    changes: Sequence[Tuple[str, bool, bool]],
    *,
    target: WriteBackTarget,
    dry_run: bool = False,
) -> WriteBackSummary:
    """Apply planned ``is_active`` updates; no-op when *dry_run*."""
    summary = WriteBackSummary(matched=len(changes))
    for sid, current, new_active in changes:
        if current == new_active:
            summary.unchanged += 1
            continue
        if current and not new_active:
            summary.true_to_false += 1
        else:
            summary.false_to_true += 1
        if dry_run:
            continue
        sql = (
            f"UPDATE {target.table} SET {target.is_active_column} = ? "
            f"WHERE {target.source_record_id_column} = ?"
        )
        params: List[object] = [1 if new_active else 0, sid]
        if target.source_name:
            sql += f" AND {target.source_name_column} = ?"
            params.append(target.source_name)
        conn.execute(sql, params)
    if not dry_run and changes:
        conn.commit()
    return summary


def run_writeback(
    database_url: str,
    results: Sequence[Dict[str, object]],
    *,
    target: WriteBackTarget,
    url_mode: str,
    dry_run: bool = False,
    confirm: Optional[ConfirmFn] = None,
    assume_yes: bool = False,
) -> WriteBackSummary:
    """Plan (and optionally apply) SQLite write-back after user confirmation."""
    db_path = parse_sqlite_path(database_url)
    if not db_path.exists():
        raise WriteBackError(f"Database file not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        plan_summary, changes = plan_sqlite_writeback(
            conn, results, target=target, url_mode=url_mode
        )
        message = build_confirmation_message(
            database_url=database_url,
            target=target,
            url_mode=url_mode,
            summary=plan_summary,
        )
        if dry_run:
            print(message)
            print("\n--dry-run: no database writes performed.")
            return plan_summary

        if not changes:
            print(message)
            print("\nNo is_active changes needed.")
            return plan_summary

        if not assume_yes and not prompt_confirm(message, confirm=confirm):
            print("Write-back aborted (not confirmed).")
            return plan_summary

        applied = apply_sqlite_writeback(conn, changes, target=target, dry_run=False)
        print(
            f"\nWrite-back applied: True→False={applied.true_to_false}, "
            f"False→True={applied.false_to_true}, unchanged={plan_summary.unchanged}"
        )
        return applied
    finally:
        conn.close()


def default_database_url() -> Optional[str]:
    return os.environ.get("DATABASE_URL")
