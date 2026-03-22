import os
import sys
import logging
from app import create_app, db
from app.models import Aircraft, Incident, Request, IncidentSource, SystemTag, AircraftVariant, ReportAnalysis

app = create_app(os.getenv('FLASK_CONFIG') or os.getenv('FLASK_ENV') or 'default')

logger = logging.getLogger(__name__)


def is_truthy_env(name):
    value = os.getenv(name)
    if value is None:
        return False
    return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}

def seed_dev_data_if_empty():
    if not app.debug:
        return

    if not is_truthy_env('AUTO_SEED'):
        return

    with app.app_context():
        try:
            if Aircraft.query.count() == 0:
                logger.info("AUTO_SEED enabled and DB is empty. Seeding from data/raw/*.json...")
                scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts')
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)

                import import_data

                import_data.main()
                logger.info(f"Seed complete. Database now has {Aircraft.query.count()} aircraft records.")
            else:
                logger.info("AUTO_SEED enabled but DB is not empty. Skipping seed.")
        except Exception as e:
            logger.error(f"Failed to seed database: {e}")

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
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '5000'))
    app.run(host=host, port=port, use_reloader=not is_truthy_env('DISABLE_RELOADER'))
