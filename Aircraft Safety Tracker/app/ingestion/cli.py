import datetime
import hashlib
import json
import os

import click
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app import db

from app.ingestion.importers.base import DataSourceImporter
from app.ingestion.importers.ntsb_importer import NTSBImporter
from app.ingestion.importers.faa_aids_importer import FAAAIDSImporter
from app.ingestion.importers.faa_sdr_importer import FAASDRImporter
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
            if source == 'NTSB':
                NTSBImporter(incremental=incremental, records=[]).run()
            elif source == 'FAA_AIDS':
                FAAAIDSImporter(incremental=incremental, records=[]).run()
            elif source == 'FAA_SDR':
                FAASDRImporter(incremental=incremental, records=[]).run()
            else:
                NoopImporter(source_name=source, incremental=incremental).run()
        except Exception:
            failures.append(source)
    if failures:
        raise click.ClickException(f"One or more sources failed: {', '.join(failures)}")


@import_data.command('ntsb')
@click.option('--start-date')
@click.option('--end-date')
@click.option('--incremental', is_flag=True, default=False)
@click.option('--file', help='Path to NTSB CAROL JSON file')
def import_ntsb(start_date, end_date, incremental, file):
    require_ingestion_schema()
    
    file_path = file or "data/raw/ntsb_incidents.json"
    records = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            records = json.load(f)
            
    NTSBImporter(
        start_date=parse_date(start_date),
        end_date=parse_date(end_date),
        incremental=incremental,
        records=records,
    ).run()


@import_data.command('faa-aids')
@click.option('--year', type=int)
@click.option('--month', type=int)
@click.option('--incremental', is_flag=True, default=False)
@click.option('--file', help='Path to FAA AIDS text file')
def import_faa_aids(year, month, incremental, file):
    require_ingestion_schema()
    
    file_path = file or "data/raw/faa_incidents.json"
    records = []
    if os.path.exists(file_path):
        if file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                header = f.readline().strip().split('\t')
                for line in f:
                    row = line.strip().split('\t')
                    if len(row) > 1 and row[0] != 'end_of_record':
                        record = {}
                        for i, v in enumerate(row):
                            if i < len(header) and v and v != 'end_of_record':
                                record[header[i]] = v.strip()
                        records.append(record)
            print(f"Loaded {len(records)} records from TXT")
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                records = json.load(f)
            
    FAAAIDSImporter(incremental=incremental, records=records).run()


@import_data.command('faa-sdr')
@click.option('--year', type=int)
@click.option('--incremental', is_flag=True, default=False)
def import_faa_sdr(year, incremental):
    require_ingestion_schema()
    FAASDRImporter(incremental=incremental, records=[], year=year).run()


# ---------------------------------------------------------------------------
# WA NTSB Suppression (Phase 6 correction)
# ---------------------------------------------------------------------------

@import_data.command('mark-wa-ntsb-inactive')
@click.option(
    '--dry-run/--apply',
    'dry_run',
    default=True,
    help="Dry run by default. Use --apply to mark matching NTSB sources inactive.",
)
def mark_wa_ntsb_inactive(dry_run):
    """
    Mark WA-coded active NTSB IncidentSource rows inactive.

    Match criteria:
      - source_name='NTSB'
      - is_active=True
      - source_record_id LIKE '_____WA%'
    """
    from app.models import IncidentSource

    require_ingestion_schema()

    query = IncidentSource.query.filter(
        IncidentSource.source_name == 'NTSB',
        IncidentSource.is_active == True,
        IncidentSource.source_record_id.like('_____WA%'),
    )
    matches = query.all()
    match_count = len(matches)

    click.echo(f"Matched WA active NTSB sources: {match_count}")
    sample_ids = [row.source_record_id for row in matches[:5] if row.source_record_id]
    if sample_ids:
        click.echo("Sample event IDs:")
        for event_id in sample_ids:
            click.echo(f"  - {event_id}")
    else:
        click.echo("Sample event IDs: none")

    if dry_run:
        click.echo("[DRY RUN] No records were updated.")
        return

    for row in matches:
        row.is_active = False
    db.session.commit()
    click.echo(f"[APPLY] Marked inactive: {match_count}")


# ---------------------------------------------------------------------------
# WA Incident Press Enrichment
# ---------------------------------------------------------------------------

@import_data.command('enrich-wa-incidents')
@click.option('--dry-run', is_flag=True, default=False,
              help="Query targets but do not write any MEDIA sources to the DB.")
