"""Resolve FAA AIDS make_model strings to v3 ASN+NTSB catalog pages (PRD 0007)."""

from __future__ import annotations

import re
from typing import FrozenSet, Optional, Set

from app.ingestion.ntsb_variant_resolution import (
    EC130_PAGE,
    is_ec130_make_model,
    is_generic_boeing_737,
    resolve_boeing_737_series_page,
    resolve_boeing_787_page,
)

SKIP_SUBSTRINGS = frozenset(
    {
        "AG-1",
        "X-45",
        "X45",
        "GLIDER",
        "PARAGLIDER",
        "ROCKET",
        "MISSILE",
        "MD600",
        "HYPER",
    }
)

STEARMAN_TARGETS = ("Boeing-Stearman Kaydet",)

FAMILY_FALLBACKS = (
    ("737", "Boeing 737"),
    ("727", "Boeing 727-200"),
    ("747", "Boeing 747-400"),
    ("757", "Boeing 757-200"),
    ("767", "Boeing 767-300"),
    ("777", "Boeing 777-200"),
    ("787", "Boeing 787"),
    ("717", "Boeing 717"),
    ("707", "Boeing 707-300"),
    ("A320", "Airbus A320"),
    ("A321", "Airbus A321"),
    ("A330", "Airbus A330-300"),
    ("A350", "Airbus A350-900"),
    ("A380", "Airbus A380"),
    ("A300", "Airbus A300-600"),
    ("A310", "Airbus A310"),
    ("A318", "Airbus A318"),
    ("A319", "Airbus A320"),
    ("AS350", "Airbus Helicopters AS350"),
    ("AS 350", "Airbus Helicopters AS350"),
    ("EC130", EC130_PAGE),
    ("BK117", "Airbus Helicopters BK117"),
)


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _pick_catalog(target: str, catalog: Set[str]) -> Optional[str]:
    if target in catalog:
        return target
    return None


def _series_from_digit(
    make_model: str, family: str, series_map: dict[str, str], catalog: Set[str]
) -> Optional[str]:
    u = _norm(make_model)
    if family not in u:
        return None
    m = re.search(rf"{family}(\d)", u)
    if m:
        page = series_map.get(m.group(1))
        return _pick_catalog(page, catalog) if page else None
    return None


def resolve_boeing_727_page(make_model: str, catalog: Set[str]) -> Optional[str]:
    u = _norm(make_model)
    if "727" not in u:
        return None
    page = _series_from_digit(
        make_model,
        "727",
        {"1": "Boeing 727-100", "2": "Boeing 727-200"},
        catalog,
    )
    if page:
        return page
    if "727100" in u or u.endswith("7271"):
        return _pick_catalog("Boeing 727-100", catalog)
    return _pick_catalog("Boeing 727-200", catalog)


def resolve_boeing_747_page(make_model: str, catalog: Set[str]) -> Optional[str]:
    u = _norm(make_model)
    if "747" not in u:
        return None
    if "7478" in u or "747-8" in make_model.upper():
        return _pick_catalog("Boeing 747-8", catalog)
    if "747SP" in u:
        return _pick_catalog("Boeing 747SP", catalog)
    if "747SR" in u:
        return _pick_catalog("Boeing 747SR", catalog)
    page = _series_from_digit(
        make_model,
        "747",
        {
            "1": "Boeing 747-100",
            "2": "Boeing 747-200",
            "3": "Boeing 747-300",
            "4": "Boeing 747-400",
        },
        catalog,
    )
    return page or _pick_catalog("Boeing 747-400", catalog)


def resolve_boeing_757_page(make_model: str, catalog: Set[str]) -> Optional[str]:
    u = _norm(make_model)
    if "757" not in u:
        return None
    if "7573" in u:
        return _pick_catalog("Boeing 757-300", catalog)
    return _pick_catalog("Boeing 757-200", catalog)


