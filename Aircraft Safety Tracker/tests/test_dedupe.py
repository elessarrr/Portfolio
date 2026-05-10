from datetime import date

from app import db
from app.ingestion.dedupe import find_best_incident_match, record_dedupe_decision
from app.models import Aircraft, DedupeDecision, Incident


def test_find_best_incident_match_exact_date_and_registration(app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='DED-1')
        db.session.add(aircraft)
        db.session.commit()

        incident = Incident(
            aircraft_id=aircraft.id,
            date=date(2024, 1, 2),
            registration='N12345',
            location='Austin, TX',
            operator='Test',
            incident_type='Accident',
        )
        db.session.add(incident)
        db.session.commit()

        matched, rule, score, details = find_best_incident_match(
            date=date(2024, 1, 2),
            registration='N12345',
            location='Austin, Texas',
            operator='Test',
        )
        assert matched is not None
        assert matched.id == incident.id
        assert rule == 'exact_date_registration'
        assert score == 1.0


def test_find_best_incident_match_fuzzy_location(app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='DED-2')
        db.session.add(aircraft)
        db.session.commit()

        incident = Incident(
            aircraft_id=aircraft.id,
            date=date(2024, 1, 2),
            registration=None,
            location='Los Angeles, CA',
            operator='Carrier',
            incident_type='Accident',
        )
        db.session.add(incident)
        db.session.commit()

        matched, rule, score, details = find_best_incident_match(
            date=date(2024, 1, 2),
            registration=None,
            location='Los Angeles California',
            operator='Carrier',
            min_score=0.4,
        )
        assert matched is not None
        assert matched.id == incident.id
        assert rule == 'fuzzy_date_registration_location'
        assert score >= 0.4


def test_record_dedupe_decision_persists(app):
    with app.app_context():
        row = record_dedupe_decision(
            source_name='FAA_AIDS',
            source_record_id='AIDS-1',
            incoming_incident_id=None,
            matched_incident_id=123,
            decision='linked_existing',
            rule='exact_date_registration',
            score=1.0,
            details={'foo': 'bar'},
        )
        assert row.id is not None
        persisted = DedupeDecision.query.filter_by(id=row.id).first()
        assert persisted is not None
        assert persisted.decision == 'linked_existing'


def test_find_best_incident_match_flags_fatality_discrepancy(app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='DED-3')
        db.session.add(aircraft)
        db.session.commit()

        # Existing incident has 5 fatalities
        incident = Incident(
            aircraft_id=aircraft.id,
            date=date(2024, 1, 2),
            registration='N12345',
            location='Austin, TX',
            operator='Test',
            incident_type='Accident',
            fatalities=5
        )
        db.session.add(incident)
        db.session.commit()

        # Incoming incident has 0 fatalities, but matches perfectly otherwise
        matched, rule, score, details = find_best_incident_match(
            date=date(2024, 1, 2),
            registration='N12345',
            location='Austin, Texas',
            operator='Test',
            fatalities=0
        )
        
        assert matched is not None
        assert matched.id == incident.id
        assert 'discrepancy' in details
        assert details['discrepancy']['field'] == 'fatalities'
        assert details['discrepancy']['incoming'] == 0
        assert details['discrepancy']['existing'] == 5


def test_find_best_incident_match_no_discrepancy(app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='DED-4')
        db.session.add(aircraft)
        db.session.commit()

        # Existing incident has 2 fatalities
        incident = Incident(
            aircraft_id=aircraft.id,
            date=date(2024, 1, 2),
            registration='N12345',
            location='Austin, TX',
            operator='Test',
            incident_type='Accident',
            fatalities=2
        )
        db.session.add(incident)
        db.session.commit()

        # Incoming incident matches the fatality count exactly
        matched, rule, score, details = find_best_incident_match(
            date=date(2024, 1, 2),
            registration='N12345',
            location='Austin, Texas',
            operator='Test',
            fatalities=2
        )
        
        assert matched is not None
        assert matched.id == incident.id
        assert 'discrepancy' not in details

