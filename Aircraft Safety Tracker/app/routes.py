import csv
import io
import logging
import threading
from datetime import datetime

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response
from sqlalchemy import or_

from app.models import Aircraft, AircraftVariant, Incident, IncidentSource, SystemTag, Request as RequestModel
from app.forms import RequestDataForm
from app import db
from thefuzz import process

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

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
    ).order_by(Aircraft.model_name).limit(20).all()
    
    if not results:
        return render_template('components/search_results.html', grouped_results={})
    
    grouped_results = {}
    series_name_by_aircraft_id = {}
    for aircraft in results:
        # Determine series name with improved heuristic
        # Step 1: Remove manufacturer from start of model_name to get the "model part"
        model_part = aircraft.model_name
        if aircraft.manufacturer and model_part.lower().startswith(aircraft.manufacturer.lower()):
            model_part = model_part[len(aircraft.manufacturer):].strip()
        
        # Step 2: Get the first word of the model part
        words = model_part.split()
        if not words:
            series_name = aircraft.model_name # Fallback
        else:
            first_word = words[0]
            
            # Step 3: Check for hyphens to split variants (e.g. 707-100 -> 707)
            if '-' in first_word:
                # Heuristic: 
                # If prefix > 2 chars (e.g. 707-100, A320-200), split at first hyphen.
                # If prefix <= 2 chars (e.g. DC-10-30), try splitting at second hyphen if exists.
                parts = first_word.split('-')
                prefix = parts[0]
                
                if len(prefix) > 2:
                    base_model = prefix
                elif len(parts) >= 3:
                    # Case like DC-10-30 -> DC-10
                    base_model = f"{parts[0]}-{parts[1]}"
                else:
                    # Case like DC-9 -> DC-9 (keep as is)
                    base_model = first_word
            else:
                base_model = first_word
            
            series_name = f"{aircraft.manufacturer} {base_model}"
        
        if series_name not in grouped_results:
            grouped_results[series_name] = []
        grouped_results[series_name].append(aircraft)
        series_name_by_aircraft_id[aircraft.id] = series_name

    variants_by_series = {}
    if results:
        aircraft_ids = [aircraft.id for aircraft in results]
        variants = AircraftVariant.query.filter(AircraftVariant.aircraft_id.in_(aircraft_ids)).order_by(
            AircraftVariant.variant_name
        ).all()
        seen = set()
        for variant in variants:
            key = (variant.aircraft_id, variant.variant_name)
            if key in seen:
                continue
            seen.add(key)
            series_name = series_name_by_aircraft_id.get(variant.aircraft_id)
            if not series_name:
                continue
            variants_by_series.setdefault(series_name, []).append(variant)
        
    return render_template('components/search_results.html', grouped_results=grouped_results, variants_by_series=variants_by_series)

@bp.route('/incidents')
def global_incidents():
    # Base query for all incidents, joining Aircraft for model details
    query = db.session.query(Incident).join(Aircraft)
    
    query = apply_incident_filters(query, request.args)
    
    # Pre-compute chart data from the filtered query
    # Need to execute without limit/offset to get the true aggregate stats
    all_filtered = query.all()
    
    chart_data = {
        'timeline': {},
        'severity': {'fatal': 0, 'nonfatal': 0},
        'manufacturers': {}
    }
    
    for inc in all_filtered:
        if not inc.date:
            continue
            
        year = str(inc.date.year)
        
        # Timeline
        chart_data['timeline'][year] = chart_data['timeline'].get(year, 0) + 1
        
        # Severity
        if inc.fatalities > 0:
            chart_data['severity']['fatal'] += 1
        else:
            chart_data['severity']['nonfatal'] += 1
            
        # Manufacturers
        mfg = inc.aircraft.manufacturer if inc.aircraft else 'Unknown'
        chart_data['manufacturers'][mfg] = chart_data['manufacturers'].get(mfg, 0) + 1
    
    # Sort timeline by year
    sorted_timeline = dict(sorted(chart_data['timeline'].items()))
    chart_data['timeline'] = sorted_timeline

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
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    can_generate_summary = aircraft_has_incidents(aircraft.id)
    
    # Base query for this specific aircraft
    query = aircraft.incidents
    
    # By default, enforce the 1985-onward rule unless overridden
    # The default date_from filter handles this if we pass it explicitly, 
    # but we need to ensure the base view defaults to post-1985 for consistency
    date_from_param = request.args.get('date_from')
    if not date_from_param:
        query = query.filter(Incident.date >= datetime(1985, 1, 1).date())
        
    query = apply_incident_filters(query, request.args)
    incidents = query.order_by(Incident.date.desc()).distinct().all()
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
    
    # Exclude the parent model name from being treated as a separate sub-variant
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

@bp.route('/aircraft/<int:aircraft_id>/incidents')
def get_incidents(aircraft_id):
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    query = aircraft.incidents
    
    date_from_param = request.args.get('date_from')
    if not date_from_param:
        query = query.filter(Incident.date >= datetime(1985, 1, 1).date())
        
    query = apply_incident_filters(query, request.args)
    incidents = query.order_by(Incident.date.desc()).distinct().all()
    return render_template('components/incident_list.html', incidents=incidents, aircraft=aircraft)