def resolve_boeing_767_page(make_model: str, catalog: Set[str]) -> Optional[str]:
    u = _norm(make_model)
    if "767" not in u:
        return None
    page = _series_from_digit(
        make_model,
        "767",
        {"2": "Boeing 767-200", "3": "Boeing 767-300", "4": "Boeing 767-400"},
        catalog,
    )
    return page or _pick_catalog("Boeing 767-300", catalog)


def resolve_boeing_777_page(make_model: str, catalog: Set[str]) -> Optional[str]:
    u = _norm(make_model)
    if "777" not in u:
        return None
    if "7779" in u or "777X" in u:
        return _pick_catalog("Boeing 777-9", catalog)
    if "7773" in u and "ER" in u:
        return _pick_catalog("Boeing 777-300ER", catalog)
    if "7773" in u:
        return _pick_catalog("Boeing 777-300", catalog)
    if "7772" in u and "LR" in u:
        return _pick_catalog("Boeing 777-200LR", catalog)
    return _pick_catalog("Boeing 777-200", catalog)


def resolve_airbus_heavy_page(make_model: str, catalog: Set[str]) -> Optional[str]:
    u = _norm(make_model)
    if "A380" in u or "388" in u:
        return _pick_catalog("Airbus A380", catalog)
    if "A350" in u:
        if "1000" in u or "K" in u[-4:]:
            return _pick_catalog("Airbus A350-1000", catalog)
        return _pick_catalog("Airbus A350-900", catalog)
    if "A340" in u:
        for target in (
            "Airbus A340-600",
            "Airbus A340-500",
            "Airbus A340-300",
            "Airbus A340-200",
        ):
            if target in catalog:
                return target
    if "A330" in u:
        for target in ("Airbus A330-900", "Airbus A330-800", "Airbus A330-300", "Airbus A330-200"):
            if target in catalog:
                return target
    if "A321" in u:
        if "NEO" in u or "N" in u[-3:]:
            return _pick_catalog("Airbus A321neo", catalog)
        return _pick_catalog("Airbus A321", catalog)
    if "A320" in u or "A319" in u or "A318" in u:
        if "NEO" in u:
            return _pick_catalog("Airbus A320neo", catalog)
        return _pick_catalog("Airbus A320", catalog)
    if "A300" in u or "A30B" in u:
        return _pick_catalog("Airbus A300-600", catalog)
    if "A310" in u:
        return _pick_catalog("Airbus A310", catalog)
    return None


def resolve_faa_canonical_model_name(
    faa_make_model: str, catalog: FrozenSet[str] | Set[str]
) -> Optional[str]:
    """Map FAA string to an existing catalog ``model_name``; None → skip at import."""
    if not faa_make_model:
        return None
    u = _norm(faa_make_model)
    if any(s in u for s in SKIP_SUBSTRINGS):
        return None
    if is_ec130_make_model(faa_make_model):
        return _pick_catalog(EC130_PAGE, catalog)
    for target in STEARMAN_TARGETS:
        if "A75" in u or "B75" in u or "PT17" in u:
            return _pick_catalog(target, catalog)

    for resolver in (
        lambda: resolve_boeing_737_series_page(faa_make_model),
        lambda: resolve_boeing_787_page(faa_make_model),
        lambda: resolve_boeing_727_page(faa_make_model, catalog),
        lambda: resolve_boeing_747_page(faa_make_model, catalog),
        lambda: resolve_boeing_757_page(faa_make_model, catalog),
        lambda: resolve_boeing_767_page(faa_make_model, catalog),
        lambda: resolve_boeing_777_page(faa_make_model, catalog),
        lambda: resolve_airbus_heavy_page(faa_make_model, catalog),
    ):
        page = resolver()
        if page and page in catalog:
            return page
        if page and page not in catalog and is_generic_boeing_737(faa_make_model):
            return _pick_catalog("Boeing 737", catalog)

    for needle, fallback in FAMILY_FALLBACKS:
        if needle.replace(" ", "") in u:
            hit = _pick_catalog(fallback, catalog)
            if hit:
                return hit

    for name in sorted(catalog, key=len, reverse=True):
        nu = _norm(name)
        if nu and (nu in u or u in nu):
            return name
    return None
