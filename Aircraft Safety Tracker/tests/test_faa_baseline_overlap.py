"""FAA baseline overlap visibility (PRD 0009 FR-0 / FR-5.6)."""

from typing import Optional

from app.ingestion.faa_baseline_overlap import incident_visible_on_aircraft_page
from app.models import Incident, IncidentSource


def _source(name: str, url: Optional[str] = None, active: bool = True) -> IncidentSource:
    s = IncidentSource(source_name=name, source_url=url, is_active=active)
    return s


def test_visible_when_primary_href_from_asn():
    inc = Incident(asn_url="https://asn.example/1")
    assert incident_visible_on_aircraft_page(inc, []) is True


def test_hidden_faa_only_without_link():
    inc = Incident(asn_url=None)
    sources = [_source("FAA_AIDS", url=None, active=True)]
    assert incident_visible_on_aircraft_page(inc, sources) is False


def test_visible_faa_with_brief_url():
    inc = Incident(asn_url=None)
    url = "https://www.asias.faa.gov/apex/f?p=100:18:::NO::AP_BRIEF_RPT_VAR:ID1"
    sources = [_source("FAA_AIDS", url=url)]
    assert incident_visible_on_aircraft_page(inc, sources) is True
