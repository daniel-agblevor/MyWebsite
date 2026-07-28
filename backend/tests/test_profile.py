from models import ContentBlock, SiteProfile


def test_profile_contact_fields_are_admin_managed_and_public(app, authenticated):
    response = authenticated.patch(
        "/api/admin/profile",
        json={
            "display_name": "Daniel Yao Agblevor",
            "specialty": "HR Systems & Automation Consultant",
            "location": "Accra, Ghana",
            "phone": "+233 50 916 3767",
            "email": "DANIEL.AGBLEVOR@OUTLOOK.COM",
        },
        headers={"X-CSRF-Token": "csrf-value"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["email"] == "daniel.agblevor@outlook.com"

    public = authenticated.get("/api/profile")
    assert public.status_code == 200
    assert public.get_json()["data"]["phone"] == "+233 50 916 3767"


def test_profile_rejects_invalid_email(authenticated):
    response = authenticated.patch(
        "/api/admin/profile",
        json={"email": "not-an-email"},
        headers={"X-CSRF-Token": "csrf-value"},
    )
    assert response.status_code == 422


def test_seed_defaults_creates_approved_personal_brand(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-defaults"])
    assert result.exit_code == 0
    with app.app_context():
        profile = SiteProfile.query.one()
        hero = ContentBlock.query.filter_by(key="hero").one()
        assert profile.display_name == "Daniel Yao Agblevor"
        assert profile.email == "daniel.agblevor@outlook.com"
        assert "GRA PAYE" in hero.body

