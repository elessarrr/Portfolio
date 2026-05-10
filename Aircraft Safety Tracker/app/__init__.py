from flask import Flask
from flask_caching import Cache
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

from config import config

db = SQLAlchemy()
migrate = Migrate()
cache = Cache()


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    if config_name == "production":
        secret_key = app.config.get("SECRET_KEY")
        if not secret_key or secret_key == "you-will-never-guess" or len(str(secret_key)) < 32:
            raise ValueError("A strong SECRET_KEY (>=32 chars) is required in production.")

    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)

    with app.app_context():
        if db.engine.dialect.name == "sqlite":
            insp = inspect(db.engine)
            if insp.has_table("incident"):
                cols = {c["name"] for c in insp.get_columns("incident")}
                if "variant_name" not in cols:
                    db.session.execute(
                        text("ALTER TABLE incident ADD COLUMN variant_name VARCHAR(64)")
                    )
                    db.session.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_incident_variant_name ON incident (variant_name)"
                        )
                    )
                    db.session.commit()

    # Register blueprints
    from app.routes import bp as main_bp

    app.register_blueprint(main_bp)

    from app.context_processors import inject_import_states

    app.context_processor(inject_import_states)

    from app.ingestion.cli import import_data

    app.cli.add_command(import_data)

    return app
