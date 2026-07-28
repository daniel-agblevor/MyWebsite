from datetime import datetime, timedelta, timezone

import jwt

from extensions import db
from models import FeatureFlag, Lead
from services.auth import AuthenticationError, verify_access_token


def seed_leads(app, count=3):
    with app.app_context():
        for index in range(count):
            db.session.add(Lead(name=f"Lead {index}", email=f"lead{index}@example.test", phone="", service_interest="Other", message="A sufficiently detailed inquiry message.", status="new" if index % 2 == 0 else "closed"))
        db.session.commit()


def test_admin_leads_requires_auth(client):
    response = client.get("/api/admin/leads")
    assert response.status_code == 401


def test_admin_leads_supports_pagination_and_filter(app, authenticated):
    seed_leads(app, 4)
    response = authenticated.get("/api/admin/leads?status=new&page=1&per_page=1")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["meta"]["per_page"] == 1
    assert payload["meta"]["total"] == 2


def test_lead_status_update_validates_value(app, authenticated):
    seed_leads(app, 1)
    invalid = authenticated.patch("/api/admin/leads/1", json={"status": "archived"}, headers={"X-CSRF-Token": "csrf-value"})
    assert invalid.status_code == 422
    valid = authenticated.patch("/api/admin/leads/1", json={"status": "contacted"}, headers={"X-CSRF-Token": "csrf-value"})
    assert valid.status_code == 200
    assert valid.get_json()["data"]["status"] == "contacted"


def test_state_change_requires_csrf(app, authenticated):
    seed_leads(app, 1)
    assert authenticated.patch("/api/admin/leads/1", json={"status": "closed"}).status_code == 403


def test_feature_mutation_requires_auth(client):
    assert client.patch("/api/admin/features/services", json={"is_enabled": True}).status_code == 401


def test_feature_mutation_and_disabled_public_endpoint(app, authenticated):
    with app.app_context():
        assert FeatureFlag.query.filter_by(feature_name="services").one().is_enabled is False
    assert authenticated.get("/api/content/services").status_code == 404
    response = authenticated.patch("/api/admin/features/services", json={"is_enabled": True}, headers={"X-CSRF-Token": "csrf-value"})
    assert response.status_code == 200
    assert authenticated.get("/api/services").status_code == 200


def test_expired_legacy_token_is_rejected(app, monkeypatch):
    token = jwt.encode({"sub": "admin", "role": "authenticated", "iss": "https://test-project.supabase.co/auth/v1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, "secret", algorithm="HS256")
    class Response:
        status_code = 200
    monkeypatch.setattr("services.auth.requests.get", lambda *args, **kwargs: Response())
    with app.app_context():
        try:
            verify_access_token(token)
            assert False, "Expired token should fail"
        except AuthenticationError:
            pass

