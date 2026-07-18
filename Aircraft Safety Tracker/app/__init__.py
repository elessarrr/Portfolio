from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from config import config

db = SQLAlchemy()
migrate = Migrate()
cache = Cache()

# Known-insecure defaults — production must never boot with these.
_INSECURE_SECRET_KEYS = frozenset({
    'you-will-never-guess',
    'your-secret-key-here',  # .env.example placeholder
})


def _assert_secure_production_secret(secret_key):
    """Fail closed: refuse production boot without a strong SECRET_KEY.

    The previous guard only rejected the literal 'you-will-never-guess', so a
    missing env var (ProductionConfig.SECRET_KEY is None) silently passed.
    """
    if secret_key is None:
        raise ValueError(
            "No SECRET_KEY set for Flask application. "
            "This is required in production — set the SECRET_KEY environment variable."
        )
    if not isinstance(secret_key, str) or not secret_key.strip():
        raise ValueError(
            "SECRET_KEY is empty. "
            "Set a non-empty SECRET_KEY environment variable for production."
        )
    if secret_key.strip() in _INSECURE_SECRET_KEYS:
        raise ValueError(
            "SECRET_KEY is a public placeholder. "
            "Set a unique, unguessable SECRET_KEY environment variable for production."
        )


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    if config_name == 'production':
        _assert_secure_production_secret(app.config.get('SECRET_KEY'))

    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)

    # Register blueprints
    from app.routes import bp as main_bp
    from app.link_picker import display_make_model, pick_primary_href
    from app.ingestion.url_builders.ntsb import is_foreign_led_ntsb
    from app.services.deepseek import (
        GENERATING_MARKER,
        SUMMARY_UNAVAILABLE_USER_MESSAGE,
        display_ai_summary,
        is_summary_fresh,
    )

    app.register_blueprint(main_bp)
    app.jinja_env.globals["pick_primary_href"] = pick_primary_href
    app.jinja_env.globals["display_make_model"] = display_make_model
    app.jinja_env.globals["is_foreign_led_ntsb"] = is_foreign_led_ntsb
    app.jinja_env.globals["display_ai_summary"] = display_ai_summary
    app.jinja_env.globals["is_summary_fresh"] = is_summary_fresh
    app.jinja_env.globals["summary_generating_marker"] = GENERATING_MARKER
    app.jinja_env.globals["summary_unavailable_message"] = SUMMARY_UNAVAILABLE_USER_MESSAGE

    return app
