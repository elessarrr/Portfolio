"""Resolve NTSB make_model strings to catalog aircraft page names (PRD 0006.3).

Rules (product-approved 2026-06):
- Boeing 737 customer codes (e.g. 737-301, 737-7H4): first digit after 737 → series page (-300, -700).
- Generic ``BOEING 737`` / ``Boeing 737`` only: family page ``Boeing 737``.
- Boeing 787: map to -8 / -9 / -10 only when that variant appears in the string; otherwise ``Boeing 787``.
- Airbus EC130 strings: ``Airbus Helicopters EC130`` (not EC135).
"""

from __future__ import annotations

import re
from typing import Optional

BOEING_737_SERIES: dict[str, str] = {
    "1": "Boeing 737-100",
    "2": "Boeing 737-200",
    "3": "Boeing 737-300",
    "4": "Boeing 737-400",
    "5": "Boeing 737-500",
    "6": "Boeing 737-600",
    "7": "Boeing 737-700",
    "8": "Boeing 737-800",
    "9": "Boeing 737-900",
}

GENERIC_737_STRINGS = frozenset({"BOEING 737", "B737", "BOEING B737", "Boeing 737"})

EC130_PAGE = "Airbus Helicopters EC130"
EC130_CREATE_MANUFACTURER = "Airbus"


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def is_generic_boeing_737(make_model: str) -> bool:
    return (make_model or "").strip().upper() in GENERIC_737_STRINGS


def is_ec130_make_model(make_model: str) -> bool:
    """True for EC130 / EC-130 / EC 130 (not EC135)."""
    u = _norm(make_model)
    if "EC135" in u or re.search(r"EC135T", u):
        return False
    return bool(re.search(r"EC130", u) or re.search(r"EC130T", u))


def resolve_boeing_737_series_page(make_model: str) -> Optional[str]:
    if is_generic_boeing_737(make_model):
        return "Boeing 737"
    u = _norm(make_model)
    if "737" not in u:
        return None
    m = re.search(r"737[- ]?(\d)", u)
    if not m:
        return None
    return BOEING_737_SERIES.get(m.group(1))


def resolve_boeing_787_page(make_model: str) -> Optional[str]:
    u = _norm(make_model)
    if "787" not in u:
        return None
    if re.search(r"787[- ]?10", u):
        return "Boeing 787-10 Dreamliner"
    if re.search(r"787[- ]?9", u):
        return "Boeing 787-9 Dreamliner"
    if re.search(r"787[- ]?8", u):
        return "Boeing 787-8 Dreamliner"
    return "Boeing 787"


def resolve_canonical_model_name(make_model: str) -> Optional[str]:
    """Best catalog ``model_name`` for this NTSB string, or None if not handled here."""
    if not make_model:
        return None
    if is_ec130_make_model(make_model):
        return EC130_PAGE
    page = resolve_boeing_737_series_page(make_model)
    if page:
        return page
    return resolve_boeing_787_page(make_model)
