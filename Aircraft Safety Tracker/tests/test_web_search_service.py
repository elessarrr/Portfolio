"""
Unit tests for app/services/web_search.py (Task 1.0).

These tests mock httpx at the function-call level so no real network calls are made.
"""

import pytest
from unittest.mock import patch, MagicMock
import httpx

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.web_search import (
    SearchResult,
    WebSearchService,
    validate_url,
    _rate_limit,
    _extract_links_from_html,
    _build_aviation_herald_query,
    _build_news_wire_query,
    _build_general_query,
    _duckduckgo_search,
    _google_cse_search,
)


# ---------------------------------------------------------------------------
# validate_url
# ---------------------------------------------------------------------------

def test_validate_url_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "x" * 200

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        is_valid, status, err = validate_url("https://example.com/article")
        assert is_valid is True
        assert status == 200
        assert err is None


def test_validate_url_404():
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "not found"

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        is_valid, status, err = validate_url("https://example.com/missing")
        assert is_valid is False
        assert status == 404
        assert "http_404" in err


def test_validate_url_body_too_small():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "too short"

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        is_valid, status, err = validate_url("https://example.com/short")
        assert is_valid is False
        assert err == "body_too_small"


def test_validate_url_none():
    is_valid, status, err = validate_url(None)
    assert is_valid is False
    assert err == "url_is_none"


def test_validate_url_timeout():
    """
    After 3 retries all raising TimeoutException, _retry gives up and raises.
    The outer try/except in validate_url catches it and returns the
    'timeout_or_transport_error_after_retry' sentinel.
    """
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.TimeoutException("timed out")
        mock_client_cls.return_value = mock_client

        is_valid, status, err = validate_url("https://example.com/slow")
        assert is_valid is False
        assert err == "timeout_or_transport_error_after_retry"
        # 3 attempts should have been made
        assert mock_client.get.call_count == 3


def test_validate_url_transport_error():
    """
    Same as timeout: after 3 retries all raising TransportError, the
    consolidated sentinel is returned.
    """
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.TransportError("connection refused")
        mock_client_cls.return_value = mock_client

        is_valid, status, err = validate_url("https://example.com/dead")
        assert is_valid is False
        assert err == "timeout_or_transport_error_after_retry"
        assert mock_client.get.call_count == 3


# ---------------------------------------------------------------------------
# _extract_links_from_html
# ---------------------------------------------------------------------------

def test_extract_links_from_html():
    html = '''
    <html><body>
        <a href="https://reuters.com/article1">Article 1</a>
        <a href="https://apnews.com/article2">Article 2</a>
        <a href="https://reuters.com/article3">Article 3</a>
    </body></html>
    '''
    links = _extract_links_from_html(html, "https://search.example.com")
    domains = [l.split("/")[2] for l in links]
    assert "reuters.com" in domains
    assert "apnews.com" in domains
    assert domains.count("reuters.com") == 1  # deduplicated


# ---------------------------------------------------------------------------
# Query builders
# ---------------------------------------------------------------------------

def test_build_aviation_herald_query():
    q = _build_aviation_herald_query("WPR24LA999", "N12345", "2024-03-15")
    assert "WPR24LA999" in q
    assert "N12345" in q
    assert "2024" in q


def test_build_news_wire_query():
    q = _build_news_wire_query("WPR24LA999", "N12345", "Delta Air Lines", "2024-03-15")
    assert "WPR24LA999" in q
    assert "N12345" in q
    assert "Delta Air Lines" in q
    assert "2024" in q


def test_build_general_query():
    q = _build_general_query("WPR24LA999", "N12345", "Delta Air Lines", "Tokyo", "2024-03-15")
    assert "WPR24LA999" in q
    assert "N12345" in q
    assert "Delta Air Lines" in q
    assert "Tokyo" in q
    assert "2024" in q


# ---------------------------------------------------------------------------
# DuckDuckGo search (mocked)
# ---------------------------------------------------------------------------

def test_duckduckgo_search_returns_results():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = (
        '<html><body>'
        '<a href="https://aviation-herald.com/article1">AH Article</a>'
        '<a href="https://reuters.com/article2">Reuters Article</a>'
        '</body></html>'
    )

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        results = _duckduckgo_search("site:aviation-herald.com WPR24LA999", tier=1)
        assert len(results) == 2
        assert results[0].tier == 1
        assert results[0].domain == "aviation-herald.com"
        assert results[1].domain == "reuters.com"


def test_duckduckgo_search_blocked():
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "forbidden"

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        results = _duckduckgo_search("WPR24LA999", tier=3)
        assert results == []


