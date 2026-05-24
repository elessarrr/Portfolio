from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from config import config

db = SQLAlchemy()
migrate = Migrate()
cache = Cache()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure SECRET_KEY is set securely in production
    if config_name == 'production' and app.config.get('SECRET_KEY') == 'you-will-never-guess':
        raise ValueError("No secure SECRET_KEY set for Flask application. This is required in production.")

    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)

    # Register blueprints
    from app.routes import bp as main_bp
    from app.link_picker import pick_primary_href

    app.register_blueprint(main_bp)
    app.jinja_env.globals["pick_primary_href"] = pick_primary_href

    return app
