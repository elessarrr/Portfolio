from app import create_app, db
from app.models import Aircraft, Incident

app = create_app()
with app.app_context():
    for a in Aircraft.query.all():
        stats = db.session.query(
            db.func.count(Incident.id),
            db.func.sum(Incident.fatalities),
            db.func.sum(db.case((Incident.fatalities > 0, 1), else_=0))
        ).filter_by(aircraft_id=a.id).first()
        
        a.total_incidents = stats[0] or 0
        a.total_fatalities = stats[1] or 0
        a.fatal_incidents = stats[2] or 0
    db.session.commit()
    print("Stats updated.")