@click.option(
    '--max-queries',
    type=int,
    default=None,
    help="Maximum number of search queries (search_tiered calls) to run in this invocation.",
)
def enrich_wa_incidents(dry_run, max_queries):
    """
    Search for press coverage of WA-coded (Western Region) NTSB incidents
    that have no active NTSB source and no existing MEDIA source.

    Target incidents are identified as:
      - Has an IncidentSource with source_name='NTSB' and is_active=False
      - Has NO IncidentSource with source_name='NTSB' and is_active=True
      - Has NO IncidentSource with source_name='MEDIA'

    Each found article is validated (HTTP 200, non-empty body) before storing.
    Search proceeds through three tiers, stopping at the first tier that
    returns at least one validated result:
      Tier 1 – Aviation Herald (site:aviation-herald.com)
      Tier 2 – Major news wires  (Reuters, AP, Bloomberg)
      Tier 3 – General web search

    Usage:
      flask import-data enrich-wa-incidents
      flask import-data enrich-wa-incidents --dry-run
      flask import-data enrich-wa-incidents --max-queries 90
    """
    from app.models import Incident, IncidentSource
    from app.services.web_search import WebSearchService

    require_ingestion_schema()

    # Identify target incidents
    ntsb_source_sub = (
        db.session.query(IncidentSource.incident_id)
        .filter(
            IncidentSource.source_name == 'NTSB',
            IncidentSource.is_active == True,
        )
        .subquery()
    )

    media_source_sub = (
        db.session.query(IncidentSource.incident_id)
        .filter(IncidentSource.source_name == 'MEDIA')
        .subquery()
    )

    inactive_ntsb_sub = (
        db.session.query(IncidentSource.incident_id)
        .filter(
            IncidentSource.source_name == 'NTSB',
            IncidentSource.is_active == False,
        )
        .subquery()
    )

    targets = (
        Incident.query
        .join(inactive_ntsb_sub, Incident.id == inactive_ntsb_sub.c.incident_id)
        .outerjoin(media_source_sub, Incident.id == media_source_sub.c.incident_id)
        .filter(media_source_sub.c.incident_id == None)
        .outerjoin(ntsb_source_sub, Incident.id == ntsb_source_sub.c.incident_id)
        .filter(ntsb_source_sub.c.incident_id == None)
        .all()
    )

    total_checked = len(targets)
    articles_found_t1 = articles_found_t2 = articles_found_t3 = 0
    skipped_count = 0
    no_result_count = 0
    errors_count = 0
    queries_used = 0

    click.echo(f"Found {total_checked} incident(s) to process.")
    if dry_run:
        click.echo("[DRY RUN] No records will be written.")
    if max_queries is not None:
        click.echo(f"Query limit set: {max_queries}")

    svc = WebSearchService(validate=True)

    for incident in targets:
        ntsb_src = next(
            (s for s in incident.sources if s.source_name == 'NTSB'),
            None,
        )
        if not ntsb_src:
            skipped_count += 1
            click.echo(f"  [SKIP] incident_id={incident.id} – NTSB source not found")
            continue

        event_id = ntsb_src.source_record_id or ""
        registration = incident.registration or ""
        operator = incident.operator or ""
        location = incident.location or ""
        date_str = incident.date.isoformat() if incident.date else ""

        if dry_run:
            click.echo(
                f"  [DRY RUN] incident_id={incident.id} event_id={event_id}"
                f" reg={registration} – would search tiers 1→2→3"
            )
            continue

        if max_queries is not None and queries_used >= max_queries:
            click.echo("  [STOP] Reached --max-queries limit.")
            break

        try:
            queries_used += 1
            articles = svc.search_tiered(
                event_id=event_id,
                registration=registration,
                operator=operator,
                location=location,
                date=date_str,
            )
        except Exception as exc:
            errors_count += 1
            click.echo(
                f"  [ERROR] incident_id={incident.id} event_id={event_id}: {exc}"
            )
            continue

        if not articles:
            no_result_count += 1
            click.echo(f"  [NO RESULT] incident_id={incident.id} event_id={event_id}")
            continue

        # Record first (highest-confidence) article as MEDIA source
        best = articles[0]
        # source_record_id is globally unique for MEDIA, so include event context
        # and a stable URL hash instead of only using the domain.
        event_key = (event_id or "").strip() or f"incident-{incident.id}"
        url_hash = hashlib.sha1((best.url or "").encode("utf-8")).hexdigest()[:16]
        source_record_id = f"{event_key}:{url_hash}"

        existing = IncidentSource.query.filter_by(
            incident_id=incident.id,
            source_name='MEDIA',
        ).first()
        if existing:
            skipped_count += 1
            click.echo(
                f"  [SKIP] incident_id={incident.id} – MEDIA source already exists"
            )
            continue

        existing_record = IncidentSource.query.filter_by(
            source_name='MEDIA',
            source_record_id=source_record_id,
        ).first()
        if existing_record:
            skipped_count += 1
            click.echo(
                f"  [SKIP] incident_id={incident.id} – duplicate MEDIA record id ({source_record_id})"
            )
            continue

        new_src = IncidentSource(
            incident_id=incident.id,
            source_name='MEDIA',
            source_record_id=source_record_id,
            source_url=best.url,
            is_active=True,
            confidence_level='Low',
            source_data={
                'enrichment_tier': best.tier,
                'enrichment_event_id': event_id,
                'articles': [{'url': a.url, 'domain': a.domain} for a in articles],
            },
        )
        try:
            db.session.add(new_src)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            skipped_count += 1
            click.echo(
                f"  [SKIP] incident_id={incident.id} – MEDIA source record already exists"
            )
            continue
        except Exception as exc:
            db.session.rollback()
            errors_count += 1
            click.echo(
                f"  [ERROR] incident_id={incident.id} event_id={event_id}: failed to store MEDIA source ({exc})"
            )
            continue

        if best.tier == 1:
            articles_found_t1 += 1
        elif best.tier == 2:
            articles_found_t2 += 1
        else:
            articles_found_t3 += 1

        click.echo(
            f"  [FOUND tier={best.tier}] incident_id={incident.id}"
            f" event_id={event_id} → {best.url}"
        )

    click.echo("\n--- Enrichment Summary ---")
    click.echo(f"  Total incidents checked : {total_checked}")
    click.echo(f"  Articles found (tier 1) : {articles_found_t1}")
    click.echo(f"  Articles found (tier 2) : {articles_found_t2}")
    click.echo(f"  Articles found (tier 3) : {articles_found_t3}")
    click.echo(f"  Skipped                  : {skipped_count}")
    click.echo(f"  No result                : {no_result_count}")
    click.echo(f"  Errors                   : {errors_count}")
    click.echo(f"  Queries used             : {queries_used}")
    if errors_count:
        raise click.ClickException(f"Enrichment completed with {errors_count} error(s).")
