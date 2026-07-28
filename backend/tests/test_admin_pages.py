from extensions import db
from models import Service


def test_admin_content_editor_renders_serializable_payload(app, authenticated):
    with app.app_context():
        db.session.add(
            Service(
                title="HR systems",
                short_description="A clear description",
                client_problem="A manual process creates recurring errors.",
                solution="A maintainable workflow with documented controls.",
                capabilities=["Workflow design"],
                cta_context="HR Systems & Automation",
            )
        )
        db.session.commit()
    response = authenticated.get("/admin/content/services")
    assert response.status_code == 200
    assert b'"capabilities"' in response.data
    assert b"Workflow design" in response.data

