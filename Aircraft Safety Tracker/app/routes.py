import csv
import io
import logging
import re
from datetime import datetime

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response, current_app
from sqlalchemy import or_
from werkzeug.exceptions import HTTPException

from app.models import Aircraft, AircraftVariant, Incident, IncidentSource, SummaryGenerationJob, SystemTag, Request as RequestModel
from app.forms import RequestDataForm
from app import db
from thefuzz import process

bp = Blueprint('main', __name__)

SOURCE_PRIORITY_ORDER = {
    'NTSB': 1,
    'FAA_AIDS': 2,
    'FAA_SDR': 3,
    'ASN': 4,
}

MODEL_SORT_SPLIT_PATTERN = re.compile(r"\s*-\s*")


def _extract_model_part(model_name, manufacturer):
    """Return model segment without manufacturer prefix for stable sorting."""
    model_part = (model_name or '').strip()
    if manufacturer and model_part.lower().startswith(manufacturer.lower()):
        model_part = model_part[len(manufacturer):].strip()
    return model_part


def _aircraft_model_sort_key(aircraft):
    """
    Sort by manufacturer + base model, then prefer base model rows before variants.
    Examples:
      Boeing 747    -> (BOEING, 747, 0, 747)
      Boeing 747-400 -> (BOEING, 747, 1, 747-400)
    """
    manufacturer = (aircraft.manufacturer or '').strip().upper()
    model_part = _extract_model_part(aircraft.model_name, aircraft.manufacturer).upper()
    base_model = MODEL_SORT_SPLIT_PATTERN.split(model_part, maxsplit=1)[0]
    has_variant_suffix = 1 if model_part != base_model else 0
    return manufacturer, base_model, has_variant_suffix, model_part

@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/faq')
def faq():
    return render_template('faq.html')

@bp.route('/search')
def search():
    query = request.args.get('q', '')
    if len(query) < 1:
        return ''
        
    # Check if database is completely empty
    total_aircraft = Aircraft.query.count()
    if total_aircraft == 0:
        return render_template('components/search_results.html', grouped_results=None, empty_db=True)
        
    # Scalable Search: Option 1 - Basic Database ILIKE Search
    # This prevents loading all records into memory. It relies on the database 
    # to filter records where the model_name contains the search query.
    like_query = f'%{query}%'
    variant_aircraft_ids = db.session.query(AircraftVariant.aircraft_id).filter(
        AircraftVariant.variant_name.ilike(like_query)
    )

    results = Aircraft.query.filter(
        or_(
            Aircraft.model_name.ilike(like_query),
            Aircraft.id.in_(variant_aircraft_ids),
        )
    ).all()
    results = sorted(results, key=_aircraft_model_sort_key)

    if not results:
        return render_template('components/search_results.html', grouped_results={})

    # Build lookup for Aircraft id -> series_name
    aircraft_to_series = {}
    for aircraft in results:
        model_part = aircraft.model_name
        if aircraft.manufacturer and model_part.lower().startswith(aircraft.manufacturer.lower()):
            model_part = model_part[len(aircraft.manufacturer):].strip()

        words = model_part.split()
        if not words:
            series_name = aircraft.model_name
        else:
            first_word = words[0]
            if '-' in first_word:
                parts = first_word.split('-')
                prefix = parts[0]
                if len(prefix) > 2:
                    base_model = prefix
                elif len(parts) >= 3:
                    base_model = f"{parts[0]}-{parts[1]}"
                else:
                    base_model = first_word
            else:
                base_model = first_word
            series_name = f"{aircraft.manufacturer} {base_model}"

        aircraft_to_series[aircraft.id] = series_name

    # Fetch variants and group by series_name for direct display
    aircraft_ids = [aircraft.id for aircraft in results]
    variants = AircraftVariant.query.filter(
        AircraftVariant.aircraft_id.in_(aircraft_ids)
    ).order_by(AircraftVariant.variant_name).all()

    # Group variants directly by series_name (AircraftVariant displayed as primary entries)
    grouped_results = {}
    for variant in variants:
        series_name = aircraft_to_series.get(variant.aircraft_id)
        if not series_name:
            continue
        if series_name not in grouped_results:
            grouped_results[series_name] = []
        grouped_results[series_name].append(variant)

    # Add Aircraft directly when they do not have variant rows of their own.
    # This keeps variant-less Aircraft visible even when other Aircraft in the
    # same series do have variants.
    aircraft_ids_with_variants = {variant.aircraft_id for variant in variants}
    for aircraft in results:
        if aircraft.id in aircraft_ids_with_variants:
            continue

        series_name = aircraft_to_series.get(aircraft.id)
        if not series_name:
            series_name = aircraft.model_name
        if series_name not in grouped_results:
            grouped_results[series_name] = []
        grouped_results[series_name].append(aircraft)

    variants_by_series = {}  # Not used in new direct display mode, kept for compatibility

    return render_template('components/search_results.html', grouped_results=grouped_results, variants_by_series=variants_by_series)


