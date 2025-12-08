from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import Aircraft, Incident, Request as RequestModel
from app.forms import RequestDataForm
from app import db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/search')
def search():
    query = request.args.get('q', '')
    if len(query) < 1:
        return ''
        
    results = Aircraft.query.filter(Aircraft.model_name.ilike(f'%{query}%')).limit(10).all()
    return render_template('components/search_results.html', results=results)

@bp.route('/aircraft/<int:aircraft_id>')
def aircraft_details(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    incidents = aircraft.incidents.order_by(Incident.date.desc()).all()
    return render_template('aircraft.html', aircraft=aircraft, incidents=incidents)

@bp.route('/aircraft/<int:aircraft_id>/incidents')
def get_incidents(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    query = aircraft.incidents
    
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
    return render_template('components/incident_list.html', incidents=incidents)

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
# from app.services.gemini import GeminiService
from app.services.deepseek import DeepSeekService

logger = logging.getLogger(__name__)

@bp.route('/aircraft/<int:aircraft_id>/regenerate-summary')
def regenerate_summary(aircraft_id):
    logger.info(f"Regenerate summary requested for aircraft_id: {aircraft_id}")
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    
    # gemini = GeminiService()
    ai_service = DeepSeekService()
    
    aircraft_data = {
        'manufacturer': aircraft.manufacturer,
        'model_name': aircraft.model_name,
        'years_in_service': aircraft.years_in_service,
        'total_incidents': aircraft.total_incidents,
        'fatal_incidents': aircraft.fatal_incidents,
        'total_fatalities': aircraft.total_fatalities
    }
    
    logger.info(f"Calling AI Service for {aircraft.model_name}...")
    summary = ai_service.generate_aircraft_summary(aircraft_data)
    logger.info(f"AI response length: {len(summary)}")
    logger.debug(f"AI response content: {summary[:100]}...")
    
    if "AI summary unavailable" not in summary and "Error" not in summary:
        aircraft.ai_summary = summary
        db.session.commit()
        if not request.headers.get('HX-Request'):
            flash('Summary regenerated successfully.', 'success')
    else:
        if not request.headers.get('HX-Request'):
            flash(f'Failed to regenerate summary: {summary}', 'error')
            
    if request.headers.get('HX-Request'):
        return render_template('components/summary_card.html', aircraft=aircraft)
        
    return redirect(url_for('main.aircraft_details', aircraft_id=aircraft.id))

@bp.app_errorhandler(404)
def not_found_error(error):
    # Suggest some random aircraft
    suggestions = Aircraft.query.order_by(db.func.random()).limit(5).all()
    return render_template('404.html', suggestions=suggestions), 404