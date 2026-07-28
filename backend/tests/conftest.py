import pathlib
import sys

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import create_app
from extensions import db
from models import FeatureFlag, Lead


@pytest.fixture
def app(tmp_path):
    app = create_app(
        "development",
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
            "SUPABASE_URL": "https://test-project.supabase.co",
            "SUPABASE_PUBLISHABLE_KEY": "test-publishable-key",
            "SUPABASE_SECRET_KEY": "test-secret-key",
            "SUPABASE_MEDIA_BUCKET": "site-media",
            "RESEND_API_KEY": "test-resend-key",
            "RESEND_FROM_EMAIL": "Website <site@example.test>",
            "CONTACT_NOTIFICATION_TO": "owner@example.test",
        },
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        for name in ("services", "portfolio", "case_studies", "testimonials", "blog"):
            db.session.add(FeatureFlag(feature_name=name, is_enabled=False))
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def valid_contact():
    return {
        "name": "Ama Mensah",
        "email": "AMA@example.com",
        "phone": "+233 20 000 0000",
        "service_interest": "HR Systems & Automation",
        "message": "We need to replace a manual onboarding and reporting process.",
    }


@pytest.fixture
def authenticated(client, monkeypatch):
    monkeypatch.setattr("services.auth.verify_access_token", lambda _token: {"sub": "admin-id", "role": "authenticated"})
    client.set_cookie("admin_access_token", "valid-token")
    client.set_cookie("admin_csrf", "csrf-value")
    return client

