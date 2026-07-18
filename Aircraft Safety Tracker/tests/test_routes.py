import os

import pytest
from app.models import Request


def test_home_page(client):
    """Test that the home page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Aircraft Safety Tracker' in response.data
    assert b'Search for an aircraft' in response.data


def test_search_endpoint(client, sample_data):
    """Test the search autocomplete endpoint."""
    # Test valid search
    response = client.get('/search?q=Boeing')
    assert response.status_code == 200
    assert b'Boeing 737' in response.data

    # Test empty search
    response = client.get('/search?q=')
    assert response.status_code == 200
    assert response.data == b''

    # Test short search
    response = client.get('/search?q=B')
    assert response.status_code == 200
    # A single character query like "B" should still match models starting with "B" (e.g. Boeing)
    # The current routes.py implementation only returns empty string for len < 1
    assert b'Boeing 737' in response.data

    # Test no results
    response = client.get('/search?q=Airbus')
    assert response.status_code == 200
    assert b'No aircraft found matching' in response.data


def test_search_trigram_failure_falls_back_to_ilike(app, sample_data, monkeypatch):
    """If the Postgres trigram path raises, search must still return ILIKE hits.

    Default tests run on SQLite, so we force the postgresql branch and make
    similarity()/word_similarity() explode — the fail-soft path should recover
    with ILIKE.
    """
    from app import routes as routes_mod

    class Boom:
        def __ge__(self, other):
            raise RuntimeError("simulated trigram failure")

        def __gt__(self, other):
            raise RuntimeError("simulated trigram failure")

        def desc(self):
            raise RuntimeError("simulated trigram failure")

    monkeypatch.setattr(routes_mod.db.engine.dialect, "name", "postgresql")
    monkeypatch.setattr(routes_mod.func, "similarity", lambda *a, **k: Boom())
    monkeypatch.setattr(routes_mod.func, "word_similarity", lambda *a, **k: Boom())
    monkeypatch.setattr(routes_mod.func, "greatest", lambda *a, **k: Boom())

    with app.app_context():
        results = routes_mod._search_aircraft("Boeing")

    assert any(a.model_name == "Boeing 737" for a in results)


@pytest.mark.skipif(
    not (os.environ.get("AST_FUZZY_TEST_DATABASE_URL") or "").startswith(
        ("postgresql://", "postgres://")
    ),
    reason="Set AST_FUZZY_TEST_DATABASE_URL to a Postgres URL to exercise pg_trgm",
)
def test_search_fuzzy_typo_match_on_postgres(monkeypatch):
    """Typo query 'boieng' must find 'Boeing 737' via pg_trgm similarity.

    Gated: requires a real Postgres URL in AST_FUZZY_TEST_DATABASE_URL (pg_trgm
    + the GIN migration applied). Not run in the default SQLite suite.

    Important: patch TestingConfig *before* create_app — a late URI override on
    app.config does not rebind Flask-SQLAlchemy's engine (stays on SQLite).
    """
    from sqlalchemy import text

    import config as config_mod
    from app.models import Aircraft

    uri = os.environ["AST_FUZZY_TEST_DATABASE_URL"]
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)

    monkeypatch.setattr(config_mod.TestingConfig, "SQLALCHEMY_DATABASE_URI", uri)

    # Import after the config patch so create_app picks up the Postgres URI.
    from app import create_app, db

    app = create_app("testing")
    assert app.config["SQLALCHEMY_DATABASE_URI"] == uri

    with app.app_context():
        assert db.engine.dialect.name == "postgresql"
        db.session.remove()
        db.drop_all()
        db.create_all()
        # Ensure extension + index exist even if alembic wasn't run on this DB.
        db.session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        db.session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_aircraft_model_name_trgm "
                "ON aircraft USING gin (model_name gin_trgm_ops)"
            )
        )
        db.session.commit()

        a1 = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737",
            years_in_service=50,
            total_incidents=10,
            fatal_incidents=2,
            total_fatalities=100,
        )
        db.session.add(a1)
        db.session.commit()

        client = app.test_client()
        # Exact substring still works.
        response = client.get("/search?q=Boeing")
        assert response.status_code == 200
        assert b"Boeing 737" in response.data

        # Typo that ILIKE alone would miss — the whole point of pg_trgm.
        response = client.get("/search?q=boieng")
        assert response.status_code == 200
        assert b"Boeing 737" in response.data

        db.session.remove()
        db.drop_all()

def test_aircraft_details(client, sample_data):
    """Test the aircraft details page."""
    response = client.get(f'/aircraft/{sample_data.id}')
    assert response.status_code == 200
    assert b'Boeing 737' in response.data
    assert b'Total Incidents' in response.data
    assert b'Years in Service' not in response.data
    assert b'10' in response.data  # total_incidents from sample_data
    
    # Test non-existent aircraft
    response = client.get('/aircraft/999')
    assert response.status_code == 404
    assert b'Page Not Found' in response.data

def test_incident_filtering(client, sample_data):
    """Test the incident filtering endpoint."""
    # Test all incidents
    response = client.get(f'/aircraft/{sample_data.id}/incidents')
    assert response.status_code == 200
    assert b'Alpha Airlines' in response.data
    assert b'Beta Airlines' in response.data
    
    # Test fatal incidents
    response = client.get(f'/aircraft/{sample_data.id}/incidents?type=fatal')
    assert response.status_code == 200
    assert b'Beta Airlines' in response.data
    assert b'Alpha Airlines' not in response.data
    
    # Test non-fatal incidents
    response = client.get(f'/aircraft/{sample_data.id}/incidents?type=nonfatal')
    assert response.status_code == 200
    assert b'Alpha Airlines' in response.data
    assert b'Beta Airlines' not in response.data

def test_request_data_page(client):
    """Test the data request page."""
    response = client.get('/feedback/request')
    assert response.status_code == 200
    assert b'Request Missing Data' in response.data

def test_request_data_empty_submit_shows_validation(client):
    """Bug 4.2: empty POST must show server-side validation errors."""
    response = client.post(
        '/feedback/request',
        data={'aircraft_model': '', 'email': ''},
    )
    assert response.status_code == 200
    assert b'This field is required' in response.data
    assert b'Request Missing Data' in response.data


def test_request_data_submission(client, app):
    """Test submitting a data request."""
    with app.app_context():
        initial_count = Request.query.count()
        
        response = client.post('/feedback/request', data={
            'aircraft_model': 'New Plane',
            'email': 'test@example.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Thank you! Your request has been recorded' in response.data
        assert Request.query.count() == initial_count + 1
        
        req = Request.query.filter_by(aircraft_model='New Plane').first()
        assert req is not None
        assert req.user_email == 'test@example.com'