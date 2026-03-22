import os
import logging
from app import create_app, db
from app.models import Aircraft, Incident, Request, IncidentSource, SystemTag, AircraftVariant, ReportAnalysis

app = create_app(os.getenv('FLASK_CONFIG') or os.getenv('FLASK_ENV') or 'default')

def seed_dev_data_if_empty():
    """Seed the database with minimal data if it's empty and we're in development."""
    if os.getenv('AUTO_SEED') != 'true':
        return

    with app.app_context():
        try:
            if Aircraft.query.count() == 0:
                logging.info("AUTO_SEED=true and DB is empty. Running import_data to seed DB...")
                from scripts.import_data import main as import_data_main
                # This will import data from data/raw/*.json
                import_data_main()
                logging.info(f"Seed complete. Database now has {Aircraft.query.count()} aircraft records.")
            else:
                logging.info("AUTO_SEED=true but DB is not empty. Skipping seed.")
        except Exception as e:
            logging.error(f"Failed to seed database: {e}")

# Run seed check before starting app
seed_dev_data_if_empty()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'Aircraft': Aircraft, 
        'Incident': Incident, 
        'Request': Request,
        'IncidentSource': IncidentSource,
        'SystemTag': SystemTag,
        'AircraftVariant': AircraftVariant,
        'ReportAnalysis': ReportAnalysis
    }

if __name__ == '__main__':
    app.run()