def test_google_cse_search_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {"link": "https://aviation-herald.com/article1", "title": "AH 1"},
            {"link": "https://reuters.com/article2", "title": "Reuters 2"},
        ]
    }

    with patch.dict("os.environ", {
        "GOOGLE_CSE_API_KEY": "fake-key",
        "GOOGLE_CSE_CX": "fake-cx",
    }, clear=False):
        with patch("app.services.web_search._GOOGLE_CSE_API_KEY", None), \
             patch("app.services.web_search._GOOGLE_CSE_CX", None), \
             patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            results = _google_cse_search("site:aviation-herald.com WPR24LA999", tier=1, max_results=2)
            assert len(results) == 2
            assert results[0].url == "https://aviation-herald.com/article1"
            assert results[0].title == "AH 1"
            assert results[0].tier == 1


def test_google_cse_search_quota_exceeded_returns_empty():
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "quota exceeded"

    with patch.dict("os.environ", {
        "GOOGLE_CSE_API_KEY": "fake-key",
        "GOOGLE_CSE_CX": "fake-cx",
    }, clear=False):
        with patch("app.services.web_search._GOOGLE_CSE_API_KEY", None), \
             patch("app.services.web_search._GOOGLE_CSE_CX", None), \
             patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            results = _google_cse_search("WPR24LA999", tier=3)
            assert results == []


def test_google_cse_search_missing_keys_returns_empty():
    with patch.dict("os.environ", {}, clear=True):
        with patch("app.services.web_search._GOOGLE_CSE_API_KEY", None), \
             patch("app.services.web_search._GOOGLE_CSE_CX", None):
            results = _google_cse_search("WPR24LA999", tier=3)
            assert results == []


# ---------------------------------------------------------------------------
# WebSearchService – search_tiered (mocked tier functions)
# ---------------------------------------------------------------------------

@patch("app.services.web_search._search_aviation_herald")
@patch("app.services.web_search._search_news_wires")
@patch("app.services.web_search._search_general")
def test_search_tiered_stops_at_tier1(mock_general, mock_wires, mock_herald):
    mock_herald.return_value = [
        SearchResult(url="https://aviation-herald.com/abc", tier=1, domain="aviation-herald.com"),
    ]
    svc = WebSearchService(validate=False)
    results = svc.search_tiered(
        event_id="WPR24LA999", registration="N12345",
        operator="Delta", location="Tokyo", date="2024-03-15"
    )

    assert len(results) == 1
    assert results[0].tier == 1
    mock_wires.assert_not_called()
    mock_general.assert_not_called()


@patch("app.services.web_search._search_aviation_herald")
@patch("app.services.web_search._search_news_wires")
@patch("app.services.web_search._search_general")
def test_search_tiered_falls_through_to_tier2(mock_general, mock_wires, mock_herald):
    mock_herald.return_value = []
    mock_wires.return_value = [
        SearchResult(url="https://reuters.com/xyz", tier=2, domain="reuters.com"),
    ]
    svc = WebSearchService(validate=False)
    results = svc.search_tiered(
        event_id="WPR24LA999", registration="N12345",
        operator="Delta", location="Tokyo", date="2024-03-15"
    )

    assert len(results) == 1
    assert results[0].tier == 2
    mock_general.assert_not_called()


@patch("app.services.web_search._search_aviation_herald")
@patch("app.services.web_search._search_news_wires")
@patch("app.services.web_search._search_general")
def test_search_tiered_all_tiers_empty(mock_general, mock_wires, mock_herald):
    mock_herald.return_value = []
    mock_wires.return_value = []
    mock_general.return_value = [
        SearchResult(url="https://example.com/article", tier=3, domain="example.com"),
    ]
    svc = WebSearchService(validate=False)
    results = svc.search_tiered(event_id="WPR24LA999", registration="N12345",
                                operator="Delta", location="Tokyo", date="2024-03-15")

    assert len(results) == 1
    assert results[0].tier == 3


@patch("app.services.web_search._search_aviation_herald")
@patch("app.services.web_search._search_news_wires")
@patch("app.services.web_search._search_general")
def test_search_tiered_respects_max_5(mock_general, mock_wires, mock_herald):
    mock_herald.return_value = []
    mock_wires.return_value = []
    many = [
        SearchResult(url=f"https://example{i}.com/a", tier=3, domain=f"example{i}.com")
        for i in range(8)
    ]
    mock_general.return_value = many
    svc = WebSearchService(validate=False)
    results = svc.search_tiered(event_id="WPR24LA999")

    assert len(results) == 5


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

def test_rate_limit_no_url():
    # Should not raise
    _rate_limit("")


def test_rate_limit_calls_sleep():
    with patch("time.sleep") as mock_sleep:
        # First call – no sleep
        _rate_limit("https://example.com/page1")
        assert mock_sleep.call_count == 0

        # Immediate second call to same domain – should sleep
        _rate_limit("https://example.com/page2")
        assert mock_sleep.call_count == 1
