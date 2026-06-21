from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta

from openai import APIConnectionError, AuthenticationError, OpenAI

logger = logging.getLogger(__name__)

DEFAULT_SUMMARY_TTL_DAYS = 7

# User-visible copy when the API is unavailable (never expose exception text or key fragments).
SUMMARY_UNAVAILABLE_USER_MESSAGE = (
    "Summary temporarily unavailable. Please try again later."
)

# In-progress marker persisted while a background regeneration runs. The HTMX
# polling partial keys off the "Generating AI summary" substring (see routes).
GENERATING_MARKER = "Generating AI summary... Please wait."

# Sentinel for "not provided" so tests can force-disable.
_UNSET = object()

# Stored summaries from before Bug 4.1 fix (must not render or block auto-regenerate).
_LEGACY_ERROR_MARKERS = (
    "failed to generate summary:",
    "error generating summary:",
    "authentication fails",
    "authentication_error",
    "error code: 401",
    "error code: 403",
)


def is_legacy_error_summary(stored: str | None) -> bool:
    if not stored:
        return False
    lower = stored.lower()
    return any(marker in lower for marker in _LEGACY_ERROR_MARKERS)


def display_ai_summary(stored: str | None) -> str | None:
    """Safe text for templates; legacy API errors are treated as missing."""
    if not stored or is_legacy_error_summary(stored):
        return None
    return stored


class DeepSeekService:
    def __init__(self, api_key=_UNSET):
        # If api_key is explicitly provided (even None), respect it.
        # If not provided, fall back to env var.
        if api_key is _UNSET:
            self.api_key = os.environ.get("DEEPSEEK_API_KEY") or None
        else:
            self.api_key = api_key or None
        self.base_url = "https://api.deepseek.com"
        
        if self.api_key:
            logger.info("DeepSeekService initialized with API key present.")
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self.enabled = True
        else:
            logger.warning("DEEPSEEK_API_KEY not set. AI features disabled.")
            self.client = None
            self.enabled = False

    def generate_aircraft_summary(self, aircraft_data):
        """
        Generates a summary for an aircraft model using DeepSeek.
        """
        if not self.enabled:
            return SUMMARY_UNAVAILABLE_USER_MESSAGE

        prompt = f"""
        Provide a concise, factual summary of the safety record of the {aircraft_data['manufacturer']} {aircraft_data['model_name']}, based STRICTLY on the Key Data provided below.
        
        Key Data:
        - Years in service: {aircraft_data['years_in_service']}
        - Total incidents: {aircraft_data['total_incidents']}
        - Fatal incidents: {aircraft_data['fatal_incidents']}
        - Total fatalities: {aircraft_data['total_fatalities']}
        
        Instructions:
        1. Base your safety assessment PRIMARILY on the provided Key Data.
        2. Do NOT cite external accident statistics, specific crash events, or data not reflected in these numbers.
        3. Do NOT hallucinate or invent safety issues.
        4. Use general knowledge ONLY for basic context (e.g., aircraft size, role, introduction era) to interpret the numbers.
        
        Keep it under 200 words. Do not include markdown formatting like **bold** or headers. Just plain text.
        """
        
        try:
            logger.info(f"Sending request to DeepSeek API for {aircraft_data['model_name']}...")
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a professional aviation safety expert. Provide objective, factual summaries based strictly on provided data. Do not use conversational fillers. Output plain text only."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.7,
                stream=False
            )
            content = response.choices[0].message.content.strip()
            logger.info(f"DeepSeek response received. Length: {len(content)}")
            return content
        except AuthenticationError:
            logger.warning("DeepSeek authentication failed (invalid or missing API key).")
            return SUMMARY_UNAVAILABLE_USER_MESSAGE
        except APIConnectionError as e:
            logger.warning("DeepSeek connection error: %s", e)
            return SUMMARY_UNAVAILABLE_USER_MESSAGE
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}", exc_info=True)
            return SUMMARY_UNAVAILABLE_USER_MESSAGE


def _summary_ttl_days() -> int:
    try:
        return int(os.environ.get("AI_SUMMARY_TTL_DAYS", str(DEFAULT_SUMMARY_TTL_DAYS)))
    except (TypeError, ValueError):
        return DEFAULT_SUMMARY_TTL_DAYS


def _usable_cached_summary(aircraft) -> str | None:
    """Return a displayable cached summary, excluding the in-progress marker."""
    stored = aircraft.ai_summary
    if stored == GENERATING_MARKER:
        return None
    return display_ai_summary(stored)


def is_summary_fresh(aircraft, *, now: datetime | None = None, ttl_days: int | None = None) -> bool:
    """True when a usable (non-legacy) summary exists and is within the TTL window."""
    if not _usable_cached_summary(aircraft):
        return False
    if aircraft.summary_generated_at is None:
        return False
    now = now or datetime.utcnow()
    ttl_days = ttl_days if ttl_days is not None else _summary_ttl_days()
    return (now - aircraft.summary_generated_at) < timedelta(days=ttl_days)


def get_or_generate_summary(aircraft, *, force: bool = False, ai_service=None, commit: bool = True):
    """Cache-aware AI summary gate (PRD 0012 FR-2).

    Returns the summary text to display. Only calls the AI API when forced or
    when the cached summary is missing/stale. On API failure, preserves any
    existing cached summary (and leaves `summary_generated_at` untouched).
    """
    from app import db

    if not force and is_summary_fresh(aircraft):
        return aircraft.ai_summary

    service = ai_service if ai_service is not None else DeepSeekService()
    aircraft_data = {
        "manufacturer": aircraft.manufacturer,
        "model_name": aircraft.model_name,
        "years_in_service": aircraft.years_in_service,
        "total_incidents": aircraft.total_incidents,
        "fatal_incidents": aircraft.fatal_incidents,
        "total_fatalities": aircraft.total_fatalities,
    }

    try:
        summary = service.generate_aircraft_summary(aircraft_data)
    except Exception:
        logger.exception("AI summary generation raised for %s; serving cached value.", aircraft.model_name)
        return aircraft.ai_summary

    if summary == SUMMARY_UNAVAILABLE_USER_MESSAGE:
        # API unavailable: keep a good cached summary if we have one.
        cached = _usable_cached_summary(aircraft)
        if cached:
            return cached
        aircraft.ai_summary = SUMMARY_UNAVAILABLE_USER_MESSAGE
        if commit:
            db.session.commit()
        return aircraft.ai_summary

    aircraft.ai_summary = summary
    aircraft.summary_generated_at = datetime.utcnow()
    if commit:
        db.session.commit()
    return summary
