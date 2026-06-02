#!/usr/bin/env python3
"""Portable URL audit engine entrypoint (PRD 0008).

This wrapper is designed to be copy/pasted into new repos. It prefers running the
module (`python -m url_audit`) when available and otherwise can scaffold files
on request.
"""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ToolingDetection:
    has_script_entrypoint: bool
    has_module_entrypoint: bool


def detect_tooling(repo_root: Path) -> ToolingDetection:
    """Detect whether audit tooling exists in the current repo (FR-1.1)."""
    script_path = repo_root / "scripts" / "audit_urls.py"
    has_script = script_path.exists()

    try:
        importlib.import_module("url_audit")
        has_module = True
    except Exception:
        has_module = False

    return ToolingDetection(
        has_script_entrypoint=has_script,
        has_module_entrypoint=has_module,
    )


def _repo_root() -> Path:
    # Assumes `scripts/audit_urls.py` lives under repo root.
    return Path(__file__).resolve().parents[1]

def _prompt_yes_no(question: str) -> bool:
    while True:
        answer = input(f"{question} [y/N]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("", "n", "no"):
            return False


def _write_if_missing(path: Path, content: str) -> bool:
    """Write file only if missing. Returns True if created."""
    if path.exists():
        print(f"- exists, skipping: {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"- created: {path}")
    return True


def scaffold_portable_engine(repo_root: Path, *, assume_yes: bool = False) -> bool:
    """Scaffold portable audit engine files (FR-1.2, FR-1.3, FR-1.4).

    Returns True if any file was created.
    """
    targets = [
        repo_root / "audit_urls.yaml",
        repo_root / "url_audit" / "__init__.py",
        repo_root / "url_audit" / "__main__.py",
        repo_root / "url_audit" / "config.py",
        repo_root / "url_audit" / "engine.py",
        repo_root / "url_audit" / "classify.py",
        repo_root / "url_audit" / "merge.py",
        repo_root / "url_audit" / "io.py",
        repo_root / "url_audit" / "http.py",
        repo_root / "url_audit" / "db_writeback.py",
        repo_root / "tests" / "test_url_audit_engine.py",
    ]

    print("Scaffold plan (will create missing files only):")
    for t in targets:
        if not t.exists():
            print(f"- would create: {t}")
    if not assume_yes and not _prompt_yes_no("Proceed with scaffolding?"):
        print("Aborted (no files created).")
        return False

    created_any = False

    created_any |= _write_if_missing(
        repo_root / "audit_urls.yaml",
        "\n".join(
            [
                "# Portable URL audit config (PRD 0008)",
                "sources:",
                "  - name: example",
                "    liveness_url: https://example.com/",
                "    url_modes: [brief]",
                "    brief_markers: [example domain]",
                "    search_markers: [search]",
                "    not_working_markers: [errors.edgesuite.net]",
                "",
            ]
        ),
    )

    created_any |= _write_if_missing(
        repo_root / "url_audit" / "__init__.py",
        "\n".join(
            [
                '"""Portable URL audit engine (PRD 0008)."""',
                "",
                "from __future__ import annotations",
                "",
                "__all__ = [\"__version__\"]",
                "",
                "__version__ = \"0.1.0\"",
                "",
            ]
        ),
    )

    created_any |= _write_if_missing(
        repo_root / "url_audit" / "__main__.py",
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from url_audit.cli import main",
                "",
                "if __name__ == \"__main__\":",
                "    raise SystemExit(main())",
                "",
            ]
        ),
    )

    # Placeholder modules; will be implemented by subsequent tasks.
    for rel in (
        "config.py",
        "engine.py",
        "classify.py",
        "merge.py",
        "io.py",
        "http.py",
        "db_writeback.py",
    ):
        created_any |= _write_if_missing(
            repo_root / "url_audit" / rel,
            "\n".join(
                [
                    "from __future__ import annotations",
                    "",
                    "# TODO(PRD-0008): implemented in subsequent tasks.",
                    "",
                ]
            ),
        )

    created_any |= _write_if_missing(
        repo_root / "tests" / "test_url_audit_engine.py",
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "def test_scaffold_placeholder() -> None:",
                "    assert True",
                "",
            ]
        ),
    )

    return created_any


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = _repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scaffold", action="store_true", help="Create missing engine files in-place.")
    parser.add_argument(
        "--scaffold-only",
        action="store_true",
        help="Scaffold then exit (do not run an audit).",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Assume yes for scaffolding prompts.",
    )
    args, passthrough = parser.parse_known_args(argv)

    detection = detect_tooling(root)

    if args.scaffold or (not detection.has_module_entrypoint and args.scaffold_only):
        scaffold_portable_engine(root, assume_yes=args.yes)
        if args.scaffold_only:
            return 0
        # Re-detect after scaffold attempt.
        detection = detect_tooling(root)

    # If the module exists, prefer it for real work.
    if detection.has_module_entrypoint:
        cmd = [sys.executable, "-m", "url_audit"] + passthrough
        return subprocess.call(cmd)

    # Otherwise, give a clear error (scaffolding implemented in later tasks).
    sys.stderr.write(
        "ERROR: url_audit module not found. Scaffold it first (PRD 0008 FR-1).\n"
    )
    sys.stderr.write(
        "       Expected `url_audit/` package and `audit_urls.yaml` in repo root.\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

