import datetime

import click
from sqlalchemy import inspect

from app import db

from app.ingestion.importers.base import DataSourceImporter

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
    NoopImporter(
        source_name='NTSB',
        start_date=parse_date(start_date),
        end_date=parse_date(end_date),
        incremental=incremental,
    ).run()


@import_data.command('faa-aids')
@click.option('--year', type=int)
@click.option('--incremental', is_flag=True, default=False)
def import_faa_aids(year, incremental):
    require_ingestion_schema()
    NoopImporter(source_name='FAA_AIDS', incremental=incremental).run()


@import_data.command('faa-sdr')
@click.option('--year', type=int)
@click.option('--incremental', is_flag=True, default=False)
def import_faa_sdr(year, incremental):
    require_ingestion_schema()
    NoopImporter(source_name='FAA_SDR', incremental=incremental).run()
