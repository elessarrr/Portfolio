import io
import os
import zipfile

import httpx

from app.ingestion.bulk.faa_aids_bulk import (
    build_faa_aids_zip_url,
    download_aids_zip_bytes,
    extract_aids_zip_bytes,
    iter_aids_records,
)


def make_zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_build_faa_aids_zip_url_year_only(monkeypatch):
    monkeypatch.setenv('FAA_AIDS_ZIP_URL_TEMPLATE', 'https://example.com/aids_{year}.zip')
    assert build_faa_aids_zip_url(2024) == 'https://example.com/aids_2024.zip'


def test_build_faa_aids_zip_url_year_month(monkeypatch):
    monkeypatch.setenv('FAA_AIDS_ZIP_URL_TEMPLATE', 'https://example.com/aids_{year}_{month}.zip')
    assert build_faa_aids_zip_url(2024, 3) == 'https://example.com/aids_2024_03.zip'


def test_extract_and_parse_aids_records(tmp_path):
    zip_bytes = make_zip_bytes({
        'aids.txt': 'date\treg\n2024-01-01\tN12345\n',
    })
    extracted = extract_aids_zip_bytes(zip_bytes, tmp_path)
    rows = list(iter_aids_records(extracted))
    assert rows == [{'date': '2024-01-01', 'reg': 'N12345'}]


def test_download_aids_zip_bytes_retries_on_429(monkeypatch):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(429, headers={'Retry-After': '0'})
        return httpx.Response(200, content=b'zip')

    transport = httpx.MockTransport(handler)
    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)

    content = download_aids_zip_bytes(
        'https://example.com/file.zip',
        transport=transport,
        sleep=fake_sleep,
        max_retries=2,
    )
    assert content == b'zip'
    assert len(calls) == 2
    assert slept

