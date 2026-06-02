"""YAML config parsing + validation for the portable URL audit engine (PRD 0008)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import yaml


class ConfigError(ValueError):
    pass


def _require_dict(value: Any, path: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{path}: expected mapping/object")
    return value


def _require_list(value: Any, path: str) -> List[Any]:
    if not isinstance(value, list):
        raise ConfigError(f"{path}: expected list")
    return value


def _require_str(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{path}: expected non-empty string")
    return value.strip()


def _require_str_list(value: Any, path: str) -> List[str]:
    items = _require_list(value, path)
    out: List[str] = []
    for i, item in enumerate(items):
        out.append(_require_str(item, f"{path}[{i}]"))
    return out


def _require_int_list(value: Any, path: str) -> List[int]:
    items = _require_list(value, path)
    out: List[int] = []
    for i, item in enumerate(items):
        if isinstance(item, bool) or not isinstance(item, int):
            raise ConfigError(f"{path}[{i}]: expected int")
        out.append(int(item))
    return out


@dataclass(frozen=True)
class SourceConfig:
    name: str
    liveness_url: str
    url_modes: List[str]
    brief_markers: List[str]
    search_markers: List[str]
    not_working_markers: List[str]
    retryable_status_codes: List[int]
    retryable_body_markers: List[str]


@dataclass(frozen=True)
class AuditConfig:
    sources: List[SourceConfig]

    def source_by_name(self, name: str) -> Optional[SourceConfig]:
        for s in self.sources:
            if s.name == name:
                return s
        return None


def load_audit_config(path: Path | str) -> AuditConfig:
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"{path}: failed to read: {exc}") from exc

    try:
        raw = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc

    root = _require_dict(raw, f"{path}")

    sources_raw = root.get("sources")
    if sources_raw is None:
        raise ConfigError(f"{path}: missing required key 'sources'")
    sources_list = _require_list(sources_raw, f"{path}:sources")
    if not sources_list:
        raise ConfigError(f"{path}:sources: must contain at least one source")

    sources: List[SourceConfig] = []
    seen_names: set[str] = set()

    for idx, entry in enumerate(sources_list):
        obj = _require_dict(entry, f"{path}:sources[{idx}]")
        name = _require_str(obj.get("name"), f"{path}:sources[{idx}].name")
        if name in seen_names:
            raise ConfigError(f"{path}:sources[{idx}].name: duplicate name {name!r}")
        seen_names.add(name)

        liveness_url = _require_str(
            obj.get("liveness_url"), f"{path}:sources[{idx}].liveness_url"
        )
        url_modes = _require_str_list(
            obj.get("url_modes"), f"{path}:sources[{idx}].url_modes"
        )
        brief_markers = _require_str_list(
            obj.get("brief_markers", []), f"{path}:sources[{idx}].brief_markers"
        )
        search_markers = _require_str_list(
            obj.get("search_markers", []), f"{path}:sources[{idx}].search_markers"
        )
        not_working_markers = _require_str_list(
            obj.get("not_working_markers", []),
            f"{path}:sources[{idx}].not_working_markers",
        )

        retryable_status_codes = _require_int_list(
            obj.get("retryable_status_codes", []),
            f"{path}:sources[{idx}].retryable_status_codes",
        )
        retryable_body_markers = _require_str_list(
            obj.get("retryable_body_markers", []),
            f"{path}:sources[{idx}].retryable_body_markers",
        )

        sources.append(
            SourceConfig(
                name=name,
                liveness_url=liveness_url,
                url_modes=url_modes,
                brief_markers=brief_markers,
                search_markers=search_markers,
                not_working_markers=not_working_markers,
                retryable_status_codes=retryable_status_codes,
                retryable_body_markers=retryable_body_markers,
            )
        )

    return AuditConfig(sources=sources)

