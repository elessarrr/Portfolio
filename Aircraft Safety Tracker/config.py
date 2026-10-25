import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


def _normalize_db_url(url: str | None) -> str | None:
    """Force psycopg2 dialect — psycopg v3 is not installed."""
    if not url:
        return url
    url = url.replace('postgres://', 'postgresql://', 1)
    url = url.replace('postgresql+psycopg://', 'postgresql+psycopg2://', 1)
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    CACHE_TYPE = os.environ.get('CACHE_TYPE') or 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300

_V3_SQLITE = 'sqlite:///' + os.path.join(basedir, 'data/aircraft_safety_v3.db')


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.environ.get('DATABASE_URL')) or _V3_SQLITE

class ProductionConfig(Config):
    DEBUG = False

    # No fallback: missing env → None. create_app() fail-closes on None / empty /
    # known placeholders so production never boots with a weak or absent key.
    SECRET_KEY = os.environ.get('SECRET_KEY')

    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.environ.get('DATABASE_URL')) or \
        'sqlite:///' + os.path.join(basedir, 'data/aircraft_safety.db')

class TestingConfig(Config):
    TESTING = True
    # Explicit test key — do not inherit the public development placeholder.
    SECRET_KEY = 'testing-secret-key-not-for-production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
