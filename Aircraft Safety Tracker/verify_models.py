from app import create_app, db
from app.models import IncidentSource, SystemTag, AircraftVariant, ReportAnalysis

app = create_app('default')

with app.app_context():
    print("Verifying models...")
    try:
        sources = IncidentSource.query.all()
        print(f"IncidentSource count: {len(sources)}")
        tags = SystemTag.query.all()
        print(f"SystemTag count: {len(tags)}")
        variants = AircraftVariant.query.all()
        print(f"AircraftVariant count: {len(variants)}")
        analyses = ReportAnalysis.query.all()
        print(f"ReportAnalysis count: {len(analyses)}")
        print("Verification successful!")
    except Exception as e:
        print(f"Verification failed: {e}")
