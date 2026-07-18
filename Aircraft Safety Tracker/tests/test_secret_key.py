"""Production must fail closed on a missing or placeholder SECRET_KEY."""
import pytest

from config import ProductionConfig


def test_production_rejects_missing_secret_key(monkeypatch):
    """None SECRET_KEY must refuse to boot — the old guard only checked the placeholder."""
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", None)
    from app import create_app

    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app("production")


def test_production_rejects_empty_secret_key(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "   ")
    from app import create_app

    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app("production")


def test_production_rejects_placeholder_secret_key(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "you-will-never-guess")
    from app import create_app

    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app("production")


def test_production_accepts_strong_secret_key(monkeypatch):
    monkeypatch.setattr(
        ProductionConfig, "SECRET_KEY", "a-strong-production-secret-key"
    )
    # Avoid needing a real DATABASE_URL for this factory smoke test.
    monkeypatch.setattr(
        ProductionConfig,
        "SQLALCHEMY_DATABASE_URI",
        "sqlite:///:memory:",
    )
    from app import create_app

    app = create_app("production")
    assert app.config["SECRET_KEY"] == "a-strong-production-secret-key"
    assert app.config["DEBUG"] is False


def test_development_still_allows_placeholder():
    """Local default may keep the placeholder; only production fails closed."""
    from app import create_app

    app = create_app("development")
    assert app.config.get("SECRET_KEY")
