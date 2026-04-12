from app.ingestion.importers.faa_sdr_importer import FAASDRImporter


class DummyFAASDRImporter(FAASDRImporter):
    def parse(self, raw_record):
        return raw_record

    def upsert(self, parsed_record):
        return None


def test_faa_sdr_importer_filters_target_manufacturers():
    importer = DummyFAASDRImporter(records=[
        {'manufacturer': 'Boeing', 'control_number': 'A1'},
        {'make': 'Airbus', 'control_number': 'A2'},
        {'manufacturer': 'Cessna', 'control_number': 'A3'},
    ])
    records = importer.fetch()
    control_numbers = {row['control_number'] for row in records}
    assert control_numbers == {'A1', 'A2'}


def test_faa_sdr_importer_deduplicates_records_across_sources(monkeypatch):
    importer = DummyFAASDRImporter(records=[])

    def fake_fetch_remote_records(self, manufacturer):
        if manufacturer == 'BOEING':
            return [
                {'control_number': 'X1', 'event_date': '2024-01-01', 'aircraft_model': '737', 'manufacturer': 'Boeing'},
                {'control_number': 'X2', 'event_date': '2024-01-02', 'aircraft_model': '737', 'manufacturer': 'Boeing'},
            ]
        return [
            {'control_number': 'X1', 'event_date': '2024-01-01', 'aircraft_model': '737', 'manufacturer': 'Airbus'},
        ]

    monkeypatch.setattr(DummyFAASDRImporter, '_fetch_remote_records', fake_fetch_remote_records)
    rows = importer.fetch()
    assert len(rows) == 2
    ids = {row['control_number'] for row in rows}
    assert ids == {'X1', 'X2'}


def test_faa_sdr_importer_rejects_html_payload():
    importer = DummyFAASDRImporter(records=[])
    assert importer._looks_like_csv('<html><body>not csv</body></html>') is False
    assert importer._looks_like_csv('a,b\n1,2') is True
