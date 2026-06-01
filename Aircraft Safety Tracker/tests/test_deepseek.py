"""DeepSeek summary service — user-safe error handling (Bug 4.1)."""

from unittest.mock import MagicMock, patch

import pytest
from openai import APIConnectionError, AuthenticationError

from app.services.deepseek import (
    SUMMARY_UNAVAILABLE_USER_MESSAGE,
    DeepSeekService,
    display_ai_summary,
    is_legacy_error_summary,
)


def test_legacy_error_summary_not_displayed():
    legacy = (
        "Failed to generate summary: Error generating summary: "
        "Error code: 401 - {'error': {'message': 'Authentication Fails'}}"
    )
    assert is_legacy_error_summary(legacy)
    assert display_ai_summary(legacy) is None


def test_missing_api_key_returns_unavailable_message():
    service = DeepSeekService(api_key=None)
    result = service.generate_aircraft_summary(
        {
            "manufacturer": "Boeing",
            "model_name": "Boeing 737",
            "years_in_service": 40,
            "total_incidents": 10,
            "fatal_incidents": 1,
            "total_fatalities": 2,
        }
    )
    assert result == SUMMARY_UNAVAILABLE_USER_MESSAGE


@patch("app.services.deepseek.OpenAI")
def test_authentication_error_returns_generic_message(mock_openai):
    client = MagicMock()
    client.chat.completions.create.side_effect = AuthenticationError(
        "invalid key", response=MagicMock(), body=None
    )
    mock_openai.return_value = client

    service = DeepSeekService(api_key="sk-test")
    result = service.generate_aircraft_summary(
        {
            "manufacturer": "Boeing",
            "model_name": "Boeing 737",
            "years_in_service": 40,
            "total_incidents": 10,
            "fatal_incidents": 1,
            "total_fatalities": 2,
        }
    )
    assert result == SUMMARY_UNAVAILABLE_USER_MESSAGE
    assert "invalid" not in result.lower()
    assert "sk-" not in result


@patch("app.services.deepseek.OpenAI")
def test_connection_error_returns_generic_message(mock_openai):
    client = MagicMock()
    client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())
    mock_openai.return_value = client

    service = DeepSeekService(api_key="sk-test")
    result = service.generate_aircraft_summary(
        {
            "manufacturer": "Boeing",
            "model_name": "Boeing 737",
            "years_in_service": 40,
            "total_incidents": 10,
            "fatal_incidents": 1,
            "total_fatalities": 2,
        }
    )
    assert result == SUMMARY_UNAVAILABLE_USER_MESSAGE


@patch("app.services.deepseek.OpenAI")
def test_success_returns_model_content(mock_openai):
    choice = MagicMock()
    choice.message.content = "  Plain text summary.  "
    response = MagicMock()
    response.choices = [choice]
    client = MagicMock()
    client.chat.completions.create.return_value = response
    mock_openai.return_value = client

    service = DeepSeekService(api_key="sk-test")
    result = service.generate_aircraft_summary(
        {
            "manufacturer": "Boeing",
            "model_name": "Boeing 737",
            "years_in_service": 40,
            "total_incidents": 10,
            "fatal_incidents": 1,
            "total_fatalities": 2,
        }
    )
    assert result == "Plain text summary."
