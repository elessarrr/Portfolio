from types import SimpleNamespace

import app.services.deepseek as deepseek_module
from app.services.deepseek import DeepSeekService


def test_deepseek_disabled_without_api_key(monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    service = DeepSeekService()
    assert service.enabled is False
    assert service.generate_aircraft_summary({
        'manufacturer': 'Boeing',
        'model_name': '737',
        'years_in_service': 50,
        'total_incidents': 10,
        'fatal_incidents': 2,
        'total_fatalities': 100,
    }) == "AI summary unavailable (API key missing)."


def test_deepseek_generate_summary_success(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='  Safe summary text  '))]
            )

    class FakeOpenAI:
        def __init__(self, api_key, base_url):
            self.api_key = api_key
            self.base_url = base_url
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(deepseek_module, 'OpenAI', FakeOpenAI)
    service = DeepSeekService()
    result = service.generate_aircraft_summary({
        'manufacturer': 'Airbus',
        'model_name': 'A320',
        'years_in_service': 35,
        'total_incidents': 8,
        'fatal_incidents': 1,
        'total_fatalities': 80,
    })
    assert result == 'Safe summary text'


def test_deepseek_generate_summary_handles_exception(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')

    class FailingCompletions:
        @staticmethod
        def create(**kwargs):
            raise RuntimeError('network timeout')

    class FakeOpenAI:
        def __init__(self, api_key, base_url):
            self.chat = SimpleNamespace(completions=FailingCompletions())

    monkeypatch.setattr(deepseek_module, 'OpenAI', FakeOpenAI)
    service = DeepSeekService()
    result = service.generate_aircraft_summary({
        'manufacturer': 'Boeing',
        'model_name': '777',
        'years_in_service': 30,
        'total_incidents': 5,
        'fatal_incidents': 0,
        'total_fatalities': 0,
    })
    assert result.startswith('Error generating summary:')
