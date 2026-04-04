from datetime import datetime

from app.models import ImportState


def inject_import_states():
    states = ImportState.query.order_by(ImportState.source_name.asc()).all()
    return {
        'import_states': states,
        'now': datetime.utcnow(),
    }

