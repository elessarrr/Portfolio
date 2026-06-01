## `app/routes.py`

// Relevant because aircraft incident views are scoped to `aircraft.incidents`, which excludes any incident rows where `incident.aircraft_id` is null.
```python
@bp.route('/aircraft/<int:aircraft_id>')
def aircraft_details(aircraft_id):
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    total_incidents = aircraft.total_incidents or 0
    can_generate_summary = total_incidents > 0 and aircraft_has_incidents(aircraft.id)
    
    # Base query for this specific aircraft
    query = aircraft.incidents
        
    query = apply_incident_filters(query, request.args)
    incidents = apply_source_priority_order(query).distinct().limit(50).all()
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
```

// Relevant because HTMX incident refresh and CSV export use the same `aircraft.incidents` scope and therefore inherit the same visibility limitation.
```python
@bp.route('/aircraft/<int:aircraft_id>/incidents')
def get_incidents(aircraft_id):
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    query = aircraft.incidents
        
    query = apply_incident_filters(query, request.args)
    incidents = apply_source_priority_order(query).distinct().limit(50).all()
    return render_template('components/incident_list.html', incidents=incidents, aircraft=aircraft)


@bp.route('/aircraft/<int:aircraft_id>/incidents/export.csv')
def export_incidents_csv(aircraft_id):
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    query = aircraft.incidents
        
    query = apply_incident_filters(query, request.args)
    
    incidents = apply_source_priority_order(query).distinct().all()
```

## `app/models.py`

// Relevant because `incident.aircraft_id` is the linkage key used by detail views, and ASN has a separate `asn_url` path that can bypass `IncidentSource`.
```python
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
    registration = db.Column(db.String(32), index=True)
    has_discrepancy = db.Column(db.Boolean, default=False)
    discrepancy_details = db.Column(db.JSON)
    
    # Relationships
    sources = db.relationship('IncidentSource', backref='incident', lazy='dynamic')
    system_tags = db.relationship('SystemTag', backref='incident', lazy='dynamic')
    report_analysis = db.relationship('ReportAnalysis', backref='incident', uselist=False)
```

// Relevant because non-ASN source visibility depends on `IncidentSource` rows being attached to incidents that also have a non-null `aircraft_id`.
```python
class IncidentSource(db.Model):
    """
    Represents an external data source that provides information about an incident.
    An Incident can have multiple IncidentSources attached to it (e.g., NTSB, FAA, ASN).
    """
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=False, index=True)
    source_name = db.Column(db.String(64), index=True)  # 'ASN', 'NTSB', 'FAA_AIDS', 'FAA_SDR'
    source_record_id = db.Column(db.String(128), index=True)
    source_url = db.Column(db.String(512))  # The original external URL where the incident data was obtained
    report_url = db.Column(db.String(512))  # Direct link to a PDF report or analysis document if available
    source_data = db.Column(db.JSON)  # Raw data from source
```

## `app/ingestion/importers/base.py`

// Relevant because unresolved `make_model` returns `None`, which directly creates incidents with `aircraft_id=None` in downstream importers.
```python
def resolve_aircraft(self, parsed_record: Dict[str, Any]) -> Optional[int]:
    """
    Attempts to resolve an Aircraft ID based on the parsed record's 'make_model'.
    If the model is Boeing or Airbus and doesn't exist, it auto-creates it.
    """
    make_model = parsed_record.get('make_model')
    if not make_model:
        return None

    make_model = strip_duplicate_words(make_model).strip()
    parsed_record['make_model'] = make_model

    # Try exact match (case-insensitive)
    aircraft = Aircraft.query.filter(Aircraft.model_name.ilike(make_model)).first()
    if aircraft:
        return aircraft.id

    # Check if Boeing or Airbus to auto-create
    lower_make_model = make_model.lower()
    manufacturer = None
    if lower_make_model.startswith('boeing'):
        manufacturer = 'Boeing'
    elif lower_make_model.startswith('airbus'):
        manufacturer = 'Airbus'

    if manufacturer:
        aircraft = Aircraft(
            manufacturer=manufacturer,
            model_name=make_model,
            total_incidents=0,
            fatal_incidents=0,
            total_fatalities=0
        )
        db.session.add(aircraft)
        db.session.flush()  # Flush to get the ID
        self._log_model_creation(aircraft)
        return aircraft.id

    return None
```

