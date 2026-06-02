"""Input/output helpers for the portable URL audit engine (PRD 0008)."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class UrlRow:
    url: str
    metadata: Dict[str, object]


def read_audit_jsonl(path: Path | str) -> List[Dict[str, object]]:
    """Read prior audit result JSONL (full row objects, including bucket/url_mode)."""
    path = Path(path)
    rows: List[Dict[str, object]] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(obj)
    return rows


def read_url_rows(path: Path | str) -> List[UrlRow]:
    """Read JSONL or CSV input into UrlRow list (FR-2.2)."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return _read_jsonl(path)
    if suffix == ".csv":
        return _read_csv(path)
    raise ValueError(f"{path}: unsupported input type (expected .jsonl or .csv)")


def _read_jsonl(path: Path) -> List[UrlRow]:
    rows: List[UrlRow] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            url = str(obj.get("url") or "").strip()
            if not url:
                raise ValueError(f"{path}:{line_no}: missing required field 'url'")
            meta = {k: v for k, v in obj.items() if k != "url"}
            rows.append(UrlRow(url=url, metadata=meta))
    return rows


def _read_csv(path: Path) -> List[UrlRow]:
    rows: List[UrlRow] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"{path}: missing header row")
        if "url" not in (name.strip() for name in reader.fieldnames):
            raise ValueError(f"{path}: missing required column 'url'")
        for row in reader:
            url = str(row.get("url") or "").strip()
            if not url:
                continue
            meta = {k: v for k, v in row.items() if k != "url"}
            rows.append(UrlRow(url=url, metadata=meta))
    return rows


def write_audit_jsonl(path: Path | str, rows: Iterable[Dict[str, object]]) -> None:
    """Write audit result rows as JSONL (one object per line)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

