"""CLI for the portable URL audit engine (PRD 0008)."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from url_audit.config import load_audit_config
from url_audit.engine import AuditRunOptions, LivenessError, run_audit_to_file
from url_audit.io import read_url_rows
from url_audit.db_writeback import (
    WriteBackError,
    WriteBackTarget,
    default_database_url,
    run_writeback,
)
from url_audit.merge import (
    MergeError,
    assert_safe_output_path,
    load_retry_rows,
    merge_audit_rows,
    resolve_merge_output_path,
)

BUCKET_HELP = """
Three-tier buckets:
  working_brief_report     — primary document reachable without extra UI steps
  working_search_prefill   — HTTP OK but intermediate/search page
  not_working              — 404, CDN/outage page, timeout, empty SPA, etc.

Liveness: probes each source's liveness_url (HTTP 2xx) before bulk audit.
Use --skip-liveness only when you accept auditing during a known outage.

Retry/merge:
  --retry-failures-from   Re-check only rows with bucket=not_working from a prior export.
  --merge-into            Merge retry results into the full export (use with retry).
  If --merge-into equals --retry-failures-from, output goes to {stem}_merged.jsonl beside that file.

Write-back (opt-in; default is audit-only):
  --write-back            After audit, update is_active in SQLite (requires confirmation).
  --dry-run               With --write-back: print change plan only, no DB writes.
  --database-url          SQLite URL (default: DATABASE_URL env).
  --write-back-source     Filter DB rows by source_name (e.g. FAA_AIDS).
  --yes-write-back        Skip confirmation prompt (use only in automation).
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="url_audit",
        description="Portable URL audit engine (PRD 0008)",
        epilog=BUCKET_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("audit_urls.yaml"),
        help="Path to audit_urls.yaml (default: ./audit_urls.yaml)",
    )
    p.add_argument(
        "--input",
        type=Path,
        help="Input JSONL/CSV with at least a 'url' field (not required with --retry-failures-from).",
    )
    p.add_argument(
        "--source",
        type=str,
        help="Source name from config (required to run an audit).",
    )
    p.add_argument(
        "--url-mode",
        type=str,
        help="URL mode (e.g. brief|search) (required to run an audit).",
    )
    p.add_argument(
        "--output",
        type=Path,
        help="Audit output JSONL (default: data/logs/url_audit_<date>.jsonl or _retry_ for retries)",
    )
    p.add_argument(
        "--retry-failures-from",
        type=Path,
        help="Prior audit JSONL; re-check only bucket=not_working rows.",
    )
    p.add_argument(
        "--merge-into",
        type=Path,
        help="With --retry-failures-from: merge retry results into this full export.",
    )
    p.add_argument("--concurrency", type=int, default=16, help="Worker count (default: 16)")
    p.add_argument("--timeout", type=int, default=15, help="HTTP timeout seconds (default: 15)")
    p.add_argument("--no-jitter", action="store_true", help="Disable 50–200ms pre-request jitter")
    p.add_argument("--no-retry", action="store_true", help="Disable single retry on transient errors")
    p.add_argument(
        "--skip-liveness",
        action="store_true",
        help="Skip liveness probe (not recommended during outages)",
    )
    p.add_argument(
        "--write-back",
        action="store_true",
        help="After audit, apply is_active updates to SQLite (ask-before-write)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="With --write-back: show planned DB changes without writing",
    )
    p.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="SQLite database URL for write-back (default: DATABASE_URL)",
    )
    p.add_argument(
        "--write-back-source",
        type=str,
        default=None,
        help="Filter DB rows by source_name column value",
    )
    p.add_argument(
        "--write-back-match-field",
        type=str,
        default="source_record_id",
        help="Audit JSONL field used to match DB rows (default: source_record_id)",
    )
    p.add_argument(
        "--yes-write-back",
        action="store_true",
        help="Skip write-back confirmation prompt",
    )
    return p


def _default_output_path(*, retry: bool) -> Path:
    today = date.today().isoformat()
    name = f"url_audit_retry_{today}.jsonl" if retry else f"url_audit_{today}.jsonl"
    return Path("data/logs") / name


def _print_bucket_summary(results: list[dict[str, object]]) -> None:
    buckets: dict[str, int] = {}
    for row in results:
        b = str(row.get("bucket") or "")
        buckets[b] = buckets.get(b, 0) + 1
    for name in sorted(buckets):
        print(f"  {name}: {buckets[name]}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg = load_audit_config(args.config)

    if not args.input and not args.retry_failures_from:
        print(f"Loaded config {args.config} with {len(cfg.sources)} source(s).")
        print("Provide --input or --retry-failures-from (plus --source and --url-mode) to run.")
        return 0

    if not args.source:
        parser.error("--source is required to run an audit")
    if not args.url_mode:
        parser.error("--url-mode is required to run an audit")

    source = cfg.source_by_name(args.source)
    if source is None:
        parser.error(f"--source {args.source!r} not found in config")
    if args.url_mode not in source.url_modes:
        parser.error(
            f"--url-mode {args.url_mode!r} not allowed for source {args.source!r} "
            f"(allowed: {source.url_modes})"
        )

    is_retry = args.retry_failures_from is not None
    try:
        if is_retry:
            rows = load_retry_rows(args.retry_failures_from, url_mode=args.url_mode)
        else:
            rows = read_url_rows(args.input)
    except (MergeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    output = args.output or _default_output_path(retry=is_retry)
    protected: list[Path] = []
    if args.input:
        protected.append(args.input)
    if args.retry_failures_from:
        protected.append(args.retry_failures_from)

    try:
        assert_safe_output_path(output, protected)
    except MergeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    options = AuditRunOptions(
        concurrency=args.concurrency,
        timeout_seconds=args.timeout,
        use_jitter=not args.no_jitter,
        use_retry=not args.no_retry,
        skip_liveness=args.skip_liveness,
    )

    try:
        results = run_audit_to_file(
            source,
            rows,
            url_mode=args.url_mode,
            output_path=output,
            options=options,
        )
    except LivenessError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        f"Audited {len(results)} URL(s) → {output} "
        f"(source={source.name!r}, url_mode={args.url_mode!r}"
        f"{', retry' if is_retry else ''})."
    )
    _print_bucket_summary(results)

    if args.retry_failures_from and args.merge_into:
        merged_path = resolve_merge_output_path(args.merge_into, args.retry_failures_from)
        try:
            assert_safe_output_path(merged_path, protected, label="Merged output")
            merge_audit_rows(args.retry_failures_from, results, merged_path)
        except MergeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Merged audit → {merged_path}")

    if args.write_back:
        database_url = args.database_url or default_database_url()
        if not database_url:
            print(
                "ERROR: --write-back requires --database-url or DATABASE_URL",
                file=sys.stderr,
            )
            return 1
        target = WriteBackTarget(
            source_name=args.write_back_source,
            match_field=args.write_back_match_field,
        )
        try:
            run_writeback(
                database_url,
                results,
                target=target,
                url_mode=args.url_mode,
                dry_run=args.dry_run,
                assume_yes=args.yes_write_back,
            )
        except WriteBackError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    return 0
