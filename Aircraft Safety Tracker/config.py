import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    CACHE_TYPE = os.environ.get('CACHE_TYPE') or 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300

_V3_SQLITE = 'sqlite:///' + os.path.join(basedir, 'data/aircraft_safety_v3.db')


class DevelopmentConfig(Config):
    DEBUG = True
    # v3 branch: ASN baseline + NTSB enrichment live in aircraft_safety_v3.db
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or _V3_SQLITE

class ProductionConfig(Config):
    DEBUG = False

    # No fallback: missing env → None. create_app() fail-closes on None / empty /
    # known placeholders so production never boots with a weak or absent key.
    SECRET_KEY = os.environ.get('SECRET_KEY')

    uri = os.environ.get('DATABASE_URL')
    if uri and uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = uri or \
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
