import json
import os
import sys
from datetime import datetime
from dateutil import parser

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Aircraft, Incident

app = create_app()

def parse_date(date_str):
    try:
        # Try fuzzy parsing which handles most formats
        # "11 May 1933" -> 1933-05-11
        # "May 1933" -> 1933-05-?? (default day=1?)
        # "1933" -> 1933-??-?? (default month=1, day=1?)
        
        # Clean date string
        clean_date = date_str.strip()
        
        # Handle "?? ??? 1933" or similar ASN oddities
        if "??" in clean_date:
            clean_date = clean_date.replace("??", "01")
        
        # Handle "xx May 1938" -> Replace xx with 01
        if "xx" in clean_date.lower():
            clean_date = clean_date.lower().replace("xx", "01")

        # Handle "unk. date 1943" -> Extract year
        if "unk. date" in clean_date.lower():
            # Try to find a 4-digit year
            import re
            match = re.search(r'\d{4}', clean_date)
            if match:
                clean_date = f"01 Jan {match.group(0)}"
            else:
                return None
            
        return parser.parse(clean_date).date()
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None

def import_file(filepath, manufacturer):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    print(f"Importing {filepath}...")
    with open(filepath, 'r') as f:
        data = json.load(f)

    with app.app_context():
        count = 0
        for item in data:
            model_name = item.get('model_name')
            if not model_name:
                continue

            # Find or create Aircraft
            aircraft = Aircraft.query.filter_by(model_name=model_name).first()
            if not aircraft:
                aircraft = Aircraft(
                    manufacturer=manufacturer,
                    model_name=model_name,
                    total_incidents=0,
                    fatal_incidents=0,
                    total_fatalities=0
                )
                db.session.add(aircraft)
                db.session.commit() # Commit to get ID

            # Create Incident
            date_obj = parse_date(item.get('date'))
            fatalities = item.get('fatalities', 0)
            
            # Check if incident already exists (avoid dupes on re-run)
            existing = Incident.query.filter_by(
                asn_url=item.get('asn_url')
            ).first()
            
            if existing:
                # Update existing record if needed (e.g. date was None)
                if existing.date is None and date_obj is not None:
                    existing.date = date_obj
                    # print(f"Updated date for {item.get('asn_url')}") # Optional logging
            else:
                incident = Incident(
                    aircraft_id=aircraft.id,
                    date=date_obj,
                    operator=item.get('operator'),
                    location=item.get('location'),
                    fatalities=fatalities,
                    description=item.get('narrative'),
                    asn_url=item.get('asn_url'),
                    incident_type=item.get('category')
                )
                db.session.add(incident)
                
                # Update stats
                aircraft.total_incidents += 1
                aircraft.total_fatalities += fatalities
                if fatalities > 0:
                    aircraft.fatal_incidents += 1
                
                count += 1
        
        db.session.commit()
        print(f"Imported {count} new incidents for {manufacturer}.")

def main():
    import_file('data/raw/boeing_incidents.json', 'Boeing')
    import_file('data/raw/airbus_incidents.json', 'Airbus')

if __name__ == "__main__":
    main()
