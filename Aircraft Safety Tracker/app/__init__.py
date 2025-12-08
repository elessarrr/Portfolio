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

    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)

    # Register blueprints and routes here later
    # from app import routes
    
    # Simple test route to verify setup
    @app.route('/')
    def index():
        return "Aircraft Safety Tracker API is running!"

    return app
