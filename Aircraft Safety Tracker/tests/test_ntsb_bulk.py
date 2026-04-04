import io
import zipfile
from pathlib import Path

import httpx

from app.ingestion.bulk.ntsb_bulk import (
    NTSBBulkUnsupportedFormat,
    download_zip_bytes,
    extract_zip_bytes,
    iter_tab_delimited_records,
)


def make_zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_extract_and_parse_tab_delimited(tmp_path):
    zip_bytes = make_zip_bytes({
        'events.txt': 'col1\tcol2\n1\tA\n2\tB\n',
    })
    extracted = extract_zip_bytes(zip_bytes, tmp_path)
    rows = [row for _path, row in iter_tab_delimited_records(extracted)]
    assert rows == [
        {'col1': '1', 'col2': 'A'},
        {'col1': '2', 'col2': 'B'},
    ]


def test_raises_on_mdb_file(tmp_path):
    zip_bytes = make_zip_bytes({
        'avall.mdb': b'\x00\x01\x02',
    })
    extracted = extract_zip_bytes(zip_bytes, tmp_path)
    try:
        list(iter_tab_delimited_records(extracted))
        assert False
    except NTSBBulkUnsupportedFormat:
        assert True


def test_download_zip_bytes_retries_on_429(monkeypatch):
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

    content = download_zip_bytes(
        'https://example.com/file.zip',
        transport=transport,
        sleep=fake_sleep,
        max_retries=2,
    )
    assert content == b'zip'
    assert len(calls) == 2
    assert slept

