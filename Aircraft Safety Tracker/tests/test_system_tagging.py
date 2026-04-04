from app import db
from app.ingestion.system_tagging import apply_jasc_mapping_to_incident
from app.models import Aircraft, Incident, JASCMapping, SystemTag, UnmappedJASC
from datetime import date


def test_apply_jasc_mapping_creates_system_tag(app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='TEST-1')
        db.session.add(aircraft)
        db.session.commit()

        incident = Incident(aircraft_id=aircraft.id, date=date(2024, 1, 1), incident_type='Incident')
        db.session.add(incident)
        db.session.commit()

        db.session.add(JASCMapping(jasc_code='29-51-00', system_name='Hydraulics', confidence='High'))
        db.session.commit()

        system_name, confidence = apply_jasc_mapping_to_incident(incident.id, '295100', tagged_by='FAA')
        assert system_name == 'Hydraulics'
        assert confidence == 'High'

        tag = SystemTag.query.filter_by(incident_id=incident.id, system_name='Hydraulics', tagged_by='FAA').first()
        assert tag is not None
        assert tag.confidence == 'High'


def test_apply_jasc_mapping_fallback_unknown(app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='TEST-2')
        db.session.add(aircraft)
        db.session.commit()

        incident = Incident(aircraft_id=aircraft.id, date=date(2024, 1, 1), incident_type='Incident')
        db.session.add(incident)
        db.session.commit()

        system_name, confidence = apply_jasc_mapping_to_incident(incident.id, 'XX', tagged_by='FAA')
        assert system_name == 'Unknown System'
        assert confidence == 'Low'

        assert UnmappedJASC.query.count() == 0


def test_apply_jasc_mapping_records_unmapped_when_valid_format_but_missing(app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='TEST-3')
        db.session.add(aircraft)
        db.session.commit()

        incident = Incident(aircraft_id=aircraft.id, date=date(2024, 1, 1), incident_type='Incident')
        db.session.add(incident)
        db.session.commit()

        system_name, confidence = apply_jasc_mapping_to_incident(incident.id, '29-51-00', tagged_by='FAA')
        assert system_name == 'Unknown System'
        assert confidence == 'Low'

        unmapped = UnmappedJASC.query.filter_by(source_name='FAA', jasc_code='29-51-00').first()
        assert unmapped is not None
        assert unmapped.occurrences == 1
