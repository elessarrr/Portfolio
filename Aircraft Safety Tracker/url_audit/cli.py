"""CLI for the portable URL audit engine (PRD 0008).

v1 CLI focuses on safe config + input loading. Audit execution is implemented
in subsequent tasks (engine, classify, merge, write-back).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from url_audit.config import load_audit_config
from url_audit.io import read_url_rows


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="url_audit", description="Portable URL audit engine (PRD 0008)")
    p.add_argument(
        "--config",
        type=Path,
        default=Path("audit_urls.yaml"),
        help="Path to audit_urls.yaml (default: ./audit_urls.yaml)",
    )
    p.add_argument(
        "--input",
        type=Path,
        help="Optional input JSONL/CSV containing at least a 'url' field/column.",
    )
    p.add_argument(
        "--source",
        type=str,
        help="Source name to use from config (required when --input is provided).",
    )
    p.add_argument(
        "--url-mode",
        type=str,
        help="URL mode to use (e.g. brief|search) (required when --input is provided).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg = load_audit_config(args.config)

    if args.input:
        if not args.source:
            parser.error("--source is required when --input is provided")
        if not args.url_mode:
            parser.error("--url-mode is required when --input is provided")

        source = cfg.source_by_name(args.source)
        if source is None:
            parser.error(f"--source {args.source!r} not found in config")
        if args.url_mode not in source.url_modes:
            parser.error(
                f"--url-mode {args.url_mode!r} not allowed for source {args.source!r} (allowed: {source.url_modes})"
            )

        rows = read_url_rows(args.input)
        print(
            f"Loaded {len(rows)} URL rows from {args.input} (source={source.name!r}, url_mode={args.url_mode!r})."
        )
        return 0

    # No input: config validates; audit execution is added in later tasks.
    print(f"Loaded config {args.config} with {len(cfg.sources)} source(s).")
    return 0