@bp.route('/api/search/autocomplete')
def search_autocomplete():
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({'results': []})

    # Keep payload intentionally minimal for frontend autocomplete rendering.
    like_query = f'%{query}%'
    autocomplete_matches = Aircraft.query.filter(
        or_(
            Aircraft.model_name.ilike(like_query),
            Aircraft.manufacturer.ilike(like_query),
        )
    ).limit(100).all()
    autocomplete_matches = sorted(autocomplete_matches, key=_aircraft_model_sort_key)[:5]

    results = [{
        'id': aircraft.id,
        'make_model': aircraft.model_name,
        'full_name': aircraft.model_name,
    } for aircraft in autocomplete_matches]

    return jsonify({'results': results})

@bp.route('/incidents')
def global_incidents():
    # Base query for all incidents, joining Aircraft for model details
    query = db.session.query(Incident).join(Aircraft)
    
    query = apply_incident_filters(query, request.args)
    
    timeline_rows = query.with_entities(
        db.extract('year', Incident.date).label('year'),
        db.func.count(db.distinct(Incident.id)).label('count')
    ).filter(
        Incident.date.isnot(None)
    ).group_by(
        'year'
    ).order_by(
        'year'
    ).all()

    fatal_count = query.filter(Incident.fatalities > 0).with_entities(
        db.func.count(db.distinct(Incident.id))
    ).scalar() or 0
    nonfatal_count = query.filter(Incident.fatalities == 0).with_entities(
        db.func.count(db.distinct(Incident.id))
    ).scalar() or 0

    manufacturer_rows = query.with_entities(
        db.func.coalesce(Aircraft.manufacturer, 'Unknown').label('manufacturer'),
        db.func.count(db.distinct(Incident.id)).label('count')
    ).group_by(
        'manufacturer'
    ).all()

    chart_data = {
        'timeline': {},
        'severity': {'fatal': fatal_count, 'nonfatal': nonfatal_count},
        'manufacturers': {}
    }

    for year, count in timeline_rows:
        chart_data['timeline'][str(int(year))] = count

    for manufacturer, count in manufacturer_rows:
        chart_data['manufacturers'][manufacturer] = count

    # Order by date descending for the list view
    incidents = query.order_by(Incident.date.desc()).distinct().limit(50).all()
    
    if request.headers.get('HX-Request') and not request.headers.get('HX-History-Restore-Request'):
        html = render_template('components/global_incident_list.html', incidents=incidents, page=1)
        charts_html = render_template('components/global_charts.html', chart_data=chart_data)
        return html + charts_html
    
    return render_template('incidents_database.html', incidents=incidents, page=1, chart_data=chart_data)

