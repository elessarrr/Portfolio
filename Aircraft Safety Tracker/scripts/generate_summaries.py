import os
import sys
import time
import logging

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Aircraft, Incident
from app.services.gemini import GeminiService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_summaries(force=False):
    app = create_app()
    gemini = GeminiService()
    
    with app.app_context():
        aircrafts = Aircraft.query.all()
        logger.info(f"Found {len(aircrafts)} aircraft in database.")
        
        updated_count = 0
        
        for aircraft in aircrafts:
            has_incidents = db.session.query(Incident.id).filter(Incident.aircraft_id == aircraft.id).first() is not None
            if not has_incidents:
                if aircraft.ai_summary:
                    aircraft.ai_summary = None
                    db.session.commit()
                logger.info(f"Skipping {aircraft.model_name} - no incidents available.")
                continue

            if aircraft.ai_summary and not force:
                logger.info(f"Skipping {aircraft.model_name} - summary already exists.")
                continue
                
            logger.info(f"Generating summary for {aircraft.model_name}...")
            
            aircraft_data = {
                'manufacturer': aircraft.manufacturer,
                'model_name': aircraft.model_name,
                'years_in_service': aircraft.years_in_service,
                'total_incidents': aircraft.total_incidents,
                'fatal_incidents': aircraft.fatal_incidents,
                'total_fatalities': aircraft.total_fatalities
            }
            
            summary = gemini.generate_aircraft_summary(aircraft_data)
            
            if "AI service unavailable" in summary or "Failed" in summary:
                logger.error(f"Failed to generate summary for {aircraft.model_name}: {summary}")
                if "AI service unavailable" in summary:
                     # Stop if service is unavailable (e.g. no key)
                     break
            else:
                aircraft.ai_summary = summary
                db.session.commit()
                updated_count += 1
                logger.info(f"Updated summary for {aircraft.model_name}.")
                
                # Sleep to respect rate limits (even with retry logic in service)
                time.sleep(2)
                
        logger.info(f"Completed. Updated {updated_count} aircraft summaries.")

if __name__ == '__main__':
    force_update = '--force' in sys.argv
    generate_summaries(force=force_update)
