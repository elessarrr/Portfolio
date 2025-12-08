from app import db
from datetime import datetime

class Aircraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    manufacturer = db.Column(db.String(64), index=True)
    model_name = db.Column(db.String(64), index=True, unique=True)
    icao_code = db.Column(db.String(10), index=True)
    years_in_service = db.Column(db.Integer)
    total_incidents = db.Column(db.Integer, default=0)
    fatal_incidents = db.Column(db.Integer, default=0)
    total_fatalities = db.Column(db.Integer, default=0)
    ai_summary = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Aircraft {self.model_name}>'

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'))
    date = db.Column(db.Date)
    operator = db.Column(db.String(128))
    location = db.Column(db.String(128))
    fatalities = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    asn_url = db.Column(db.String(256))
    incident_type = db.Column(db.String(64))  # e.g., "Accident", "Hijacking"

    aircraft = db.relationship('Aircraft', backref=db.backref('incidents', lazy='dynamic'))

    def __repr__(self):
        return f'<Incident {self.date} - {self.operator}>'
