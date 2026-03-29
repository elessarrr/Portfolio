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
BOEING_INCIDENTS_PATH = os.path.join(DATA_DIR, 'raw', 'boeing_incidents.json')
AIRBUS_INCIDENTS_PATH = os.path.join(DATA_DIR, 'raw', 'airbus_incidents.json')


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


def _get_paths_for_manufacturer(manufacturer):
    key = (manufacturer or '').strip().lower()
    if key == 'boeing':
        return {
            'name': 'Boeing',
            'type_index_url': BOEING_TYPE_INDEX_URL,
            'catalog_path': BOEING_CATALOG_PATH,
            'incidents_path': BOEING_INCIDENTS_PATH,
            'manufacturer_prefix': 'Boeing',
        }
    if key == 'airbus':
        return {
            'name': 'Airbus',
            'type_index_url': AIRBUS_TYPE_INDEX_URL,
            'catalog_path': AIRBUS_CATALOG_PATH,
            'incidents_path': AIRBUS_INCIDENTS_PATH,
            'manufacturer_prefix': 'Airbus',
        }
    raise ValueError(f"Unsupported manufacturer: {manufacturer}")


def load_catalog_links(manufacturer):
    info = _get_paths_for_manufacturer(manufacturer)
    try:
        with open(info['catalog_path'], 'r', encoding='utf-8') as f:
            return json.load(f) or {}
    except FileNotFoundError:
        with httpx.Client() as client:
            from scraper_utils import get_model_links
            links = get_model_links(client, info['type_index_url'], info['manufacturer_prefix'])
        os.makedirs(os.path.dirname(info['catalog_path']), exist_ok=True)
        with open(info['catalog_path'], 'w', encoding='utf-8') as f:
            json.dump(links, f, indent=2)
        return links


def run_incident_scrape(manufacturer, resume=True, max_models=None):
    info = _get_paths_for_manufacturer(manufacturer)
    manufacturer_name = info['name']
    model_links = load_catalog_links(manufacturer_name)

    if max_models is not None:
        try:
            max_models = int(max_models)
        except Exception:
            max_models = None

    with AsnSyncLock():
        incidents = []
        completed_models = set()

        if resume and os.path.exists(info['incidents_path']):
            try:
                with open(info['incidents_path'], 'r', encoding='utf-8') as f:
                    incidents = json.load(f) or []
                completed_models = {item.get('model_name') for item in incidents if item.get('model_name')}
            except Exception:
                incidents = []
                completed_models = set()

        state = read_sync_state()
        progress_key = f"asn_full_scrape_progress_{manufacturer_name.lower()}"
        if resume:
            completed_from_state = (state or {}).get(progress_key, {}).get('completed_models')
            if isinstance(completed_from_state, list):
                completed_models.update({x for x in completed_from_state if isinstance(x, str) and x})

        os.makedirs(os.path.dirname(info['incidents_path']), exist_ok=True)

        with httpx.Client() as client:
            from scraper_utils import scrape_model_incidents

            processed = 0
            for model_name, url in model_links.items():
                if not model_name or not url:
                    continue
                if model_name in completed_models:
                    continue
                if max_models is not None and processed >= max_models:
                    break

                model_incidents = scrape_model_incidents(model_name, url, client)
                incidents.extend(model_incidents)
                completed_models.add(model_name)
                processed += 1

                with open(info['incidents_path'], 'w', encoding='utf-8') as f:
                    json.dump(incidents, f, indent=2)

                state = read_sync_state()
                state[progress_key] = {
                    'completed_models': sorted(completed_models),
                    'total_models': len(model_links),
                    'last_model_completed': model_name,
                    'updated_at': int(time.time()),
                    'incidents_written': len(incidents),
                }
                write_sync_state(state)

                time.sleep(2.0)

        state = read_sync_state()
        state[f"last_successful_asn_full_scrape_at_{manufacturer_name.lower()}"] = int(time.time())
        state[f"last_successful_asn_full_scrape_counts_{manufacturer_name.lower()}"] = {
            'models_completed': len(completed_models),
            'models_total': len(model_links),
            'incidents_total': len(incidents),
        }
        write_sync_state(state)

        return {
            'manufacturer': manufacturer_name,
            'models_total': len(model_links),
            'models_completed': len(completed_models),
            'incidents_total': len(incidents),
            'incidents_path': info['incidents_path'],
        }


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

    scraped = {
        'Boeing': {
            'incidents_total': None,
            'models_unique': None,
        },
        'Airbus': {
            'incidents_total': None,
            'models_unique': None,
        },
    }

    for name, path in [('Boeing', BOEING_INCIDENTS_PATH), ('Airbus', AIRBUS_INCIDENTS_PATH)]:
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    items = json.load(f) or []
                scraped[name]['incidents_total'] = len(items)
                scraped[name]['models_unique'] = len({i.get('model_name') for i in items if i.get('model_name')})
        except Exception:
            pass

    report = {
        'generated_at': int(time.time()),
        'catalog': {
            'Boeing': discovered_boeing,
            'Airbus': discovered_airbus,
            'last_successful_asn_catalog_sync_at': (state or {}).get('last_successful_asn_catalog_sync_at'),
        },
        'scraped': scraped,
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
    parser.add_argument('--mode', choices=['catalog', 'full', 'reconcile'], default='catalog')
    parser.add_argument('--manufacturer', choices=['boeing', 'airbus', 'all'], default='all')
    parser.add_argument('--no-resume', action='store_true')
    parser.add_argument('--max-models', default=None)
    args = parser.parse_args(argv)

    if args.mode == 'catalog':
        if args.dry_run:
            boeing_links = load_catalog_links('Boeing')
            airbus_links = load_catalog_links('Airbus')
            print(json.dumps({'Boeing': len(boeing_links), 'Airbus': len(airbus_links)}, indent=2))
            return 0
        run_catalog_discovery()
        return 0

    if args.mode == 'reconcile':
        report = build_reconciliation_report()
        if args.dry_run:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            write_reconciliation_report(report)
        return 0

    resume = not args.no_resume
    if args.manufacturer in {'boeing', 'all'}:
        run_incident_scrape('Boeing', resume=resume, max_models=args.max_models)
    if args.manufacturer in {'airbus', 'all'}:
        run_incident_scrape('Airbus', resume=resume, max_models=args.max_models)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
