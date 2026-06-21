"""AI summary caching tests (PRD 0012, Task 2.0).

The cache gate `get_or_generate_summary` must avoid burning API credits when a
fresh summary already exists, refresh stale summaries, allow forced bypass, and
never lose a good cached summary on API failure.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app import db
from app.models import Aircraft
from app.services.deepseek import (
    SUMMARY_UNAVAILABLE_USER_MESSAGE,
    get_or_generate_summary,
)

AUTO_TRIGGER = 'hx-trigger="load delay:500ms"'


def _make_aircraft(**kw):
    defaults = dict(
        manufacturer="Boeing",
        model_name="Boeing 737-800",
        total_incidents=10,
        fatal_incidents=1,
        total_fatalities=5,
    )
    defaults.update(kw)
    a = Aircraft(**defaults)
    db.session.add(a)
    db.session.commit()
    return a


def test_cache_hit_skips_api(app):
    with app.app_context():
        a = _make_aircraft(
            ai_summary="cached summary",
            summary_generated_at=datetime.utcnow() - timedelta(days=1),
        )
        svc = MagicMock()
        out = get_or_generate_summary(a, force=False, ai_service=svc)
        svc.generate_aircraft_summary.assert_not_called()
        assert out == "cached summary"


def test_cache_miss_calls_api_and_saves(app):
    with app.app_context():
        a = _make_aircraft()
        svc = MagicMock()
        svc.generate_aircraft_summary.return_value = "fresh summary"
        out = get_or_generate_summary(a, force=False, ai_service=svc)
        svc.generate_aircraft_summary.assert_called_once()
        assert out == "fresh summary"
        refetched = db.session.get(Aircraft, a.id)
        assert refetched.ai_summary == "fresh summary"
        assert refetched.summary_generated_at is not None


def test_stale_cache_refreshes(app):
    with app.app_context():
        old = datetime.utcnow() - timedelta(days=8)
        a = _make_aircraft(ai_summary="old summary", summary_generated_at=old)
        svc = MagicMock()
        svc.generate_aircraft_summary.return_value = "new summary"
        out = get_or_generate_summary(a, force=False, ai_service=svc)
        svc.generate_aircraft_summary.assert_called_once()
        assert out == "new summary"
        assert db.session.get(Aircraft, a.id).summary_generated_at > old


def test_force_bypasses_fresh_cache(app):
    with app.app_context():
        a = _make_aircraft(
            ai_summary="cached", summary_generated_at=datetime.utcnow()
        )
        svc = MagicMock()
        svc.generate_aircraft_summary.return_value = "regenerated"
        out = get_or_generate_summary(a, force=True, ai_service=svc)
        svc.generate_aircraft_summary.assert_called_once()
        assert out == "regenerated"


def test_api_failure_keeps_existing_cache(app):
    with app.app_context():
        ts = datetime.utcnow() - timedelta(days=8)  # stale → would trigger a call
        a = _make_aircraft(ai_summary="good cached", summary_generated_at=ts)
        svc = MagicMock()
        svc.generate_aircraft_summary.side_effect = RuntimeError("boom")
        out = get_or_generate_summary(a, force=True, ai_service=svc)
        assert out == "good cached"
        refetched = db.session.get(Aircraft, a.id)
        assert refetched.ai_summary == "good cached"
        assert refetched.summary_generated_at == ts  # unchanged on failure


# --- Route / template integration (FR-2.2, FR-2.4, FR-2.5) ---


def test_fresh_summary_page_load_skips_autotrigger(client, app):
    with app.app_context():
        a = _make_aircraft(
            model_name="Boeing 777",
            ai_summary="Cached summary text.",
            summary_generated_at=datetime.utcnow(),
        )
        aid = a.id
    html = client.get(f"/aircraft/{aid}").data.decode()
    assert "Cached summary text." in html
    assert AUTO_TRIGGER not in html  # fresh → no API regeneration on load


def test_stale_summary_page_load_has_autotrigger(client, app):
    with app.app_context():
        a = _make_aircraft(
            model_name="Boeing 777",
            ai_summary="Old summary.",
            summary_generated_at=datetime.utcnow() - timedelta(days=10),
        )
        aid = a.id
    html = client.get(f"/aircraft/{aid}").data.decode()
    assert AUTO_TRIGGER in html  # stale → refresh triggered


def test_regenerate_without_force_serves_fresh_cache(client, app):
    with app.app_context():
        a = _make_aircraft(
            model_name="Boeing 777",
            ai_summary="Cached summary text.",
            summary_generated_at=datetime.utcnow(),
        )
        aid = a.id
    resp = client.get(
        f"/aircraft/{aid}/regenerate-summary", headers={"HX-Request": "true"}
    )
    # Fresh + no force → cached card, not the in-progress polling partial.
    assert b"Generating AI summary" not in resp.data
    assert b"Cached summary text." in resp.data


def test_regenerate_force_triggers_generation(client, app):
    with app.app_context():
        a = _make_aircraft(
            model_name="Boeing 777",
            ai_summary="Cached summary text.",
            summary_generated_at=datetime.utcnow(),
        )
        aid = a.id
    with patch("app.routes.threading.Thread"):  # don't run real background work
        resp = client.get(
            f"/aircraft/{aid}/regenerate-summary?force=true",
            headers={"HX-Request": "true"},
        )
    # Forced → in-progress polling partial regardless of cache freshness.
    assert b"Generating AI summary" in resp.data
