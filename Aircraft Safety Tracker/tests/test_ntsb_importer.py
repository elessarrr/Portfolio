from datetime import date
from unittest.mock import patch

import pytest

from app import db
from app.ingestion.importers.ntsb_importer import NTSBImporter
from app.models import Incident, IncidentSource


def test_ntsb_importer_creates_incident_and_source(app):
    with app.app_context():
        with patch('app.ingestion.importers.ntsb_importer.validate_source_url') as mock_source, \
             patch('app.ingestion.importers.ntsb_importer.validate_pdf_url') as mock_pdf:
            mock_source.return_value = (True, 200, None)
            mock_pdf.return_value = (True, 200, None)
            importer = NTSBImporter(records=[
                {
                    'ntsb_id': 'ABC12FA000',
                    'event_date': '2020-01-02',
                    'location': 'Austin, TX',
                    'operator': 'Test Operator',
                    'fatalities': '2',
                    'probable_cause': 'Loss of control',
                    'url': 'https://example.com/case',
                    'pdf_report_url': 'https://example.com/report.pdf',
                }
            ])
            importer.run()

        incident = Incident.query.first()
        assert incident is not None
        assert incident.date == date(2020, 1, 2)
        assert incident.location == 'Austin, TX'
        assert incident.fatalities == 2
        assert incident.description == 'Loss of control'

        source = IncidentSource.query.filter_by(source_name='NTSB', source_record_id='ABC12FA000').first()
        assert source is not None
        assert source.incident_id == incident.id
        assert source.confidence_level == 'High'
        assert source.report_url == 'https://example.com/report.pdf'


def test_ntsb_importer_upserts_by_source_record_id(app):
    with app.app_context():
        importer = NTSBImporter(records=[
            {
                'ntsb_id': 'ABC12FA000',
                'event_date': '2020-01-02',
                'location': 'Austin, TX',
                'operator': 'Op',
                'fatalities': '0',
                'probable_cause': 'Initial',
            }
        ])
        importer.run()

        importer = NTSBImporter(records=[
            {
                'ntsb_id': 'ABC12FA000',
                'event_date': '2020-01-02',
                'location': 'Austin, Texas',
                'fatalities': '1',
                'probable_cause': 'Updated',
            }
        ])
        importer.run()

        assert Incident.query.count() == 1
        incident = Incident.query.first()
        assert incident.location == 'Austin, Texas'
        assert incident.fatalities == 1
        assert incident.description == 'Updated'


def test_ntsb_importer_rejects_out_of_range_dates(app):
    with app.app_context():
        importer = NTSBImporter(records=[
            {
                'ntsb_id': 'ABC12FA000',
                'event_date': '1984-12-31',
                'location': 'X',
                'probable_cause': 'Old',
            },
            {
                'ntsb_id': 'ABC12FA001',
                'event_date': '2026-01-01',
                'location': 'Y',
                'probable_cause': 'Future',
            },
        ])
        importer.run()
        assert Incident.query.count() == 0


# ---------------------------------------------------------------------------
# PRD-0014 task 5.1 — NTSB link URL tests
# ---------------------------------------------------------------------------

def test_ntsb_source_url_is_canonical_docket_url_when_cm_ntsbNum_present(app):
    """
    When a payload contains cm_ntsbNum (NTSB number), source_url must be the
    canonical non-PDF docket URL, not the legacy CAROL detail URL.
    """
    with app.app_context():
        with patch('app.ingestion.importers.ntsb_importer.validate_source_url') as mock_source, \
             patch('app.ingestion.importers.ntsb_importer.validate_pdf_url') as mock_pdf:
            mock_source.return_value = (True, 200, None)
            mock_pdf.return_value = (True, 200, None)
            importer = NTSBImporter(records=[{
                'ntsb_id': 'WPR19LA999',
                'cm_ntsbNum': 'WPR19LA999',
                'cm_mkey': '99999',
                'event_date': '2019-06-15',
                'location': 'Phoenix, AZ',
                'probable_cause': 'Test',
                'pdf_report_url': 'https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/WPR19LA999/pdf',
            }])
            importer.run()

        source = IncidentSource.query.filter_by(source_record_id='WPR19LA999').first()
        assert source is not None
        assert source.source_name == 'NTSB'
        # Canonical docket URL is the expected source_url (non-PDF Details).
        assert source.source_url == 'https://data.ntsb.gov/Docket/?NTSBNumber=WPR19LA999'
        # report_url remains the secondary docs link (PDF or other).
        assert 'WPR19LA999' in (source.report_url or '')


