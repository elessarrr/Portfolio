"""Tests for ASN incremental scrape short-circuit.

Core behaviour:
- scrape_model_incidents skips the expensive detail fetch for URLs already in the DB
- scrape_boeing/airbus.main thread known_urls through to scrape_model_incidents
- ingest_asn loads known_urls from the DB and passes them to the scrapers
- existing_asn_urls() returns the set of known asn_url values from the DB
"""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

# ---------------------------------------------------------------------------
# Minimal HTML listing fixture — three incidents, two of which are "known"
# ---------------------------------------------------------------------------
_LISTING_HTML = """
<html><body>
<table>
  <tr>
    <th>Acc. date</th><th>Type</th><th>Reg</th><th>Operator</th>
    <th>Fatalities</th><th>Location</th><th>Category</th>
  </tr>
  <tr>
    <td><a href="/wikibase/100">01 Jan 2020</a></td>
    <td>B737</td><td>N123</td><td>Delta</td><td>0</td><td>Atlanta</td><td>A1</td>
  </tr>
  <tr>
    <td><a href="/wikibase/200">02 Feb 2021</a></td>
    <td>B737</td><td>N456</td><td>United</td><td>1</td><td>Denver</td><td>A1</td>
  </tr>
  <tr>
    <td><a href="/wikibase/300">03 Mar 2022</a></td>
    <td>B737</td><td>N789</td><td>Southwest</td><td>0</td><td>Dallas</td><td>A1</td>
  </tr>
</table>
</body></html>
"""

_KNOWN_URLS = frozenset({
    "https://aviation-safety.net/wikibase/100",
    "https://aviation-safety.net/wikibase/200",
})

_NEW_URL = "https://aviation-safety.net/wikibase/300"


# ---------------------------------------------------------------------------
# scraper_utils.scrape_model_incidents — short-circuit behaviour
# ---------------------------------------------------------------------------

class TestScrapeModelIncidentsShortCircuit:

    def _make_client(self):
        client = MagicMock()
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.text = _LISTING_HTML
        client.get.return_value = resp
        return client

    def test_skips_detail_fetch_for_known_urls(self):
        """Detail fetch must NOT be called for incidents already in the DB."""
        from scraper_utils import scrape_model_incidents

        client = self._make_client()
        detail_calls = []

        with patch("scraper_utils.scrape_incident_details") as mock_detail:
            mock_detail.return_value = (0, "narrative")
            incidents = scrape_model_incidents(
                "Boeing 737",
                "https://aviation-safety.net/asndb/type/b737",
                client,
                known_urls=_KNOWN_URLS,
            )
            called_urls = [c.args[0] for c in mock_detail.call_args_list]

        # Only the unknown URL should have triggered a detail fetch
        assert _NEW_URL in called_urls, "new URL should be fetched"
        assert "https://aviation-safety.net/wikibase/100" not in called_urls
        assert "https://aviation-safety.net/wikibase/200" not in called_urls

    def test_returns_only_new_incidents(self):
        """Only the 1 new incident should be returned; known ones are skipped."""
        from scraper_utils import scrape_model_incidents

        client = self._make_client()
        with patch("scraper_utils.scrape_incident_details") as mock_detail:
            mock_detail.return_value = (0, "narrative")
            incidents = scrape_model_incidents(
                "Boeing 737",
                "https://aviation-safety.net/asndb/type/b737",
                client,
                known_urls=_KNOWN_URLS,
            )

        assert len(incidents) == 1
        assert incidents[0]["asn_url"] == _NEW_URL

    def test_empty_known_urls_fetches_all(self):
        """With no known_urls every incident gets a detail fetch (existing behaviour)."""
        from scraper_utils import scrape_model_incidents

        client = self._make_client()
        with patch("scraper_utils.scrape_incident_details") as mock_detail:
            mock_detail.return_value = (0, "narrative")
            incidents = scrape_model_incidents(
                "Boeing 737",
                "https://aviation-safety.net/asndb/type/b737",
                client,
                known_urls=frozenset(),
            )

        assert len(incidents) == 3
        assert mock_detail.call_count == 3


# ---------------------------------------------------------------------------
# scrape_boeing / scrape_airbus — known_urls parameter threads through
# ---------------------------------------------------------------------------

