from datetime import datetime
from flask import current_app

from app.models import ImportState


def inject_import_states():
    states = ImportState.query.order_by(ImportState.source_name.asc()).all()
    states_by_source = {state.source_name: state for state in states}
    footer_source_order = ("ASN", "FAA_AIDS", "FAA_SDR", "NTSB")
    configured_defaults = current_app.config.get("DATA_FRESHNESS_DEFAULTS", {})

    footer_data_freshness = []
    for source_name in footer_source_order:
        state = states_by_source.get(source_name)
        freshness_label = configured_defaults.get(source_name, "Unknown")
        if state and state.last_successful_at:
            freshness_label = state.last_successful_at.strftime("%b %Y")
        footer_data_freshness.append({
            "source_name": source_name,
            "freshness_label": freshness_label,
        })

    return {
        'import_states': states,
        'footer_data_freshness': footer_data_freshness,
        'now': datetime.utcnow(),
    }