def test_ntsb_source_url_falls_back_to_carol_detail_when_no_ntsb_number_identifiers(app):
    """
    When neither cm_ntsbNum nor ntsb_id is in the raw payload (both would map to
    source_record_id), source_url falls back to the legacy CAROL investigation detail
    URL via cm_mkey. This covers older records that lack NTSB number identifiers.
    """
    with app.app_context():
        # Omit ntsb_id so ntsb_num is None in parse_record → CAROL fallback activates.
        importer = NTSBImporter(records=[{
            # no ntsb_id (source_record_id would be absent)
            # no cm_ntsbNum
            'cm_mkey': '88888',
            'event_date': '2008-03-20',
            'location': 'Los Angeles, CA',
            'probable_cause': 'Test legacy',
        }])
        importer.run()

        # No source_record_id means we match on cm_mkey in source_data.
        sources = IncidentSource.query.all()
        assert len(sources) == 1
        source = sources[0]
        # Falls back to CAROL detail via cm_mkey.
        assert source.source_url == 'https://carol.ntsb.gov/investigations/detail/88888'


def test_ntsb_source_url_does_not_fallback_to_carol_for_pre_2008_mkey_only_records(app):
    """
    Pre-cutover records should not default to CAROL when we only have cm_mkey.
    This avoids routing old investigations to the wrong system by assumption.
    """
    with app.app_context():
        importer = NTSBImporter(records=[{
            'cm_mkey': '77777',
            'event_date': '2007-03-20',
            'location': 'Los Angeles, CA',
            'probable_cause': 'Legacy test',
        }])
        importer.run()

        # Record is intentionally skipped because it has neither source_record_id
        # nor a trustworthy source_url candidate under the new routing rule.
        assert IncidentSource.query.count() == 0


def test_ntsb_source_url_uses_legacy_brief_when_ev_id_present(app):
    """
    If a raw record includes a numeric ev_id, source_url should route directly
    to the legacy brief page rather than CAROL.
    """
    with app.app_context():
        with patch('app.ingestion.importers.ntsb_importer.validate_source_url') as mock_source:
            mock_source.return_value = (True, 200, None)
            importer = NTSBImporter(records=[{
                'cm_ntsbNum': 'NYC02LA081',
                'ntsb_id': 'NYC02LA081',
                'ev_id': '12345',
                'event_date': '2002-03-20',
                'location': 'Queens, NY',
                'probable_cause': 'Legacy mapping present',
            }])
            importer.run()

        source = IncidentSource.query.filter_by(source_record_id='NYC02LA081').first()
        assert source is not None
        assert source.source_url == 'https://www.ntsb.gov/Pages/brief.aspx?ev_id=12345&key=0'


def test_ntsb_source_url_and_report_url_are_distinct_and_both_populated(app):
    """
    source_url (canonical non-PDF Details) and report_url (secondary docs) must
    be stored as separate, non-identical fields when both are available.
    """
    with app.app_context():
        with patch('app.ingestion.importers.ntsb_importer.validate_source_url') as mock_source, \
             patch('app.ingestion.importers.ntsb_importer.validate_pdf_url') as mock_pdf:
            mock_source.return_value = (True, 200, None)
            mock_pdf.return_value = (True, 200, None)
            importer = NTSBImporter(records=[{
                'ntsb_id': 'NYC23FA001',
                'cm_ntsbNum': 'NYC23FA001',
                'event_date': '2023-08-01',
                'location': 'New York, NY',
                'probable_cause': 'Test dual-link',
                'pdf_report_url': 'https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/NYC23FA001/pdf',
            }])
            importer.run()

        source = IncidentSource.query.filter_by(source_record_id='NYC23FA001').first()
        assert source is not None
        # Details link — must be a non-PDF docket URL.
        assert 'data.ntsb.gov/Docket' in source.source_url
        assert '.pdf' not in source.source_url
        # Docs link — must contain the PDF report URL.
        assert 'NYC23FA001' in (source.report_url or '')
        # They must not be the same value.
        assert source.source_url != source.report_url
