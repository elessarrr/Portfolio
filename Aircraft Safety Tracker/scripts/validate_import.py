from run import app
from app import db
from app.models import ImportLog, Incident, IncidentSource, Aircraft

def run_validation():
    with app.app_context():
        logs = ImportLog.query.order_by(ImportLog.started_at.desc()).limit(10).all()
        print("Recent Import Logs:")
        for l in logs:
            print(f'[{l.started_at}] Source={l.source_name}, Status={l.status}, Processed={l.records_processed}, Duplicates={l.duplicates_merged}, Errors={l.errors_count}')
            
        print("\nReferential Integrity Check:")
        # Check for any incident sources that don't point to a valid incident
        orphans = IncidentSource.query.filter(IncidentSource.incident_id.notin_(
            db.session.query(Incident.id)
        )).count()
        
        print(f"Orphaned IncidentSources: {orphans}")
        
        # Check incident count by source
        ntsb_count = IncidentSource.query.filter_by(source_name='NTSB').count()
        faa_count = IncidentSource.query.filter_by(source_name='FAA_AIDS').count()
        print(f"NTSB Records in DB: {ntsb_count}")
        print(f"FAA AIDS Records in DB: {faa_count}")
        
        # Verify specific missing 2026 incident
        boeing_717_2026 = db.session.query(Incident).join(Aircraft).filter(
            Aircraft.model_name.ilike('%717%'),
            Incident.date >= '2026-01-01'
        ).count()
        print(f"Boeing 717 2026 Incidents in DB: {boeing_717_2026}")
        
        print("\nValidation complete.")

if __name__ == '__main__':
    run_validation()