@bp.route('/aircraft/<int:aircraft_id>/incidents/export.csv')
def export_incidents_csv(aircraft_id):
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    query = aircraft.incidents
    
    date_from_param = request.args.get('date_from')
    if not date_from_param:
        query = query.filter(Incident.date >= datetime(1985, 1, 1).date())
        
    query = apply_incident_filters(query, request.args)
    incidents = query.order_by(Incident.date.desc()).distinct().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Aircraft', 'Operator', 'System', 'Description', 'Source'])

    for incident in incidents:
        systems = ', '.join(sorted({tag.system_name for tag in incident.system_tags if tag.system_name}))
        sources = ', '.join(sorted({source.source_name for source in incident.sources if source.source_name}))
        writer.writerow([
            incident.date.isoformat() if incident.date else '',
            aircraft.model_name,
            incident.operator or '',
            systems,
            incident.description or '',
            sources
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


def aircraft_has_incidents(aircraft_id):
    return db.session.query(Incident.id).filter(Incident.aircraft_id == aircraft_id).first() is not None

def generate_summary_background(app_context, aircraft_id):
    """Background task to generate the AI summary without blocking the main thread."""
    # We need to push the app context to access the database in a new thread
    with app_context():
        aircraft = db.session.get(Aircraft, aircraft_id)
        if not aircraft:
            logger.error(f"Background task failed: Aircraft {aircraft_id} not found.")
            return
        if not aircraft_has_incidents(aircraft.id):
            aircraft.ai_summary = None
            db.session.commit()
            logger.info(f"Background thread: Skipped summary for {aircraft.model_name} (no incidents).")
            return

        try:
            ai_service = DeepSeekService()
            aircraft_data = {
                'manufacturer': aircraft.manufacturer,
                'model_name': aircraft.model_name,
                'years_in_service': aircraft.years_in_service,
                'total_incidents': aircraft.total_incidents,
                'fatal_incidents': aircraft.fatal_incidents,
                'total_fatalities': aircraft.total_fatalities
            }

            logger.info(f"Background thread: Calling AI Service for {aircraft.model_name}...")
            summary = ai_service.generate_aircraft_summary(aircraft_data)

            if "AI summary unavailable" not in summary and "Error" not in summary:
                aircraft.ai_summary = summary
            else:
                aircraft.ai_summary = f"Failed to generate summary: {summary}"
        except Exception as exc:
            logger.exception("Background thread: Summary generation failed")
            aircraft.ai_summary = f"Failed to generate summary: {type(exc).__name__}"

        db.session.commit()
        logger.info(f"Background thread: Saved new summary for {aircraft.model_name}.")

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
    
    # Temporarily set the summary to indicate it is generating
    aircraft.ai_summary = "Generating AI summary... Please wait."
    db.session.commit()
    
    from flask import current_app
    app_context = current_app.app_context
    
    # Start the background thread
    thread = threading.Thread(target=generate_summary_background, args=(app_context, aircraft.id), daemon=True)
    thread.start()
    
    # If it's an HTMX request, return a partial that polls for the result
    if request.headers.get('HX-Request'):
        return render_template('components/summary_card_polling.html', aircraft=aircraft)
        
    # Standard fallback
    flash('Summary generation started. Refresh the page in a few seconds.', 'info')
    return redirect(url_for('main.aircraft_details', aircraft_id=aircraft.id))

@bp.route('/aircraft/<int:aircraft_id>/summary-status')
def check_summary_status(aircraft_id):
    """Endpoint for HTMX to poll while the summary is generating."""
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    can_generate_summary = aircraft_has_incidents(aircraft.id)
    if not can_generate_summary:
        return render_template('components/summary_card.html', aircraft=aircraft, can_generate_summary=False)
    
    if aircraft.ai_summary and "Generating AI summary" not in aircraft.ai_summary:
        # Done generating, return the final summary card
        return render_template('components/summary_card.html', aircraft=aircraft, can_generate_summary=True)
        
    # Still generating, return the polling partial again
    return render_template('components/summary_card_polling.html', aircraft=aircraft)


@bp.route('/api/analyze-report', methods=['POST'])
def analyze_report():
    payload = request.get_json(silent=True) or {}
    report_text = payload.get('report_text')
    report_url = payload.get('report_url')
    model = payload.get('model')

    if not report_text and not report_url:
        return jsonify({
            'error': 'Missing input',
            'details': 'Provide report_text or report_url in the request body.'
        }), 400

    analyzer = ReportAnalyzerService(model_name=model)
    # Prefer remote_addr, fallback to X-Forwarded-For if needed (though spoofable without ProxyFix)
    client_id = request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown').split(',')[0].strip()
    result, status_code = analyzer.analyze_report(
        client_id=client_id,
        report_text=report_text,
        report_url=report_url
    )
    return jsonify(result), status_code

@bp.app_errorhandler(404)
def not_found_error(error):
    # Suggest some random aircraft
    suggestions = Aircraft.query.order_by(db.func.random()).limit(5).all()
    return render_template('404.html', suggestions=suggestions), 404