@bp.route('/incidents/page')
def global_incidents_page():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    query = db.session.query(Incident).join(Aircraft)
    query = apply_incident_filters(query, request.args)
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Order by date descending, apply limit and offset
    incidents = query.order_by(Incident.date.desc()).distinct().offset(offset).limit(per_page).all()
    
    return render_template('components/global_incident_list.html', incidents=incidents, page=page)

@bp.route('/aircraft/<int:aircraft_id>')
def aircraft_details(aircraft_id):
    try:
        aircraft = db.get_or_404(Aircraft, aircraft_id)
        total_incidents = aircraft.total_incidents or 0
        can_generate_summary = total_incidents > 0 and aircraft_has_incidents(aircraft.id)

        query = aircraft.incidents

        query = apply_incident_filters(query, request.args)
        incidents = apply_source_priority_order(query).distinct().limit(50).all()
        system_options = [value[0] for value in db.session.query(SystemTag.system_name)
            .join(Incident, Incident.id == SystemTag.incident_id)
            .filter(Incident.aircraft_id == aircraft.id)
            .distinct()
            .order_by(SystemTag.system_name)
            .all()]
        source_options = [value[0] for value in db.session.query(IncidentSource.source_name)
            .join(Incident, Incident.id == IncidentSource.incident_id)
            .filter(Incident.aircraft_id == aircraft.id)
            .distinct()
            .order_by(IncidentSource.source_name)
            .all()]

        variant_options = sorted({
            variant.variant_name
            for variant in aircraft.variants.all()
            if variant.variant_name and variant.variant_name != aircraft.model_name
        })

        selected_filters = {
            'type': request.args.get('type', 'all'),
            'date_from': request.args.get('date_from', ''),
            'date_to': request.args.get('date_to', ''),
            'systems': request.args.getlist('system'),
            'sources': request.args.getlist('source'),
            'variants': request.args.getlist('variant')
        }
        return render_template(
            'aircraft.html',
            aircraft=aircraft,
            incidents=incidents,
            system_options=system_options,
            source_options=source_options,
            variant_options=variant_options,
            selected_filters=selected_filters,
            can_generate_summary=can_generate_summary
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error rendering aircraft_details for aircraft_id=%s", aircraft_id)
        return render_template('500.html'), 500

@bp.route('/aircraft/<int:aircraft_id>/incidents')
def get_incidents(aircraft_id):
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    query = aircraft.incidents
        
    query = apply_incident_filters(query, request.args)
    incidents = apply_source_priority_order(query).distinct().limit(50).all()
    return render_template('components/incident_list.html', incidents=incidents, aircraft=aircraft)


@bp.route('/aircraft/<int:aircraft_id>/incidents/export.csv')
def export_incidents_csv(aircraft_id):
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    query = aircraft.incidents
        
    query = apply_incident_filters(query, request.args)
    
    incidents = apply_source_priority_order(query).distinct().all()
    incident_ids = [incident.id for incident in incidents]

    systems_by_incident = {}
    sources_by_incident = {}
    if incident_ids:
        system_rows = db.session.query(SystemTag.incident_id, SystemTag.system_name).filter(
            SystemTag.incident_id.in_(incident_ids)
        ).all()
        source_rows = db.session.query(IncidentSource.incident_id, IncidentSource.source_name).filter(
            IncidentSource.incident_id.in_(incident_ids)
        ).all()

        for incident_id, system_name in system_rows:
            if not system_name:
                continue
            systems_by_incident.setdefault(incident_id, set()).add(system_name)
        for incident_id, source_name in source_rows:
            if not source_name:
                continue
            sources_by_incident.setdefault(incident_id, set()).add(source_name)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Aircraft', 'Operator', 'System', 'Description', 'Source'])

    def sanitize_csv_field(field):
        """Prevent CSV Injection (Excel Macro Injection) by prepending a quote to suspicious characters."""
        if not field:
            return ''
        field_str = str(field)
        if field_str and field_str[0] in ('=', '+', '-', '@'):
            return f"'{field_str}"
        return field_str

    for incident in incidents:
        systems = ', '.join(sorted(systems_by_incident.get(incident.id, set())))
        sources = ', '.join(sorted(sources_by_incident.get(incident.id, set())))
        writer.writerow([
            incident.date.isoformat() if incident.date else '',
            sanitize_csv_field(aircraft.model_name),
            sanitize_csv_field(incident.operator),
            sanitize_csv_field(systems),
            sanitize_csv_field(incident.description),
            sanitize_csv_field(sources)
        ])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=incident_export_{aircraft.id}.csv'
    return response

@bp.route('/feedback/request', methods=['GET', 'POST'])
def request_data():
    form = RequestDataForm()
    if form.validate_on_submit():
        new_request = RequestModel(
            aircraft_model=form.aircraft_model.data,
            user_email=form.email.data
        )
        db.session.add(new_request)
        db.session.commit()
        flash('Thank you! Your request has been recorded.', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('request_data.html', form=form)


from app.services.deepseek import DeepSeekService
from app.services.gemini import GeminiService
from app.services.report_analyzer import ReportAnalyzerService

logger = logging.getLogger(__name__)


def parse_date_value(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def apply_incident_filters(query, params):
    filter_type = params.get('type', 'all')
    if filter_type == 'fatal':
        query = query.filter(Incident.fatalities > 0)
    elif filter_type == 'nonfatal':
        query = query.filter(Incident.fatalities == 0)

    date_from = parse_date_value(params.get('date_from'))
    if date_from:
        query = query.filter(Incident.date >= date_from)

    date_to = parse_date_value(params.get('date_to'))
    if date_to:
        query = query.filter(Incident.date <= date_to)

    systems = params.getlist('system')
    if systems:
        query = query.join(Incident.system_tags).filter(SystemTag.system_name.in_(systems))

    sources = params.getlist('source')
    if sources:
        query = query.join(Incident.sources).filter(IncidentSource.source_name.in_(sources))

    variants = params.getlist('variant')
    if variants:
        query = query.filter(Incident.variant_name.in_(variants))

    manufacturers = params.getlist('manufacturer')
    if manufacturers:
        query = query.filter(Incident.aircraft.has(Aircraft.manufacturer.in_(manufacturers)))

    models = params.getlist('model')
    if models:
        query = query.filter(Incident.aircraft.has(Aircraft.model_name.in_(models)))

    location = params.get('location')
    if location:
        query = query.filter(Incident.location.ilike(f'%{location}%'))

    return query


def apply_source_priority_order(query):
    """Order incidents by date and deterministic source priority."""
    source_priority_case = db.case(
        (IncidentSource.source_name == 'NTSB', SOURCE_PRIORITY_ORDER['NTSB']),
        (IncidentSource.source_name == 'FAA_AIDS', SOURCE_PRIORITY_ORDER['FAA_AIDS']),
        (IncidentSource.source_name == 'FAA_SDR', SOURCE_PRIORITY_ORDER['FAA_SDR']),
        (IncidentSource.source_name == 'ASN', SOURCE_PRIORITY_ORDER['ASN']),
        else_=99,
    )
    priority_subquery = db.session.query(
        IncidentSource.incident_id.label('incident_id'),
        db.func.min(source_priority_case).label('source_priority')
    ).group_by(
        IncidentSource.incident_id
    ).subquery()

    return query.outerjoin(
        priority_subquery, Incident.id == priority_subquery.c.incident_id
    ).order_by(
        Incident.date.desc(),
        db.func.coalesce(priority_subquery.c.source_priority, 99).asc(),
        Incident.id.desc()
    )


def aircraft_has_incidents(aircraft_id):
    return db.session.query(Incident.id).filter(Incident.aircraft_id == aircraft_id).first() is not None

def enqueue_summary_job(aircraft_id):
    active_job = SummaryGenerationJob.query.filter(
        SummaryGenerationJob.aircraft_id == aircraft_id,
        SummaryGenerationJob.status.in_(('pending', 'processing'))
    ).first()
    if active_job:
        return active_job
    job = SummaryGenerationJob(aircraft_id=aircraft_id, status='pending')
    db.session.add(job)
    db.session.commit()
    return job


def process_pending_summary_job(aircraft_id):
    pending_job = SummaryGenerationJob.query.filter_by(
        aircraft_id=aircraft_id,
        status='pending'
    ).order_by(SummaryGenerationJob.created_at.asc()).first()
    if not pending_job:
        return

    claimed = SummaryGenerationJob.query.filter_by(id=pending_job.id, status='pending').update({
        'status': 'processing',
        'started_at': datetime.utcnow(),
        'attempts': pending_job.attempts + 1
    })
    db.session.commit()
    if not claimed:
        return

    job = db.session.get(SummaryGenerationJob, pending_job.id)
    aircraft = db.session.get(Aircraft, aircraft_id)
    if not aircraft:
        job.status = 'failed'
        job.last_error = f'Aircraft {aircraft_id} not found'
        job.completed_at = datetime.utcnow()
        db.session.commit()
        return

    if not aircraft_has_incidents(aircraft.id):
        aircraft.ai_summary = None
        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.session.commit()
        return

    aircraft_data = {
        'manufacturer': aircraft.manufacturer,
        'model_name': aircraft.model_name,
        'years_in_service': aircraft.years_in_service,
        'total_incidents': aircraft.total_incidents,
        'fatal_incidents': aircraft.fatal_incidents,
        'total_fatalities': aircraft.total_fatalities
    }
    try:
        summary = None
        generation_errors = []
        service_chain = (
            ('DeepSeekService', DeepSeekService),
            ('GeminiService', GeminiService),
        )
        for service_name, service_cls in service_chain:
            try:
                ai_service = service_cls()
                candidate_summary = ai_service.generate_aircraft_summary(aircraft_data)
            except Exception as service_exc:
                logger.exception("%s raised during summary generation", service_name)
                generation_errors.append(f'{service_name}:{type(service_exc).__name__}')
                continue

            if not candidate_summary:
                generation_errors.append(f'{service_name}:empty_response')
                continue
            if "AI summary unavailable" in candidate_summary or "Error generating summary" in candidate_summary:
                generation_errors.append(candidate_summary)
                continue
            summary = candidate_summary
            break

        if summary:
            aircraft.ai_summary = summary
            job.status = 'completed'
            job.last_error = None
        else:
            error_detail = '; '.join(generation_errors) or 'No summary generated'
            aircraft.ai_summary = f"Failed to generate summary: {error_detail}"
            job.status = 'failed'
            job.last_error = error_detail
    except Exception as exc:
        logger.exception("Summary job failed")
        aircraft.ai_summary = f"Failed to generate summary: {type(exc).__name__}"
        job.status = 'failed'
        job.last_error = type(exc).__name__

    job.completed_at = datetime.utcnow()
    db.session.commit()


def get_client_identifier():
    if current_app.config.get('TRUST_X_FORWARDED_FOR'):
        forwarded_for = request.headers.get('X-Forwarded-For', '')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'

@bp.route('/aircraft/<int:aircraft_id>/regenerate-summary')
def regenerate_summary(aircraft_id):
    logger.info(f"Regenerate summary requested for aircraft_id: {aircraft_id}")
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    can_generate_summary = aircraft_has_incidents(aircraft.id)

    if not can_generate_summary:
        aircraft.ai_summary = None
        db.session.commit()
        if request.headers.get('HX-Request'):
            return render_template('components/summary_card.html', aircraft=aircraft, can_generate_summary=False)
        flash('Summary not generated: no incidents available for this aircraft.', 'warning')
        return redirect(url_for('main.aircraft_details', aircraft_id=aircraft.id))
    
    aircraft.ai_summary = "Generating AI summary... Please wait."
    db.session.commit()
    enqueue_summary_job(aircraft.id)
    
    # If it's an HTMX request, return a partial that polls for the result
    if request.headers.get('HX-Request'):
        return render_template('components/summary_card_polling.html', aircraft=aircraft)
        
    # Standard fallback
    flash('Summary generation started. Refresh the page in a few seconds.', 'info')
    return redirect(url_for('main.aircraft_details', aircraft_id=aircraft.id))

@bp.route('/aircraft/<int:aircraft_id>/summary-status')
def check_summary_status(aircraft_id):
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    can_generate_summary = aircraft_has_incidents(aircraft.id)
    if not can_generate_summary:
        return render_template('components/summary_card.html', aircraft=aircraft, can_generate_summary=False)

    process_pending_summary_job(aircraft.id)
    db.session.refresh(aircraft)

    latest_job = SummaryGenerationJob.query.filter_by(aircraft_id=aircraft.id).order_by(
        SummaryGenerationJob.created_at.desc()
    ).first()
    if latest_job and latest_job.status == 'failed':
        if not aircraft.ai_summary or "Generating AI summary" in aircraft.ai_summary:
            fallback_error = latest_job.last_error or "Failed to generate summary. Please try again later."
            aircraft.ai_summary = f"Failed to generate summary: {fallback_error}"
            db.session.commit()
            db.session.refresh(aircraft)
        return render_template('components/summary_card.html', aircraft=aircraft, can_generate_summary=True)

    if aircraft.ai_summary and "Generating AI summary" not in aircraft.ai_summary:
        return render_template('components/summary_card.html', aircraft=aircraft, can_generate_summary=True)

    return render_template('components/summary_card_polling.html', aircraft=aircraft)


@bp.route('/api/analyze-report', methods=['POST'])
def analyze_report():
    max_content_length = current_app.config.get('MAX_CONTENT_LENGTH')
    if max_content_length and request.content_length and request.content_length > max_content_length:
        return jsonify({
            'error': 'Payload too large',
            'details': f'Request body exceeds maximum size of {max_content_length} bytes.'
        }), 413

    payload = request.get_json(silent=True) or {}
    report_text = payload.get('report_text')
    report_url = payload.get('report_url')
    model = payload.get('model')

    max_report_chars = int(current_app.config.get('REPORT_ANALYZER_MAX_REPORT_TEXT_CHARS') or 50000)
    if report_text and len(report_text) > max_report_chars:
        return jsonify({
            'error': 'Payload too large',
            'details': f'report_text exceeds maximum length of {max_report_chars} characters.'
        }), 413

    if not report_text and not report_url:
        return jsonify({
            'error': 'Missing input',
            'details': 'Provide report_text or report_url in the request body.'
        }), 400

    analyzer = ReportAnalyzerService(model_name=model)
    client_id = get_client_identifier()
    result, status_code = analyzer.analyze_report(
        client_id=client_id,
        report_text=report_text,
        report_url=report_url
    )
    return jsonify(result), status_code


@bp.route('/api/data-source-status')
def data_source_status():
    """
    Per PRD-0016 FR-15: Return real-time availability for all configured data sources.
    Each source's status is derived from the ImportState table (last_attempted_at,
    last_successful_at, last_status, last_error).
    """
    from app.models import ImportState

    sources = ImportState.query.order_by(ImportState.source_name).all()
    result = []
    for s in sources:
        result.append({
            'source_name': s.source_name,
            'last_successful_at': s.last_successful_at.isoformat() if s.last_successful_at else None,
            'last_attempted_at': s.last_attempted_at.isoformat() if s.last_attempted_at else None,
            'last_status': s.last_status,
            'last_error': s.last_error,
        })
    return jsonify(result)


@bp.app_errorhandler(404)
def not_found_error(error):
    # Suggest some random aircraft
    suggestions = Aircraft.query.order_by(db.func.random()).limit(5).all()
    return render_template('404.html', suggestions=suggestions), 404