## `app/ingestion/importers/ntsb_importer.py`

// Relevant because NTSB inserts call `resolve_aircraft`; if resolution fails, incidents are still created but remain unlinked to aircraft views.
```python
incident = Incident(
    aircraft_id=self.resolve_aircraft(parsed_record),
    date=parsed_record['date'],
    operator=parsed_record.get('operator'),
    location=parsed_record.get('location'),
    fatalities=parsed_record.get('fatalities') or 0,
    description=parsed_record.get('description'),
    incident_type='Accident',
    registration=parsed_record.get('registration'),
)
db.session.add(incident)
db.session.flush()
```

## `app/ingestion/importers/faa_aids_importer.py`

// Relevant because FAA_AIDS follows the same pattern and can persist incidents with null `aircraft_id` when make/model mapping fails.
```python
incident = Incident(
    aircraft_id=self.resolve_aircraft(parsed_record),
    date=parsed_record['date'],
    operator=parsed_record.get('operator'),
    location=parsed_record.get('location'),
    fatalities=parsed_record.get('fatalities') or 0,
    description=parsed_record.get('description'),
    incident_type='Incident',
    registration=parsed_record.get('registration'),
)
db.session.add(incident)
db.session.commit()
```

## `app/ingestion/importers/faa_sdr_importer.py`

// Relevant because FAA_SDR also relies on `resolve_aircraft`, so visibility depends on successful make/model normalization and mapping.
```python
incident = Incident(
    aircraft_id=self.resolve_aircraft(parsed_record),
    date=parsed_record.get("date"),
    operator=parsed_record.get("operator"),
    location=parsed_record.get("location"),
    fatalities=0,
    description=parsed_record.get("description"),
    incident_type="Incident",
    registration=parsed_record.get("registration"),
)
db.session.add(incident)
db.session.flush()
```

## `app/templates/components/incident_list.html`

// Relevant because the template has explicit ASN fallbacks via `incident.asn_url`, so ASN can still appear even when `IncidentSource` attachment is sparse.
```jinja2
{% elif incident.asn_url %}
    <a href="{{ incident.asn_url }}" target="_blank" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 hover:bg-blue-200">ASN &nearr;</a>
{% else %}
    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">No sources</span>
{% endif %}
...
{% if primary_source and (primary_source.report_url or primary_source.source_url) %}
    <a href="{{ primary_source.report_url or primary_source.source_url }}" target="_blank" class="text-primary hover:underline">Details &nearr;</a>
{% elif incident.asn_url %}
    <a href="{{ incident.asn_url }}" target="_blank" class="text-primary hover:underline">Details &nearr;</a>
{% else %}
    <span class="text-xs text-gray-400">No external link</span>
{% endif %}
```

## `scripts/import_data.py`

// Relevant because legacy ASN ingestion writes `asn_url` and `aircraft_id` directly to `Incident` without creating `IncidentSource` rows, creating a split-source data model.
```python
# Check if incident already exists (avoid dupes on re-run)
existing = Incident.query.filter_by(asn_url=item.get("asn_url")).first()

if existing:
    # Update existing record
    existing.date = date_obj
    existing.fatalities = fatalities
    existing.description = item.get("narrative")
    existing.location = item.get("location")
    existing.incident_type = item.get("category")
    existing.operator = item.get("operator")
    if variant_name:
        existing.variant_name = variant_name
else:
    incident = Incident(
        aircraft_id=aircraft.id,
        date=date_obj,
        operator=item.get("operator"),
        location=item.get("location"),
        fatalities=fatalities,
        description=item.get("narrative"),
        asn_url=item.get("asn_url"),
        incident_type=item.get("category"),
        variant_name=variant_name,
    )
    db.session.add(incident)
```