class TestScraperMainKnownUrls:
    # scrape_boeing/airbus import functions directly from scraper_utils at module
    # load time, so we must patch THEIR namespace, not scraper_utils directly.

    def test_scrape_boeing_passes_known_urls(self, tmp_path, monkeypatch):
        import scrape_boeing

        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "raw").mkdir(parents=True)

        known = frozenset({"https://aviation-safety.net/wikibase/999"})
        received = {}

        def fake_scrape_model(name, url, client, known_urls=frozenset()):
            received["known_urls"] = known_urls
            return []

        with patch.object(scrape_boeing, "get_model_links",
                          return_value={"Model X": "https://aviation-safety.net/asndb/type/mx"}):
            with patch.object(scrape_boeing, "scrape_model_incidents",
                              side_effect=fake_scrape_model):
                scrape_boeing.main(known_urls=known)

        assert received.get("known_urls") == known

    def test_scrape_airbus_passes_known_urls(self, tmp_path, monkeypatch):
        import scrape_airbus

        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "raw").mkdir(parents=True)

        known = frozenset({"https://aviation-safety.net/wikibase/888"})
        received = {}

        def fake_scrape_model(name, url, client, known_urls=frozenset()):
            received["known_urls"] = known_urls
            return []

        with patch.object(scrape_airbus, "get_model_links",
                          return_value={"Model X": "https://aviation-safety.net/asndb/type/ax"}):
            with patch.object(scrape_airbus, "scrape_model_incidents",
                              side_effect=fake_scrape_model):
                scrape_airbus.main(known_urls=known)


# ---------------------------------------------------------------------------
# existing_asn_urls() — DB query
# ---------------------------------------------------------------------------

def test_existing_asn_urls_returns_set(app):
    """existing_asn_urls() returns a set of all non-null Incident.asn_url values."""
    from app.ingestion.weekly_ingest import existing_asn_urls
    from app import db
    from app.models import Aircraft, Incident

    with app.app_context():
        a = Aircraft(manufacturer="Test", model_name="Test Model",
                     total_incidents=0, fatal_incidents=0, total_fatalities=0)
        db.session.add(a)
        db.session.flush()
        db.session.add(Incident(aircraft_id=a.id, asn_url="https://asn.net/1"))
        db.session.add(Incident(aircraft_id=a.id, asn_url="https://asn.net/2"))
        db.session.add(Incident(aircraft_id=a.id, asn_url=None))  # null must be excluded
        db.session.commit()

        result = existing_asn_urls()
        assert isinstance(result, (set, frozenset))
        assert "https://asn.net/1" in result
        assert "https://asn.net/2" in result
        assert None not in result


# ---------------------------------------------------------------------------
# ingest_asn — known_urls_fn is called and passed to scrapers
# ---------------------------------------------------------------------------

class TestGetSoupRateLimit:
    """get_soup must back off and retry on HTTP 429 instead of silently dropping."""

    def _resp(self, status, text="<html><body>ok</body></html>", retry_after=None):
        r = MagicMock()
        r.status_code = status
        r.text = text
        r.headers = {"Retry-After": retry_after} if retry_after else {}
        if status >= 400 and status != 429:
            r.raise_for_status.side_effect = Exception(f"{status} error")
        else:
            r.raise_for_status.return_value = None
        return r

    def test_retries_on_429_then_succeeds(self):
        from scraper_utils import get_soup
        client = MagicMock()
        client.get.side_effect = [self._resp(429), self._resp(429), self._resp(200)]
        slept = []
        soup = get_soup("http://x", client, base_delay=1.0, sleep=lambda s: slept.append(s))
        assert soup is not None
        assert client.get.call_count == 3
        assert len(slept) == 2

    def test_respects_retry_after_header(self):
        from scraper_utils import get_soup
        client = MagicMock()
        client.get.side_effect = [self._resp(429, retry_after="7"), self._resp(200)]
        slept = []
        get_soup("http://x", client, base_delay=1.0, sleep=lambda s: slept.append(s))
        assert slept and slept[0] == 7.0

    def test_gives_up_after_max_retries(self):
        from scraper_utils import get_soup
        client = MagicMock()
        client.get.return_value = self._resp(429)
        slept = []
        soup = get_soup("http://x", client, max_retries=3, base_delay=1.0,
                        sleep=lambda s: slept.append(s))
        assert soup is None
        assert client.get.call_count == 4  # initial + 3 retries
        assert len(slept) == 3

    def test_success_no_sleep(self):
        from scraper_utils import get_soup
        client = MagicMock()
        client.get.return_value = self._resp(200)
        slept = []
        soup = get_soup("http://x", client, sleep=lambda s: slept.append(s))
        assert soup is not None
        assert slept == []


def test_ingest_asn_passes_known_urls_to_scrapers(app):
    """ingest_asn must load known URLs from known_urls_fn and pass them to scrapers."""
    from app.ingestion.weekly_ingest import ingest_asn

    known = frozenset({"https://asn.net/old1", "https://asn.net/old2"})
    received_boeing = {}
    received_airbus = {}

    def mock_boeing(known_urls=frozenset()):
        received_boeing["known_urls"] = known_urls
        return 5

    def mock_airbus(known_urls=frozenset()):
        received_airbus["known_urls"] = known_urls
        return 3

    with app.app_context():
        ingest_asn(
            scrape_boeing_fn=mock_boeing,
            scrape_airbus_fn=mock_airbus,
            import_fn=lambda: None,
            known_urls_fn=lambda: known,
        )

    assert received_boeing["known_urls"] == known
    assert received_airbus["known_urls"] == known
