"""Tests for .compound/scripts/validate-frontmatter.py parser-safety checks."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = PROJECT_ROOT / ".compound" / "scripts" / "validate-frontmatter.py"


def _run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_validator_passes_smoke_doc():
    doc = PROJECT_ROOT / "docs/solutions/conventions/compound-store-smoke-test.md"
    assert doc.is_file()
    result = _run(doc)
    assert result.returncode == 0, result.stderr
    assert "OK:" in result.stdout


def test_validator_rejects_unclosed_frontmatter(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("---\ntitle: oops\nbody without closing delimiter\n")
    result = _run(bad)
    assert result.returncode == 1
    assert "not closed" in result.stderr


def test_validator_rejects_unquoted_hash_in_value(tmp_path):
    bad = tmp_path / "bad-hash.md"
    bad.write_text("---\ntitle: foo # bar comment\n---\n\n# Body\n")
    result = _run(bad)
    assert result.returncode == 1
    assert " #" in result.stderr or "quote" in result.stderr.lower()


def test_validator_usage_error_without_path():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
