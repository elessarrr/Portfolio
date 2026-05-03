"""
Integration tests for the `flask import-data enrich-wa-incidents` CLI command.

Covers:
  1.3  – Target incident identification logic
  1.4  – Full pipeline: identify → search → validate → store MEDIA source
  1.7  – Idempotency (skip if MEDIA source already exists)
  1.8  – Logging output

Uses the real SQLite in-memory DB (via app fixture) with mocked WebSearchService.
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock
import hashlib

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import db
from app.models import Incident, IncidentSource
from app.services.web_search import SearchResult


# ---------------------------------------------------------------------------
# Fixture – creates test data with various source configurations
# ---------------------------------------------------------------------------

@pytest.fixture
def wa_incident_dataset(app):
    """
    Create a minimal dataset matching the enrichment targeting criteria:

      - inc_active       : has active NTSB source       → NOT targeted
      - inc_inactive     : inactive NTSB source only    → TARGETED
      - inc_inactive_w_media : inactive NTSB + MEDIA     → NOT targeted (already enriched)
      - inc_no_ntsb      : no NTSB source at all        → NOT targeted
    """
    with app.app_context():
        from app.models import Aircraft
        ac = Aircraft(manufacturer="Boeing", model_name="Boeing 737", years_in_service=50)
        db.session.add(ac)
        db.session.commit()

        inc_active = Incident(
            aircraft_id=ac.id, date=date(2024, 1, 1),
            operator="Active Airlines", location="Seattle, WA",
            registration="N7711A", incident_type="Accident",
        )
        inc_inactive = Incident(
            aircraft_id=ac.id, date=date(2024, 2, 1),
            operator="West Air", location="Tokyo, Japan",
            registration="N222XZ", incident_type="Accident",
        )
        inc_inactive_w_media = Incident(
            aircraft_id=ac.id, date=date(2024, 3, 1),
            operator="Pacific West", location="Osaka, Japan",
            registration="N333YZ", incident_type="Accident",
        )
        inc_no_ntsb = Incident(
            aircraft_id=ac.id, date=date(2024, 4, 1),
            operator="No Source Airline", location="Seoul, Korea",
            registration="N444ZZ", incident_type="Incident",
        )
        db.session.add_all([inc_active, inc_inactive, inc_inactive_w_media, inc_no_ntsb])
        db.session.commit()

        # inc_active: active NTSB source
        db.session.add(IncidentSource(
            incident_id=inc_active.id, source_name="NTSB",
            source_record_id="WPR24LA001", source_url="https://data.ntsb.gov/Docket/001",
            is_active=True, confidence_level="High",
        ))
        # inc_inactive: inactive NTSB source only
        db.session.add(IncidentSource(
            incident_id=inc_inactive.id, source_name="NTSB",
            source_record_id="WPR24LA999", source_url="https://data.ntsb.gov/Docket/999",
            is_active=False, confidence_level="High",
        ))
        # inc_inactive_w_media: inactive NTSB + existing MEDIA
        db.session.add(IncidentSource(
            incident_id=inc_inactive_w_media.id, source_name="NTSB",
            source_record_id="WPR24LA888", source_url="https://data.ntsb.gov/Docket/888",
            is_active=False, confidence_level="High",
        ))
        db.session.add(IncidentSource(
            incident_id=inc_inactive_w_media.id, source_name="MEDIA",
            source_record_id="reuters.com",
            source_url="https://reuters.com/article/888",
            is_active=True, confidence_level="Low",
        ))
        db.session.commit()

        yield {
            "inc_active": inc_active.id,
            "inc_inactive": inc_inactive.id,
            "inc_inactive_w_media": inc_inactive_w_media.id,
            "inc_no_ntsb": inc_no_ntsb.id,
        }


# ---------------------------------------------------------------------------
# Tests – CLI help
# ---------------------------------------------------------------------------

def test_enrich_wa_incidents_help(runner):
    result = runner.invoke(args=['import-data', 'enrich-wa-incidents', '--help'])
    assert result.exit_code == 0
    assert 'enrich-wa-incidents' in result.output


# ---------------------------------------------------------------------------
# Tests – Dry run
# ---------------------------------------------------------------------------

def test_enrich_wa_incidents_dry_run(app, runner, wa_incident_dataset):
    """Dry run shows the one targeted incident without writing anything."""
    with patch('app.services.web_search.WebSearchService'):
        result = runner.invoke(args=['import-data', 'enrich-wa-incidents', '--dry-run'])
        assert result.exit_code == 0
        assert '[DRY RUN]' in result.output
        # WPR24LA999 is the only target
        assert 'WPR24LA999' in result.output


# ---------------------------------------------------------------------------
# Tests – Full enrichment pipeline
# ---------------------------------------------------------------------------

def test_enrich_wa_incidents_stores_media_source(app, runner, wa_incident_dataset):
    """Successful search stores a new MEDIA source."""
    mock_svc = MagicMock()
    mock_svc.search_tiered.return_value = [
        SearchResult(
            url="https://aviation-herald.com/press/wpr24la999",
            tier=1,
            domain="aviation-herald.com",
        ),
        SearchResult(
            url="https://reuters.com/article/999",
            tier=2,
            domain="reuters.com",
        ),
    ]

    with patch('app.services.web_search.WebSearchService', return_value=mock_svc):
        result = runner.invoke(args=['import-data', 'enrich-wa-incidents'])
        assert result.exit_code == 0
        assert '[FOUND tier=1]' in result.output

    with app.app_context():
        media = IncidentSource.query.filter_by(
            incident_id=wa_incident_dataset['inc_inactive'],
            source_name='MEDIA',
        ).first()
        assert media is not None
        assert media.source_url == "https://aviation-herald.com/press/wpr24la999"
        assert media.is_active is True
        assert media.confidence_level == 'Low'
        assert media.source_data['enrichment_tier'] == 1
        assert len(media.source_data['articles']) == 2


def test_enrich_wa_incidents_idempotent(app, runner, wa_incident_dataset):
    """
    Idempotency: running the job twice must not create duplicate MEDIA sources.

    The first run creates a MEDIA source for inc_inactive. The second run finds
    0 targetable incidents (because inc_inactive now has a MEDIA source), so
    the summary shows 0 incidents checked — this IS the correct idempotent
    behaviour (no duplicates, no errors).
    """
    mock_svc = MagicMock()
    mock_svc.search_tiered.return_value = [
        SearchResult(url="https://example.com/new", tier=2, domain="example.com"),
    ]

    with patch('app.services.web_search.WebSearchService', return_value=mock_svc):
        # First run – should succeed and find one incident
        result1 = runner.invoke(args=['import-data', 'enrich-wa-incidents'])
        assert result1.exit_code == 0

    with app.app_context():
        # Exactly one MEDIA source created (no duplicates)
        count = IncidentSource.query.filter_by(
            incident_id=wa_incident_dataset['inc_inactive'],
            source_name='MEDIA',
        ).count()
        assert count == 1

    with patch('app.services.web_search.WebSearchService', return_value=mock_svc):
        # Second run – 0 incidents targeted because inc_inactive now has MEDIA
        result2 = runner.invoke(args=['import-data', 'enrich-wa-incidents'])
        assert result2.exit_code == 0
        assert 'Total incidents checked : 0' in result2.output


def test_enrich_wa_incidents_no_result(app, runner, wa_incident_dataset):
    """All tiers return nothing → no MEDIA source created."""
    mock_svc = MagicMock()
    mock_svc.search_tiered.return_value = []

    with patch('app.services.web_search.WebSearchService', return_value=mock_svc):
        result = runner.invoke(args=['import-data', 'enrich-wa-incidents'])
        assert result.exit_code == 0
        assert '[NO RESULT]' in result.output

    with app.app_context():
        media = IncidentSource.query.filter_by(
            incident_id=wa_incident_dataset['inc_inactive'],
            source_name='MEDIA',
        ).first()
        assert media is None


def test_enrich_wa_incidents_error_handling(app, runner, wa_incident_dataset):
    """WebSearchService raises → error is caught, logged, and command exits non-zero."""
    mock_svc = MagicMock()
    mock_svc.search_tiered.side_effect = RuntimeError("search exploded")

    with patch('app.services.web_search.WebSearchService', return_value=mock_svc):
        result = runner.invoke(args=['import-data', 'enrich-wa-incidents'])
        assert result.exit_code != 0
        assert '[ERROR]' in result.output
        assert 'Enrichment completed with 1 error(s).' in result.output


def test_enrich_wa_incidents_skips_duplicate_source_record_id(app, runner, wa_incident_dataset):
    """
    If a computed MEDIA source_record_id already exists on another incident,
    enrichment should skip safely instead of crashing with IntegrityError.
    """
    target_event_id = "WPR24LA999"
    best_url = "https://www.bing.com/"
    expected_record_id = f"{target_event_id}:{hashlib.sha1(best_url.encode('utf-8')).hexdigest()[:16]}"

    with app.app_context():
        from app.models import Aircraft
        ac = Aircraft.query.first()
        blocker_incident = Incident(
            aircraft_id=ac.id, date=date(2024, 5, 1),
            operator="Blocker Air", location="Test City",
            registration="N555AA", incident_type="Incident",
        )
        db.session.add(blocker_incident)
        db.session.flush()
        db.session.add(IncidentSource(
            incident_id=blocker_incident.id,
            source_name='MEDIA',
            source_record_id=expected_record_id,
            source_url=best_url,
            is_active=True,
            confidence_level='Low',
        ))
        db.session.commit()

    mock_svc = MagicMock()
    mock_svc.search_tiered.return_value = [
        SearchResult(url=best_url, tier=1, domain='www.bing.com'),
    ]

    with patch('app.services.web_search.WebSearchService', return_value=mock_svc):
        result = runner.invoke(args=['import-data', 'enrich-wa-incidents'])
        assert result.exit_code == 0
        assert 'duplicate MEDIA record id' in result.output


# ---------------------------------------------------------------------------
# Tests – Summary output
# ---------------------------------------------------------------------------

def test_enrich_wa_incidents_summary(app, runner, wa_incident_dataset):
    mock_svc = MagicMock()
    mock_svc.search_tiered.return_value = [
        SearchResult(url="https://ah.com/a", tier=1, domain="ah.com"),
    ]

    with patch('app.services.web_search.WebSearchService', return_value=mock_svc):
        result = runner.invoke(args=['import-data', 'enrich-wa-incidents'])
        assert result.exit_code == 0
        assert 'Enrichment Summary' in result.output or '---' in result.output


# ---------------------------------------------------------------------------
# Tests – Exclusions (active NTSB, no NTSB source)
# ---------------------------------------------------------------------------

def test_enrich_wa_incidents_excludes_active_ntsb(app, runner, wa_incident_dataset):
    """inc_active has active NTSB source → must not be targeted."""
    with patch('app.services.web_search.WebSearchService') as mock_cls:
        mock_cls.return_value = MagicMock()
        result = runner.invoke(args=['import-data', 'enrich-wa-incidents', '--dry-run'])
        assert result.exit_code == 0
        # WPR24LA001 is the active NTSB event_id — should NOT appear
        assert 'WPR24LA001' not in result.output


def test_enrich_wa_incidents_excludes_no_ntsb(app, runner, wa_incident_dataset):
    """inc_no_ntsb has no NTSB source → must not be targeted."""
    with patch('app.services.web_search.WebSearchService') as mock_cls:
        mock_cls.return_value = MagicMock()
        result = runner.invoke(args=['import-data', 'enrich-wa-incidents', '--dry-run'])
        assert result.exit_code == 0
        # Only one incident should be processed (inc_inactive)
        lines_with_incident = [
            l for l in result.output.splitlines()
            if 'incident_id=' in l and 'DRY RUN' in l
        ]
        assert len(lines_with_incident) == 1


def test_enrich_wa_incidents_respects_max_queries(app, runner, wa_incident_dataset):
    """
    --max-queries caps search_tiered calls in a single invocation.
    """
    mock_svc = MagicMock()
    mock_svc.search_tiered.return_value = []

    with patch('app.services.web_search.WebSearchService', return_value=mock_svc):
        result = runner.invoke(args=['import-data', 'enrich-wa-incidents', '--max-queries', '0'])
        assert result.exit_code == 0
        assert 'Query limit set: 0' in result.output
        assert '[STOP] Reached --max-queries limit.' in result.output
        assert 'Queries used             : 0' in result.output
        assert mock_svc.search_tiered.call_count == 0
