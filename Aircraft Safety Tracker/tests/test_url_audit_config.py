from __future__ import annotations

from pathlib import Path

import pytest

from url_audit.config import ConfigError, load_audit_config


def test_load_valid_config(tmp_path: Path) -> None:
    p = tmp_path / "audit_urls.yaml"
    p.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: faa_asias",
                "    liveness_url: https://www.asias.faa.gov/",
                "    url_modes: [brief, search]",
                "    brief_markers: [p12_aids_rprt_nbr]",
                "    search_markers: [search]",
                "    not_working_markers: [errors.edgesuite.net]",
                "    retryable_status_codes: [503, 504]",
                "    retryable_body_markers: [errors.edgesuite.net]",
                "",
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_audit_config(p)
    assert len(cfg.sources) == 1
    assert cfg.sources[0].name == "faa_asias"
    assert cfg.sources[0].url_modes == ["brief", "search"]


def test_missing_sources_key(tmp_path: Path) -> None:
    p = tmp_path / "audit_urls.yaml"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_audit_config(p)
    assert "missing required key 'sources'" in str(exc.value)


def test_duplicate_source_name_rejected(tmp_path: Path) -> None:
    p = tmp_path / "audit_urls.yaml"
    p.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: dup",
                "    liveness_url: https://example.com/",
                "    url_modes: [brief]",
                "  - name: dup",
                "    liveness_url: https://example.org/",
                "    url_modes: [brief]",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError) as exc:
        load_audit_config(p)
    assert "duplicate name" in str(exc.value)


def test_wrong_type_rejected(tmp_path: Path) -> None:
    p = tmp_path / "audit_urls.yaml"
    p.write_text(
        "\n".join(
            [
                "sources:",
                "  - name: x",
                "    liveness_url: https://example.com/",
                "    url_modes: brief",  # should be list
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError) as exc:
        load_audit_config(p)
    assert "expected list" in str(exc.value)

