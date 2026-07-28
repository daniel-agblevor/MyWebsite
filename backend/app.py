import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import CONFIGS
from extensions import db, limiter, migrate


def create_app(config_name=None, test_config=None):
    environment = config_name or os.getenv("FLASK_ENV", "development")
    config_class = CONFIGS.get(environment, CONFIGS["development"])
    if environment == "production":
        config_class.validate()

    app = Flask(__name__, template_folder="admin/templates", static_folder="static")
    app.config.from_object(config_class)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    CORS(
        app,
        resources={r"/api/*": {"origins": [app.config["FRONTEND_URL"]]}},
        methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
        supports_credentials=True,
    )

    from api.public import public_api
    from api.admin import admin_api
    from admin.routes import admin_pages

    app.register_blueprint(public_api)
    app.register_blueprint(admin_api)
    app.register_blueprint(admin_pages)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.path.startswith("/admin"):
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
            response.headers["Cache-Control"] = "no-store"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; style-src 'self'; script-src 'self'; "
                "img-src 'self' https://*.supabase.co data:; frame-ancestors 'none'; "
                "form-action 'self'; base-uri 'self'"
            )
        else:
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.errorhandler(413)
    def oversized(_error):
        return jsonify({"ok": False, "error": {"code": "payload_too_large", "message": "The request is too large."}}), 413

    @app.errorhandler(429)
    def rate_limited(_error):
        return jsonify({"ok": False, "error": {"code": "rate_limited", "message": "Too many requests. Please try again later."}}), 429

    @app.errorhandler(500)
    def server_error(_error):
        return jsonify({"ok": False, "error": {"code": "server_error", "message": "Something went wrong."}}), 500

    register_commands(app)
    return app


def register_commands(app):
    @app.cli.command("seed-defaults")
    def seed_defaults():
        from models import ContentBlock, FeatureFlag, SiteProfile

        for name in ("services", "portfolio", "case_studies", "testimonials", "blog"):
            if not FeatureFlag.query.filter_by(feature_name=name).first():
                db.session.add(FeatureFlag(feature_name=name, is_enabled=False))
        if not SiteProfile.query.first():
            db.session.add(SiteProfile(
                display_name="Daniel Yao Agblevor",
                specialty="HR Systems & Automation Consultant",
                location="Accra, Ghana",
                phone="+233 50 916 3767",
                email="daniel.agblevor@outlook.com",
            ))
        if not ContentBlock.query.filter_by(key="hero").first():
            db.session.add(ContentBlock(
                key="hero",
                title="Modernize HR operations with systems built for accuracy, compliance, and scale.",
                body="I help Ghanaian and West African organizations modernize HR operations by building automated, compliance-ready systems for payroll, attendance, and workforce reporting. Combining hands-on HR operations experience with technical fluency in Excel/VBA, Python, ZKTeco BioTime, and Power BI, I turn manual, error-prone HR processes into reliable, audit-ready systems — grounded in Ghana's GRA PAYE and SSNIT regulatory framework, and built to ISO 9001/30414-aligned standards.",
                data={"eyebrow": "HR Systems · Automation · Compliance"},
            ))
        db.session.commit()
        print("Default feature flags and site profile are ready.")


if __name__ == "__main__":
    create_app().run()

