from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from url_audit.config import SourceConfig
from url_audit.engine import (
    AuditRunOptions,
    LivenessError,
    probe_liveness,
    run_audit,
    run_audit_to_file,
)
from url_audit.http import FetchResult
from url_audit.io import UrlRow

FetchMap = Dict[str, FetchResult]


def _source() -> SourceConfig:
    return SourceConfig(
        name="stub",
        liveness_url="https://liveness.example/",
        url_modes=["brief"],
        brief_markers=["example domain"],
        search_markers=["search form"],
        not_working_markers=["cdn error"],
        retryable_status_codes=[503],
        retryable_body_markers=["cdn error"],
    )


def _fetcher(responses: FetchMap):
    def fetch(url: str) -> FetchResult:
        return responses.get(url, (404, "missing"))

    return fetch


def test_liveness_abort_on_non_2xx() -> None:
    source = _source()
    with pytest.raises(LivenessError):
        probe_liveness(source, _fetcher({source.liveness_url: (503, "down")}))


def test_liveness_skip() -> None:
    source = _source()
    probe_liveness(source, _fetcher({}), skip=True)


def test_run_audit_output_schema(tmp_path: Path) -> None:
    source = _source()
    rows = [
        UrlRow(url="https://example.com/page", metadata={"source_record_id": "abc"}),
    ]
    responses: FetchMap = {
        source.liveness_url: (200, "ok"),
        "https://example.com/page": (200, "Example Domain landing"),
    }
    results = run_audit(
        source,
        rows,
        url_mode="brief",
        options=AuditRunOptions(skip_liveness=False, use_jitter=False, use_retry=False),
        fetcher=_fetcher(responses),
    )
    assert len(results) == 1
    row = results[0]
    for field in (
        "url",
        "http_status",
        "link_viable",
        "product_viable",
        "bucket",
        "reason",
        "checked_at",
        "url_mode",
    ):
        assert field in row
    assert row["url"] == "https://example.com/page"
    assert row["url_mode"] == "brief"
    assert row["source_record_id"] == "abc"
    assert row["bucket"] == "working_brief_report"
    assert row["product_viable"] is True


def test_run_audit_writes_jsonl(tmp_path: Path) -> None:
    source = _source()
    out = tmp_path / "out.jsonl"
    rows = [UrlRow(url="https://example.com/x", metadata={})]
    responses: FetchMap = {
        source.liveness_url: (200, ""),
        "https://example.com/x": (200, "Example Domain"),
    }
    run_audit_to_file(
        source,
        rows,
        url_mode="brief",
        output_path=out,
        options=AuditRunOptions(skip_liveness=False, use_jitter=False, use_retry=False),
        fetcher=_fetcher(responses),
    )
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert '"bucket": "working_brief_report"' in lines[0]
