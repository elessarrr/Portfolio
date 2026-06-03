from flask import Blueprint, render_template, request, flash, redirect, url_for
from sqlalchemy import or_
from app.ingestion.faa_baseline_overlap import incident_visible_on_aircraft_page
from app.models import Aircraft, Incident, IncidentSource, Request as RequestModel
from app.forms import RequestDataForm
from app import db
from thefuzz import process

bp = Blueprint('main', __name__)


def _load_sources_by_incident_id(incident_ids):
    """Batch-load active IncidentSource rows for a page of incidents (no N+1)."""
    if not incident_ids:
        return {}
    rows = (
        IncidentSource.query.filter(
            IncidentSource.incident_id.in_(incident_ids),
            or_(IncidentSource.is_active.is_(True), IncidentSource.is_active.is_(None)),
        )
        .order_by(IncidentSource.id.asc())
        .all()
    )
    lookup = {}
    for source in rows:
        lookup.setdefault(source.incident_id, []).append(source)
    return lookup


def _incidents_query(aircraft):
    return aircraft.incidents


def _visible_incidents(incidents, sources_by_incident):
    """PRD 0009: hide FAA-only rows with no outbound link."""
    return [
        inc
        for inc in incidents
        if incident_visible_on_aircraft_page(inc, sources_by_incident.get(inc.id, []))
    ]


@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/search')
def search():
    query = request.args.get('q', '')
    if len(query) < 1:
        return ''
        
    # Scalable Search: Option 1 - Basic Database ILIKE Search
    # This prevents loading all records into memory. It relies on the database 
    # to filter records where the model_name contains the search query.
    results = Aircraft.query.filter(
        Aircraft.model_name.ilike(f'%{query}%')
    ).order_by(Aircraft.model_name).limit(20).all()
    
    if not results:
        return render_template('components/search_results.html', grouped_results={})
    
    # Group results by "Series"
    grouped_results = {}
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
        
    return render_template('components/search_results.html', grouped_results=grouped_results)

@bp.route('/aircraft/<int:aircraft_id>')
def aircraft_details(aircraft_id):
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    incidents = _incidents_query(aircraft).order_by(Incident.date.desc()).all()
    sources_by_incident = _load_sources_by_incident_id([i.id for i in incidents])
    incidents = _visible_incidents(incidents, sources_by_incident)
    return render_template(
        'aircraft.html',
        aircraft=aircraft,
        incidents=incidents,
        sources_by_incident=sources_by_incident,
    )

@bp.route('/aircraft/<int:aircraft_id>/incidents')
def get_incidents(aircraft_id):
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    query = _incidents_query(aircraft)

    # Filter by type
    filter_type = request.args.get('type', 'all')
    if filter_type == 'fatal':
        query = query.filter(Incident.fatalities > 0)
    elif filter_type == 'nonfatal':
        query = query.filter(Incident.fatalities == 0)

    # Filter by date
    date_from = request.args.get('date_from')
    if date_from:
        query = query.filter(Incident.date >= date_from)

    date_to = request.args.get('date_to')
    if date_to:
        query = query.filter(Incident.date <= date_to)

    incidents = query.order_by(Incident.date.desc()).all()
    sources_by_incident = _load_sources_by_incident_id([i.id for i in incidents])
    incidents = _visible_incidents(incidents, sources_by_incident)
    return render_template(
        'components/incident_list.html',
        incidents=incidents,
        sources_by_incident=sources_by_incident,
    )

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

import logging
import threading
# from app.services.gemini import GeminiService
from app.services.deepseek import (
    SUMMARY_UNAVAILABLE_USER_MESSAGE,
    DeepSeekService,
)

logger = logging.getLogger(__name__)

def generate_summary_background(app_context, aircraft_id):
    """Background task to generate the AI summary without blocking the main thread."""
    # We need to push the app context to access the database in a new thread
    with app_context():
        aircraft = db.session.get(Aircraft, aircraft_id)
        if not aircraft:
            logger.error(f"Background task failed: Aircraft {aircraft_id} not found.")
            return

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
        if summary == SUMMARY_UNAVAILABLE_USER_MESSAGE:
            aircraft.ai_summary = SUMMARY_UNAVAILABLE_USER_MESSAGE
        else:
            aircraft.ai_summary = summary

        db.session.commit()
        logger.info(f"Background thread: Saved new summary for {aircraft.model_name}.")

@bp.route('/aircraft/<int:aircraft_id>/regenerate-summary')
def regenerate_summary(aircraft_id):
    logger.info(f"Regenerate summary requested for aircraft_id: {aircraft_id}")
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    
    # Temporarily set the summary to indicate it is generating
    aircraft.ai_summary = "Generating AI summary... Please wait."
    db.session.commit()
    
    from flask import current_app
    app_context = current_app.app_context
    
    # Start the background thread
    thread = threading.Thread(target=generate_summary_background, args=(app_context, aircraft.id))
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
    
    if aircraft.ai_summary and "Generating AI summary" not in aircraft.ai_summary:
        # Done generating, return the final summary card
        return render_template('components/summary_card.html', aircraft=aircraft)
        
    # Still generating, return the polling partial again
    return render_template('components/summary_card_polling.html', aircraft=aircraft)

@bp.app_errorhandler(404)
def not_found_error(error):
    # Suggest some random aircraft
    suggestions = Aircraft.query.order_by(db.func.random()).limit(5).all()
    return render_template('404.html', suggestions=suggestions), 404