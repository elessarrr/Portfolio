"""Dedupe helpers: decide if an NTSB record is already covered by ASN.

This module is used for NTSB enrichment where we only INSERT incidents that
are not already present in the ASN baseline.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Optional

from thefuzz import fuzz


def _norm_text(value: Optional[str]) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[\s\-]+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _ratio(a: Optional[str], b: Optional[str]) -> int:
    aa = _norm_text(a)
    bb = _norm_text(b)
    if not aa or not bb:
        return 0
    return int(fuzz.token_set_ratio(aa, bb))


def _days_apart(a: datetime.date, b: datetime.date) -> int:
    return abs((a - b).days)


def fatalities_like_import(value: Optional[int]) -> int:
    """Match NTSBImporter insert: null/unknown → 0 in DB (see LEARNINGS §38)."""
    if value is None:
        return 0
    return int(value)


@dataclass(frozen=True)
class DedupeSignals:
    date_close: bool
    operator_close: bool
    location_close: bool
    fatalities_close: bool

    def strong_count(self) -> int:
        return int(self.date_close) + int(self.operator_close) + int(self.location_close) + int(
            self.fatalities_close
        )


@dataclass(frozen=True)
class DedupeDecision:
    asn_covered: bool
    signals: DedupeSignals
    operator_ratio: int
    location_ratio: int
    days_apart: int


def score_ntsb_vs_asn(
    *,
    ntsb_date: datetime.date,
    asn_date: datetime.date,
    ntsb_operator: Optional[str],
    asn_operator: Optional[str],
    ntsb_location: Optional[str],
    asn_location: Optional[str],
    ntsb_fatalities: Optional[int],
    asn_fatalities: Optional[int],
    date_window_days: int = 1,
    operator_ratio_threshold: int = 90,
    location_ratio_threshold: int = 85,
    fatalities_delta_threshold: int = 1,
) -> DedupeDecision:
    days = _days_apart(ntsb_date, asn_date)
    op_ratio = _ratio(ntsb_operator, asn_operator)
    loc_ratio = _ratio(ntsb_location, asn_location)

    date_close = days <= date_window_days
    operator_close = op_ratio >= operator_ratio_threshold
    location_close = loc_ratio >= location_ratio_threshold

    fatalities_close = False
    if ntsb_fatalities is not None and asn_fatalities is not None:
        fatalities_close = abs(int(ntsb_fatalities) - int(asn_fatalities)) <= fatalities_delta_threshold

    signals = DedupeSignals(
        date_close=date_close,
        operator_close=operator_close,
        location_close=location_close,
        fatalities_close=fatalities_close,
    )

    # Balanced policy: treat as ASN-covered if 2+ strong signals match.
    asn_covered = signals.strong_count() >= 2

    return DedupeDecision(
        asn_covered=asn_covered,
        signals=signals,
        operator_ratio=op_ratio,
        location_ratio=loc_ratio,
        days_apart=days,
    )

