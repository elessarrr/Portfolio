from __future__ import annotations

import json
from pathlib import Path

import pytest

from url_audit.io import write_audit_jsonl
from url_audit.merge import (
    MergeError,
    assert_safe_output_path,
    load_retry_rows,
    merge_audit_rows,
    resolve_merge_output_path,
)


def _write_audit(path: Path, rows: list[dict]) -> None:
    write_audit_jsonl(path, rows)


def test_resolve_merge_output_path_same_file(tmp_path: Path) -> None:
    base = tmp_path / "audit.jsonl"
    base.write_text("{}\n", encoding="utf-8")
    merged = resolve_merge_output_path(base, base)
    assert merged == tmp_path / "audit_merged.jsonl"


def test_resolve_merge_output_path_distinct_files(tmp_path: Path) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    assert resolve_merge_output_path(b, a) == b


def test_assert_safe_output_rejects_clobber(tmp_path: Path) -> None:
    base = tmp_path / "base.jsonl"
    with pytest.raises(MergeError) as exc:
        assert_safe_output_path(base, [base])
    assert "overwrite" in str(exc.value)


def test_load_retry_rows_filters_not_working(tmp_path: Path) -> None:
    p = tmp_path / "prior.jsonl"
    _write_audit(
        p,
        [
            {"url": "https://a", "bucket": "not_working", "url_mode": "brief"},
            {"url": "https://b", "bucket": "working_brief_report", "url_mode": "brief"},
        ],
    )
    rows = load_retry_rows(p)
    assert len(rows) == 1
    assert rows[0].url == "https://a"


def test_load_retry_rows_empty_raises(tmp_path: Path) -> None:
    p = tmp_path / "prior.jsonl"
    _write_audit(p, [{"url": "https://b", "bucket": "working_brief_report"}])
    with pytest.raises(MergeError):
        load_retry_rows(p)


def test_merge_audit_rows_by_url_and_mode(tmp_path: Path) -> None:
    base = tmp_path / "full.jsonl"
    _write_audit(
        base,
        [
            {"url": "https://a", "bucket": "not_working", "url_mode": "brief", "n": 1},
            {"url": "https://b", "bucket": "working_brief_report", "url_mode": "brief", "n": 2},
        ],
    )
    updates = [
        {
            "url": "https://a",
            "bucket": "working_brief_report",
            "url_mode": "brief",
            "n": 99,
        },
    ]
    out = tmp_path / "merged.jsonl"
    merge_audit_rows(base, updates, out)
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    by_url = {r["url"]: r for r in rows}
    assert by_url["https://a"]["bucket"] == "working_brief_report"
    assert by_url["https://a"]["n"] == 99
    assert by_url["https://b"]["n"] == 2


def test_merge_refuses_to_clobber_base(tmp_path: Path) -> None:
    base = tmp_path / "full.jsonl"
    _write_audit(base, [{"url": "https://a", "bucket": "not_working"}])
    with pytest.raises(MergeError):
        merge_audit_rows(base, [{"url": "https://a", "bucket": "working_brief_report"}], base)
