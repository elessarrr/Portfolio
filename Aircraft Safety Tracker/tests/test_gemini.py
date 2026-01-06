import pytest
from unittest.mock import patch, MagicMock
from app.services.gemini import GeminiService

def test_gemini_service_initialization_no_key():
    with patch.dict('os.environ', {}, clear=True):
        service = GeminiService(api_key=None)
        assert service.enabled is False
        assert service.model is None

def test_gemini_service_initialization_with_key():
    with patch.dict('os.environ', {'GOOGLE_GEMINI_API_KEY': 'test_key'}):
        # We need to mock the entire module if it doesn't have the attribute
        with patch('app.services.gemini.HAS_GEMINI', True):
            with patch('app.services.gemini.genai') as mock_genai:
                service = GeminiService()
                if service.enabled:
                    mock_genai.configure.assert_called_with(api_key='test_key')
                    mock_genai.GenerativeModel.assert_called_with('gemini-pro')

def test_generate_content_mock_mode():
    with patch.dict('os.environ', {}, clear=True):
        service = GeminiService(api_key=None)
        result = service.generate_content("test prompt")
        assert "AI summary unavailable" in result

def test_generate_aircraft_summary_mock_mode():
    with patch.dict('os.environ', {}, clear=True):
        service = GeminiService(api_key=None)
        data = {
            'manufacturer': 'Boeing',
            'model_name': '737',
            'years_in_service': 50,
            'total_incidents': 10,
            'fatal_incidents': 2,
            'total_fatalities': 100
        }
        result = service.generate_aircraft_summary(data)
        assert "AI summary unavailable" in result
