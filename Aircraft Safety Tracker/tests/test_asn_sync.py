import os
import sys
import time

import pytest


@pytest.fixture
def asn_sync_module():
    scripts_dir = os.path.join(os.getcwd(), 'scripts')
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import asn_sync
    return asn_sync


def test_asn_sync_lock_exclusive(tmp_path, asn_sync_module):
    lock_path = tmp_path / 'asn_sync.lock'

    with asn_sync_module.AsnSyncLock(lock_path=str(lock_path), stale_seconds=9999):
        with pytest.raises(asn_sync_module.AsnSyncLockError):
            with asn_sync_module.AsnSyncLock(lock_path=str(lock_path), stale_seconds=9999):
                pass


def test_asn_sync_lock_stale_recovery(tmp_path, asn_sync_module):
    lock_path = tmp_path / 'asn_sync.lock'
    lock_path.write_text('stale')
    stale_mtime = time.time() - 9999
    os.utime(lock_path, (stale_mtime, stale_mtime))

    with asn_sync_module.AsnSyncLock(lock_path=str(lock_path), stale_seconds=1):
        assert lock_path.exists()


def test_should_trigger_catalog_sync(asn_sync_module):
    now = 1_700_000_000

    assert asn_sync_module.should_trigger_catalog_sync({}, interval_days=7, now_ts=now) is True
    assert asn_sync_module.should_trigger_catalog_sync(
        {'last_successful_asn_catalog_sync_at': now - (6 * 86400)},
        interval_days=7,
        now_ts=now,
    ) is False
    assert asn_sync_module.should_trigger_catalog_sync(
        {'last_successful_asn_catalog_sync_at': now - (8 * 86400)},
        interval_days=7,
        now_ts=now,
    ) is True


def test_load_catalog_links_writes_file(tmp_path, monkeypatch, asn_sync_module):
    monkeypatch.setattr(asn_sync_module, 'DATA_DIR', str(tmp_path))
    monkeypatch.setattr(asn_sync_module, 'BOEING_CATALOG_PATH', str(tmp_path / 'raw' / 'asn_catalog_boeing.json'))
    monkeypatch.setattr(asn_sync_module, 'BOEING_TYPE_INDEX_URL', 'https://example.com/types/B')

    class DummyClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(asn_sync_module.httpx, 'Client', lambda *args, **kwargs: DummyClient())

    def fake_get_model_links(_client, _url, _prefix):
        return {'Boeing 707': 'https://example.com/type/707'}

    import scraper_utils
    monkeypatch.setattr(scraper_utils, 'get_model_links', fake_get_model_links)

    links = asn_sync_module.load_catalog_links('Boeing')
    assert links.get('Boeing 707')
