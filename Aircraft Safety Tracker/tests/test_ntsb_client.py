import httpx

from app.ingestion.clients.ntsb import NTSBApiClient


def test_ntsb_client_retries_on_429(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.url)
        if len(calls) == 1:
            return httpx.Response(429, headers={'Retry-After': '0'})
        return httpx.Response(200, json=[{'id': 1}])

    transport = httpx.MockTransport(handler)
    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)

    client = NTSBApiClient(base_url='https://example.com', transport=transport, sleep=fake_sleep)
    try:
        data = client.request_json('GET', '/test')
    finally:
        client.close()

    assert data == [{'id': 1}]
    assert len(calls) == 2
    assert slept


def test_ntsb_client_iter_batches_uses_offset_and_limit(monkeypatch):
    seen = []

    def handler(request):
        params = dict(request.url.params)
        seen.append((int(params.get('offset', '0')), int(params.get('limit', '0'))))
        if len(seen) == 1:
            return httpx.Response(200, json=[{'id': 1}, {'id': 2}])
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    client = NTSBApiClient(base_url='https://example.com', transport=transport, sleep=lambda _: None)
    try:
        batches = list(client.iter_batches('/test', base_params={}, batch_size=2))
    finally:
        client.close()

    assert batches == [[{'id': 1}, {'id': 2}]]
    assert seen[0] == (0, 2)

