import json
import os
import time
import argparse
import sys

import httpx


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
SYNC_STATE_PATH = os.path.join(DATA_DIR, 'asn_sync_state.json')
LOCK_PATH = os.path.join(DATA_DIR, 'asn_sync.lock')
RECONCILIATION_REPORT_PATH = os.path.join(DATA_DIR, 'asn_reconciliation_report.json')

BOEING_TYPE_INDEX_URL = 'https://aviation-safety.net/asndb/types/B'
AIRBUS_TYPE_INDEX_URL = 'https://aviation-safety.net/asndb/types/A'
BOEING_CATALOG_PATH = os.path.join(DATA_DIR, 'raw', 'asn_catalog_boeing.json')
AIRBUS_CATALOG_PATH = os.path.join(DATA_DIR, 'raw', 'asn_catalog_airbus.json')


class AsnSyncLockError(RuntimeError):
    pass


class AsnSyncLock:
    def __init__(self, lock_path=LOCK_PATH, stale_seconds=60 * 60):
        self.lock_path = lock_path
        self.stale_seconds = stale_seconds
        self._fd = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)

        try:
            self._fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            payload = {
                'pid': os.getpid(),
                'created_at': int(time.time()),
            }
            os.write(self._fd, json.dumps(payload).encode('utf-8'))
            os.fsync(self._fd)
            return self
        except FileExistsError:
            try:
                stat = os.stat(self.lock_path)
                age_seconds = time.time() - stat.st_mtime
            except FileNotFoundError:
                return self.__enter__()

            if age_seconds > self.stale_seconds:
                try:
                    os.remove(self.lock_path)
                except FileNotFoundError:
                    return self.__enter__()
                return self.__enter__()

            raise AsnSyncLockError(f"ASN sync already running (lock exists at {self.lock_path}).")

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._fd is not None:
                os.close(self._fd)
        finally:
            self._fd = None
            try:
                os.remove(self.lock_path)
            except FileNotFoundError:
                pass


def read_sync_state(path=SYNC_STATE_PATH):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def write_sync_state(state, path=SYNC_STATE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(state or {}, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def get_last_successful_catalog_sync_at(state):
    value = (state or {}).get('last_successful_asn_catalog_sync_at')
    if isinstance(value, int):
        return value
    value = (state or {}).get('last_successful_asn_sync_at')
    if isinstance(value, int):
        return value
    return None


def should_trigger_catalog_sync(state, interval_days=7, now_ts=None):
    if interval_days is None:
        interval_days = 7
    try:
        interval_days = int(interval_days)
    except Exception:
        interval_days = 7

    last_sync_at = get_last_successful_catalog_sync_at(state or {})
    if last_sync_at is None:
        return True

    now_ts = time.time() if now_ts is None else now_ts
    return (now_ts - last_sync_at) >= interval_days * 86400


def run_catalog_discovery():
    try:
        with AsnSyncLock():
            from scraper_utils import get_model_links

            with httpx.Client() as client:
                boeing_links = get_model_links(client, BOEING_TYPE_INDEX_URL, 'Boeing')
                airbus_links = get_model_links(client, AIRBUS_TYPE_INDEX_URL, 'Airbus')

            os.makedirs(os.path.dirname(BOEING_CATALOG_PATH), exist_ok=True)
            with open(BOEING_CATALOG_PATH, 'w', encoding='utf-8') as f:
                json.dump(boeing_links, f, indent=2)

            with open(AIRBUS_CATALOG_PATH, 'w', encoding='utf-8') as f:
                json.dump(airbus_links, f, indent=2)

            state = read_sync_state()
            state.update({
                'last_successful_asn_catalog_sync_at': int(time.time()),
                'last_successful_asn_catalog_sync_source': 'asn_sync.run_catalog_discovery',
                'last_successful_asn_catalog_sync_counts': {
                    'Boeing': len(boeing_links),
                    'Airbus': len(airbus_links),
                },
            })
            write_sync_state(state)

            return state
    except AsnSyncLockError:
        return None


def build_reconciliation_report():
    state = read_sync_state()

    discovered_boeing = None
    discovered_airbus = None
    try:
        if os.path.exists(BOEING_CATALOG_PATH):
            with open(BOEING_CATALOG_PATH, 'r', encoding='utf-8') as f:
                discovered_boeing = len(json.load(f) or {})
        if os.path.exists(AIRBUS_CATALOG_PATH):
            with open(AIRBUS_CATALOG_PATH, 'r', encoding='utf-8') as f:
                discovered_airbus = len(json.load(f) or {})
    except Exception:
        discovered_boeing = None
        discovered_airbus = None

    if discovered_boeing is None or discovered_airbus is None:
        counts = (state or {}).get('last_successful_asn_catalog_sync_counts') or {}
        discovered_boeing = discovered_boeing if discovered_boeing is not None else counts.get('Boeing')
        discovered_airbus = discovered_airbus if discovered_airbus is not None else counts.get('Airbus')

    imported_boeing = None
    imported_airbus = None
    variants_boeing = None
    variants_airbus = None

    try:
        from app import create_app, db
        from app.models import Aircraft, AircraftVariant

        app = create_app('development')
        with app.app_context():
            imported_boeing = Aircraft.query.filter(Aircraft.manufacturer == 'Boeing').count()
            imported_airbus = Aircraft.query.filter(Aircraft.manufacturer == 'Airbus').count()
            variants_boeing = db.session.query(AircraftVariant).join(Aircraft).filter(Aircraft.manufacturer == 'Boeing').count()
            variants_airbus = db.session.query(AircraftVariant).join(Aircraft).filter(Aircraft.manufacturer == 'Airbus').count()
    except Exception:
        pass

    def pct(imported, discovered):
        try:
            if imported is None or discovered in (None, 0):
                return None
            return round((imported / discovered) * 100.0, 1)
        except Exception:
            return None

    report = {
        'generated_at': int(time.time()),
        'catalog': {
            'Boeing': discovered_boeing,
            'Airbus': discovered_airbus,
            'last_successful_asn_catalog_sync_at': (state or {}).get('last_successful_asn_catalog_sync_at'),
        },
        'database': {
            'Aircraft': {
                'Boeing': imported_boeing,
                'Airbus': imported_airbus,
            },
            'AircraftVariant': {
                'Boeing': variants_boeing,
                'Airbus': variants_airbus,
            },
            'last_successful_asn_sync_at': (state or {}).get('last_successful_asn_sync_at'),
        },
        'coverage_percent': {
            'Aircraft': {
                'Boeing': pct(imported_boeing, discovered_boeing),
                'Airbus': pct(imported_airbus, discovered_airbus),
            }
        },
    }

    return report


def write_reconciliation_report(report, path=RECONCILIATION_REPORT_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(report or {}, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)

    try:
        state = read_sync_state()
        state['last_reconciliation_report_at'] = int(time.time())
        state['last_reconciliation_report_path'] = path
        write_sync_state(state)
    except Exception:
        pass


def main(argv=None):
    parser = argparse.ArgumentParser(description='ASN sync utilities')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and report without writing state/files')
    args = parser.parse_args(argv)

    with httpx.Client() as client:
        from scraper_utils import get_model_links
        boeing_links = get_model_links(client, BOEING_TYPE_INDEX_URL, 'Boeing')
        airbus_links = get_model_links(client, AIRBUS_TYPE_INDEX_URL, 'Airbus')

    if args.dry_run:
        print(json.dumps({'Boeing': len(boeing_links), 'Airbus': len(airbus_links)}, indent=2))
        return 0

    run_catalog_discovery()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
