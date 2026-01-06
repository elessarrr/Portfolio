from app import create_app, db
from app.models import Aircraft, Incident

app = create_app()
with app.app_context():
    # Update one incident to be fatal for testing
    incident = Incident.query.filter_by(aircraft_id=1).first()
    if incident:
        incident.fatalities = 5
        db.session.commit()
        print(f"Updated incident {incident.id} to have 5 fatalities")
    
    # Verify
    fatal_count = Incident.query.filter_by(aircraft_id=1).filter(Incident.fatalities > 0).count()
    print(f"Fatal incidents for ID 1: {fatal_count}")
