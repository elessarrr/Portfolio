import app.services.report_analyzer as report_analyzer_module
from app.services.report_analyzer import ReportAnalyzerService


def test_parse_analysis_extracts_embedded_json(app):
    with app.app_context():
        service = ReportAnalyzerService(model_name='mock')
        raw = 'prefix {"root_cause":"Hydraulic leak","contributing_factors":["Maintenance"],"summary":"Short"} suffix'
        parsed = service._parse_analysis(raw)
        assert parsed['root_cause'] == 'Hydraulic leak'
        assert parsed['contributing_factors'] == ['Maintenance']
        assert parsed['summary'] == 'Short'


def test_analyze_report_uses_cache_and_marks_cached(app, monkeypatch):
    with app.app_context():
        service = ReportAnalyzerService(model_name='mock')

        class FakeCache:
            def __init__(self):
                self.data = {}

            def get(self, key):
                return self.data.get(key)

            def set(self, key, value, timeout=None):
                self.data[key] = value

            def inc(self, key):
                self.data[key] = int(self.data.get(key) or 0) + 1
                return self.data[key]

        fake_cache = FakeCache()
        monkeypatch.setattr(report_analyzer_module, 'cache', fake_cache)

        payload = 'Synthetic incident report body'
        first, status_first = service.analyze_report(client_id='c1', report_text=payload)
        first_cached_state = first['cached']
        second, status_second = service.analyze_report(client_id='c1', report_text=payload)

        assert status_first == 200
        assert status_second == 200
        assert first_cached_state is False
        assert second['cached'] is True
        assert second['root_cause'] == first['root_cause']
