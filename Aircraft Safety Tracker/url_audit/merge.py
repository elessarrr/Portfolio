"""Retry + merge helpers for portable URL audit exports (PRD 0008)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from url_audit.classify import BUCKET_NOT_WORKING
from url_audit.io import UrlRow, read_audit_jsonl, write_audit_jsonl

MergeKey = Tuple[str, str]


class MergeError(ValueError):
    pass


def load_retry_rows(
    audit_path: Path | str,
    *,
    url_mode: Optional[str] = None,
) -> List[UrlRow]:
    """Load prior audit JSONL and return only ``not_working`` rows as UrlRow input."""
    rows = read_audit_jsonl(audit_path)
    failed = [r for r in rows if r.get("bucket") == BUCKET_NOT_WORKING]
    if url_mode is not None:
        failed = [
            r
            for r in failed
            if r.get("url_mode") in (None, url_mode)
        ]
    if not failed:
        raise MergeError(f"No {BUCKET_NOT_WORKING!r} rows in {audit_path}")
    out: List[UrlRow] = []
    for row in failed:
        url = str(row.get("url") or "").strip()
        if not url:
            continue
        meta = {k: v for k, v in row.items() if k != "url"}
        out.append(UrlRow(url=url, metadata=meta))
    if not out:
        raise MergeError(f"No rows with a url field in {audit_path}")
    return out


def merge_key(row: Dict[str, object], *, match_url_mode: bool) -> MergeKey | Tuple[str]:
    url = str(row.get("url") or "")
    if match_url_mode:
        return (url, str(row.get("url_mode") or ""))
    return (url,)


def resolve_merge_output_path(merge_into: Path, retry_from: Path) -> Path:
    """If merge target equals the retry base file, write ``{stem}_merged.jsonl`` beside it."""
    if merge_into.resolve() == retry_from.resolve():
        return retry_from.with_name(f"{retry_from.stem}_merged.jsonl")
    return merge_into


def assert_safe_output_path(
    output: Path,
    protected: Sequence[Path],
    *,
    label: str = "output",
) -> None:
    """Refuse to write *output* when it would overwrite a protected input file."""
    out = output.resolve()
    for path in protected:
        if path is not None and out == Path(path).resolve():
            raise MergeError(
                f"{label} {output} would overwrite protected input {path}; "
                "choose a different path or use merge naming rules."
            )


def merge_audit_rows(
    base_path: Path | str,
    updates: Sequence[Dict[str, object]],
    merged_path: Path | str,
    *,
    match_url_mode: bool = True,
) -> Path:
    """Merge *updates* into the full export at *base_path*; write *merged_path*."""
    base_path = Path(base_path)
    merged_path = Path(merged_path)
    protected = [base_path]
    assert_safe_output_path(merged_path, protected, label="Merged output")

    by_key: Dict[MergeKey | Tuple[str], Dict[str, object]] = {}
    for row in updates:
        key = merge_key(row, match_url_mode=match_url_mode)
        by_key[key] = dict(row)

    merged_rows: List[Dict[str, object]] = []
    for row in read_audit_jsonl(base_path):
        key = merge_key(row, match_url_mode=match_url_mode)
        if key in by_key:
            merged_rows.append(by_key.pop(key))
        else:
            merged_rows.append(row)

    for leftover in by_key.values():
        merged_rows.append(leftover)

    write_audit_jsonl(merged_path, merged_rows)
    return merged_path
