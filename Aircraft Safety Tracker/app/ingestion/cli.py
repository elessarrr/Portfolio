import datetime

import click
from sqlalchemy import inspect

from app import db

from app.ingestion.importers.base import DataSourceImporter
from app.ingestion.importers.ntsb_importer import NTSBImporter
from app.ingestion.importers.faa_aids_importer import FAAAIDSImporter
from app.ingestion.seed.jasc_seed import default_jasc_seed
from app.models import JASCMapping

def parse_date(value):
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%d').date()
    except Exception:
        raise click.ClickException('Invalid date format. Use YYYY-MM-DD.')


def require_ingestion_schema():
    inspector = inspect(db.engine)
    required_tables = {'import_log', 'import_state'}
    missing = sorted([name for name in required_tables if not inspector.has_table(name)])
    if missing:
        raise click.ClickException(
            f"Missing database tables: {', '.join(missing)}. Run `flask db upgrade` first."
        )


class NoopImporter(DataSourceImporter):
    def __init__(self, source_name, **kwargs):
        super().__init__(**kwargs)
        self.source_name = source_name

    def fetch(self):
        return []

    def parse(self, raw_record):
        return None

    def upsert(self, parsed_record):
        return None


@click.group('import-data')
def import_data():
    pass


@import_data.command('seed-jasc')
def seed_jasc():
    require_ingestion_schema()
    rows = default_jasc_seed()
    for row in rows:
        code = row['jasc_code']
        system_name = row['system_name']
        existing = JASCMapping.query.filter_by(jasc_code=code).first()
        if existing:
            existing.system_name = system_name
        else:
            db.session.add(JASCMapping(jasc_code=code, system_name=system_name, confidence='Medium'))
    db.session.commit()


@import_data.command('all')
@click.option('--incremental', is_flag=True, default=False)
def import_all(incremental):
    require_ingestion_schema()
    sources = ['NTSB', 'FAA_AIDS', 'FAA_SDR', 'ASN']
    failures = []
    for source in sources:
        try:
            NoopImporter(source_name=source, incremental=incremental).run()
        except Exception:
            failures.append(source)
    if failures:
        raise click.ClickException(f"One or more sources failed: {', '.join(failures)}")


@import_data.command('ntsb')
@click.option('--start-date')
@click.option('--end-date')
@click.option('--incremental', is_flag=True, default=False)
def import_ntsb(start_date, end_date, incremental):
    require_ingestion_schema()
    NTSBImporter(
        start_date=parse_date(start_date),
        end_date=parse_date(end_date),
        incremental=incremental,
        records=[],
    ).run()


@import_data.command('faa-aids')
@click.option('--year', type=int)
@click.option('--month', type=int)
@click.option('--incremental', is_flag=True, default=False)
def import_faa_aids(year, month, incremental):
    require_ingestion_schema()
    FAAAIDSImporter(incremental=incremental, records=[]).run()


@import_data.command('faa-sdr')
@click.option('--year', type=int)
@click.option('--incremental', is_flag=True, default=False)
def import_faa_sdr(year, incremental):
    require_ingestion_schema()
    NoopImporter(source_name='FAA_SDR', incremental=incremental).run()
