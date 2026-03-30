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

    # Relationships
    variants = db.relationship('AircraftVariant', backref='aircraft', lazy='dynamic')
    incidents = db.relationship('Incident', backref='aircraft', lazy='dynamic')

    def __repr__(self):
        return f'<Aircraft {self.model_name}>'

class AircraftVariant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'), nullable=False, index=True)
    variant_name = db.Column(db.String(64), index=True)  # e.g., '737-800', 'A320neo'
    years_in_service = db.Column(db.String(64))
    total_incidents = db.Column(db.Integer, default=0)
    fatal_incidents = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint('aircraft_id', 'variant_name', name='uq_aircraft_variant_aircraft_id_variant_name'),
    )

    def __repr__(self):
        return f'<AircraftVariant {self.variant_name}>'

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'), index=True)
    date = db.Column(db.Date, index=True)
    operator = db.Column(db.String(128))
    location = db.Column(db.String(128))
    fatalities = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    asn_url = db.Column(db.String(256))
    incident_type = db.Column(db.String(64))  # e.g., "Accident", "Hijacking"
    variant_name = db.Column(db.String(64), index=True)
    
    # Relationships
    sources = db.relationship('IncidentSource', backref='incident', lazy='dynamic')
    system_tags = db.relationship('SystemTag', backref='incident', lazy='dynamic')
    report_analysis = db.relationship('ReportAnalysis', backref='incident', uselist=False)

    def __repr__(self):
        return f'<Incident {self.date} - {self.operator}>'

class IncidentSource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=False, index=True)
    source_name = db.Column(db.String(64), index=True)  # 'ASN', 'NTSB', 'FAA_AIDS', 'FAA_SDR'
    source_record_id = db.Column(db.String(128), index=True)
    source_url = db.Column(db.String(512))
    source_data = db.Column(db.JSON)  # Raw data from source
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    confidence_level = db.Column(db.String(32), default='Unverified')

    __table_args__ = (
        db.UniqueConstraint('source_name', 'source_record_id', name='uq_incident_source_source_name_source_record_id'),
        db.Index('ix_incident_source_incident_id_source_name', 'incident_id', 'source_name'),
    )

    def __repr__(self):
        return f'<IncidentSource {self.source_name}>'

class SystemTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=False, index=True)
    system_name = db.Column(db.String(64), index=True)  # 'Hydraulics', 'Electrical', etc.
    confidence = db.Column(db.String(32))  # 'High', 'Medium', 'Low'
    tagged_by = db.Column(db.String(64))  # 'ASN', 'AI', 'User'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SystemTag {self.system_name}>'

class ReportAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=False, index=True)
    report_url = db.Column(db.String(512))
    root_cause = db.Column(db.Text)
    contributing_factors = db.Column(db.JSON)
    findings = db.Column(db.Text)
    recommendations = db.Column(db.JSON)
    narrative_summary = db.Column(db.Text)
    analysis_confidence = db.Column(db.Float)  # 0.0-1.0
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)
    ai_model = db.Column(db.String(64))  # 'gemini-1.5-flash', 'claude-3-opus', etc.

    def __repr__(self):
        return f'<ReportAnalysis {self.incident_id}>'


class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_model = db.Column(db.String(128), index=True)
    user_email = db.Column(db.String(120), index=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Request {self.aircraft_model}>'


class ImportLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_name = db.Column(db.String(64), index=True, nullable=False)
    status = db.Column(db.String(32), index=True, nullable=False, default='running')
    started_at = db.Column(db.DateTime, default=datetime.utcnow, index=True, nullable=False)
    finished_at = db.Column(db.DateTime)

    records_processed = db.Column(db.Integer, default=0)
    duplicates_detected = db.Column(db.Integer, default=0)
    duplicates_merged = db.Column(db.Integer, default=0)
    errors_count = db.Column(db.Integer, default=0)

    log_path = db.Column(db.String(512))
    details = db.Column(db.JSON)

    def __repr__(self):
        return f'<ImportLog {self.source_name} {self.status}>'


class JASCMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jasc_code = db.Column(db.String(32), index=True, nullable=False, unique=True)
    jasc_description = db.Column(db.String(256))
    system_name = db.Column(db.String(64), nullable=False, index=True)
    confidence = db.Column(db.String(32))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True, nullable=False)

    def __repr__(self):
        return f'<JASCMapping {self.jasc_code}>'


class ImportState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_name = db.Column(db.String(64), index=True, nullable=False, unique=True)

    last_attempted_at = db.Column(db.DateTime, index=True)
    last_successful_at = db.Column(db.DateTime, index=True)
    last_status = db.Column(db.String(32), index=True)
    last_import_log_id = db.Column(db.Integer)

    last_records_processed = db.Column(db.Integer, default=0)
    last_duplicates_detected = db.Column(db.Integer, default=0)
    last_duplicates_merged = db.Column(db.Integer, default=0)
    last_errors_count = db.Column(db.Integer, default=0)

    last_error = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, index=True, nullable=False)

    def __repr__(self):
        return f'<ImportState {self.source_name}>'
