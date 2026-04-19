import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
    CACHE_TYPE = os.environ.get("CACHE_TYPE") or "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH") or 5 * 1024 * 1024)
    REPORT_ANALYZER_MAX_REPORT_TEXT_CHARS = int(
        os.environ.get("REPORT_ANALYZER_MAX_REPORT_TEXT_CHARS") or 50000
    )
    TRUST_X_FORWARDED_FOR = (os.environ.get("TRUST_X_FORWARDED_FOR") or "").lower() in (
        "1",
        "true",
        "yes",
    )
    DATA_FRESHNESS_DEFAULTS = {
        "ASN": "Apr 2026",
        "FAA_AIDS": "Apr 2026",
        "FAA_SDR": "Apr 2026",
        "NTSB": "Apr 2026",
    }


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(
        basedir, "data/aircraft_safety.db"
    )


class ProductionConfig(Config):
    DEBUG = False

    # In production, we MUST have a secure SECRET_KEY set in the environment.
    # The application factory (create_app) will validate this.
    SECRET_KEY = os.environ.get("SECRET_KEY") or ""

    uri = os.environ.get("DATABASE_URL")
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = uri or "sqlite:///" + os.path.join(basedir, "data/aircraft_safety.db")


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
