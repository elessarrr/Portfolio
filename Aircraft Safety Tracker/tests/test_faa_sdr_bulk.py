import httpx

from app.ingestion.bulk.faa_sdr_bulk import (
    build_faa_sdr_csv_url,
    download_sdr_csv_text,
    iter_sdr_records,
)


def test_build_faa_sdr_csv_url(monkeypatch):
    monkeypatch.setenv('FAA_SDR_CSV_URL_TEMPLATE', 'https://example.com/sdr_{year}.csv')
    assert build_faa_sdr_csv_url(2023) == 'https://example.com/sdr_2023.csv'


def test_iter_sdr_records_parses_csv():
    csv_text = 'a,b\n1,2\n'
    rows = list(iter_sdr_records(csv_text))
    assert rows == [{'a': '1', 'b': '2'}]


def test_download_sdr_csv_text_retries_on_429(monkeypatch):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(429, headers={'Retry-After': '0'})
        return httpx.Response(200, text='a,b\n1,2\n')

    transport = httpx.MockTransport(handler)
    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)

    content = download_sdr_csv_text(
        'https://example.com/file.csv',
        transport=transport,
        sleep=fake_sleep,
        max_retries=2,
    )
    assert 'a,b' in content
    assert len(calls) == 2
    assert slept

