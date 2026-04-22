from datetime import date

from app import db
from app.ingestion.importers.faa_sdr_importer import FAASDRImporter
from app.models import DedupeDecision, Incident, IncidentSource


class DummyFAASDRImporter(FAASDRImporter):
    def parse(self, raw_record):
        return raw_record

    def upsert(self, parsed_record):
        return None


def test_faa_sdr_importer_filters_target_manufacturers():
    importer = DummyFAASDRImporter(
        records=[
            {"manufacturer": "Boeing", "control_number": "A1"},
            {"make": "Airbus", "control_number": "A2"},
            {"manufacturer": "Cessna", "control_number": "A3"},
        ]
    )
    records = importer.fetch()
    control_numbers = {row["control_number"] for row in records}
    assert control_numbers == {"A1", "A2"}


def test_faa_sdr_importer_deduplicates_records_across_sources(monkeypatch):
    importer = DummyFAASDRImporter(records=[])

    def fake_fetch_remote_records(self, manufacturer):
        if manufacturer == "BOEING":
            return [
                {
                    "control_number": "X1",
                    "event_date": "2024-01-01",
                    "aircraft_model": "737",
                    "manufacturer": "Boeing",
                },
                {
                    "control_number": "X2",
                    "event_date": "2024-01-02",
                    "aircraft_model": "737",
                    "manufacturer": "Boeing",
                },
            ]
        return [
            {
                "control_number": "X1",
                "event_date": "2024-01-01",
                "aircraft_model": "737",
                "manufacturer": "Airbus",
            },
        ]

    monkeypatch.setattr(DummyFAASDRImporter, "_fetch_remote_records", fake_fetch_remote_records)
    rows = importer.fetch()
    assert len(rows) == 2
    ids = {row["control_number"] for row in rows}
    assert ids == {"X1", "X2"}


def test_faa_sdr_importer_rejects_html_payload():
    importer = DummyFAASDRImporter(records=[])
    assert importer._looks_like_csv("<html><body>not csv</body></html>") is False
    assert importer._looks_like_csv("a,b\n1,2") is True


def test_faa_sdr_importer_fetch_uses_mocked_api_payload(monkeypatch):
    importer = FAASDRImporter(records=[])

    def fake_request_csv_payload(self, client, url, manufacturer):
        return (
            "control_number,event_date,aircraft_model,manufacturer\n"
            "SDR-1,2024-01-01,B737,BOEING\n"
            "SDR-2,2024-01-01,172,CESSNA\n"
        )

    monkeypatch.setattr(FAASDRImporter, "_request_csv_payload", fake_request_csv_payload)
    rows = importer._fetch_remote_records("BOEING")
    assert len(rows) == 1
    assert rows[0]["control_number"] == "SDR-1"


def test_faa_sdr_importer_parse_maps_expected_fields():
    importer = FAASDRImporter(records=[])
    parsed = importer.parse(
        {
            "control no": "SDR-9",
            "occurrence_date": "2024-03-15",
            "operator_nm": " Demo Air ",
            "acft_model": "B737",
            "remarks": "  Hydraulic leak observed  ",
        }
    )
    assert parsed is not None
    assert parsed["source_record_id"] == "SDR-9"
    assert parsed["date"] == date(2024, 3, 15)
    assert parsed["operator"] == "Demo Air"
    assert parsed["make_model"] == "Boeing 737"
    assert parsed["description"] == "Hydraulic leak observed"


def test_faa_sdr_importer_creates_standalone_incident_when_no_match(app):
    with app.app_context():
        importer = FAASDRImporter(
            records=[
                {
                    "control_number": "SDR-NEW-1",
                    "date": "2024-05-02",
                    "manufacturer": "Boeing",
                    "aircraft_model": "B737",
                    "operator": "Standalone Air",
                    "description": "Hydraulic issue",
                }
            ]
        )
        importer.run()

        incident = Incident.query.first()
        assert incident is not None
        assert incident.date == date(2024, 5, 2)
        assert incident.operator == "Standalone Air"
        assert incident.description == "Hydraulic issue"

        source = IncidentSource.query.filter_by(
            source_name="FAA_SDR",
            source_record_id="SDR-NEW-1",
        ).first()
        assert source is not None
        assert source.incident_id == incident.id

        decision = DedupeDecision.query.filter_by(
            source_name="FAA_SDR",
            source_record_id="SDR-NEW-1",
        ).first()
        assert decision is not None
        assert decision.decision == "created_new"


def test_faa_sdr_importer_upsert_links_existing_incident(app):
    with app.app_context():
        existing = Incident(
            date=date(2024, 7, 1),
            registration="N777AA",
            operator="Link Air",
            location="Austin, TX",
            incident_type="Incident",
            description="Existing record",
            fatalities=0,
        )
        db.session.add(existing)
        db.session.commit()

        importer = FAASDRImporter(records=[])
        importer.upsert(
            {
                "source_record_id": "SDR-LINK-1",
                "date": date(2024, 7, 1),
                "registration": "N777AA",
                "operator": "Link Air",
                "location": "Austin, TX",
                "description": "FAA SDR narrative",
                "source_data": {"control_number": "SDR-LINK-1"},
            }
        )
        db.session.commit()

        assert Incident.query.count() == 1
        source = IncidentSource.query.filter_by(
            source_name="FAA_SDR",
            source_record_id="SDR-LINK-1",
        ).first()
        assert source is not None
        assert source.incident_id == existing.id

        decision = DedupeDecision.query.filter_by(
            source_name="FAA_SDR",
            source_record_id="SDR-LINK-1",
        ).first()
        assert decision is not None
        assert decision.decision == "linked_existing"


def test_faa_sdr_importer_processes_synthetic_boeing_with_aircraft_link(app):
    with app.app_context():
        # Synthetic/fake FAA SDR payload for linkage-path verification.
        importer = FAASDRImporter(
            records=[
                {
                    "control_number": "SDR-SYNTH-BOEING-1",
                    "date": "2024-08-01",
                    "manufacturer": "Boeing",
                    "aircraft_model": "B737",
                    "operator": "Synthetic Air",
                    "description": "Synthetic FAA SDR record for test coverage",
                }
            ]
        )

        import_log, stats = importer.run()

        assert import_log.records_processed > 0
        assert stats.records_processed > 0

        incident = Incident.query.filter_by(operator="Synthetic Air").first()
        assert incident is not None
        assert incident.aircraft_id is not None
