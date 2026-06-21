"""NTSB bulk (monthly .mdb update) adapter tests — PRD 0012 Task 3.0.

The adapter turns NTSB avdata Microsoft Access exports into records that the
existing `NTSBImporter` already understands, filtered to Boeing/Airbus and
diffed against rows already in the DB. mdbtools / HTTP I/O are isolated so these
tests run offline.
"""

from __future__ import annotations

from app.ingestion.clients.ntsb_bulk import (
    build_records,
    diff_new_records,
    parse_latest_update_url,
)
from app.ingestion.importers.ntsb_importer import NTSBImporter

LISTING_HTML = """
<table>
  <tr><td id="fileName">avall.zip</td><td id="fileDate">6/15/2026 3:00:00 AM</td>
      <td><a href="/avdata/FileDirectory/DownloadFile?fileID=C%3A%5Cavdata%5Cavall.zip">avall.zip</a></td></tr>
  <tr><td id="fileName">up01JUN.zip</td><td id="fileDate">6/1/2026 3:00:20 AM</td>
      <td><a href="/avdata/FileDirectory/DownloadFile?fileID=C%3A%5Cavdata%5Cup01JUN.zip">up01JUN.zip</a></td></tr>
  <tr><td id="fileName">up15JUN.zip</td><td id="fileDate">6/15/2026 3:00:20 AM</td>
      <td><a href="/avdata/FileDirectory/DownloadFile?fileID=C%3A%5Cavdata%5Cup15JUN.zip">up15JUN.zip</a></td></tr>
  <tr><td id="fileName">up01JUL.zip</td><td id="fileDate">7/1/2025 3:00:29 AM</td>
      <td><a href="/avdata/FileDirectory/DownloadFile?fileID=C%3A%5Cavdata%5Cup01JUL.zip">up01JUL.zip</a></td></tr>
</table>
"""

EVENTS = [
    {
        "ev_id": "20260601X00001",
        "ntsb_no": "WPR26LA178",
        # Real mdb-export output format: MM/DD/YY with a time component.
        "ev_date": "04/25/26 00:00:00",
        "ev_city": "Everett",
        "ev_state": "WA",
        "ev_country": "USA",
        "inj_tot_f": "0",
    },
    {
        "ev_id": "20260601X00002",
        "ntsb_no": "ERA26FA166",
        "ev_date": "04/13/26 00:00:00",
        "ev_city": "Bronson",
        "ev_state": "FL",
        "ev_country": "USA",
        "inj_tot_f": "2",
    },
]

AIRCRAFT = [
    {
        "ev_id": "20260601X00001",
        "Aircraft_Key": "1",
        "acft_make": "BOEING",
        "acft_model": "737",
        "oper_name": "DELTA AIR LINES",
        "far_part": "121",
    },
    {
        # Non-Boeing/Airbus → must be excluded.
        "ev_id": "20260601X00002",
        "Aircraft_Key": "1",
        "acft_make": "CESSNA",
        "acft_model": "172",
        "oper_name": "PRIVATE",
        "far_part": "091",
    },
]


def test_parse_latest_update_url_picks_newest_weekly_update():
    url = parse_latest_update_url(LISTING_HTML)
    # Skips avall.zip (full snapshot); picks the most recently dated up*.zip.
    assert "up15JUN.zip" in url
    assert url.startswith("https://data.ntsb.gov/")


def test_build_records_filters_boeing_airbus_and_maps_fields():
    records = build_records(EVENTS, AIRCRAFT)
    assert len(records) == 1
    rec = records[0]
    assert rec["ntsb_id"] == "WPR26LA178"
    assert rec["make_model"] == "BOEING 737"
    assert rec["event_date"] == "2026-04-25"
    assert rec["fatalities"] == "0"
    assert rec["location"] == "Everett, WA"
    assert rec["operator"] == "DELTA AIR LINES"
    assert rec["ev_id"] == "20260601X00001"


def test_diff_new_records_excludes_existing_ids():
    records = build_records(EVENTS, AIRCRAFT)
    assert diff_new_records(records, existing_ids={"WPR26LA178"}) == []
    assert len(diff_new_records(records, existing_ids=set())) == 1


def test_built_records_are_importer_compatible():
    """A built record must parse cleanly through the existing NTSBImporter."""
    rec = build_records(EVENTS, AIRCRAFT)[0]
    parsed = NTSBImporter.parse(rec)
    assert parsed is not None
    assert parsed["source_record_id"] == "WPR26LA178"
    assert parsed["make_model"] == "BOEING 737"
    assert parsed["location"] == "Everett, WA"
    # Deterministic docket URL with no network (fetcher=None path).
    assert parsed["source_url"] == "https://data.ntsb.gov/Docket/?NTSBNumber=WPR26LA178"
