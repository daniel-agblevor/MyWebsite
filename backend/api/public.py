import hashlib

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from api.serializers import serialize
from extensions import db, limiter
from models import BlogPost, CaseStudy, ContentBlock, FeatureFlag, Lead, PortfolioProject, Service, SiteProfile, SlideshowImage, Testimonial
from services.email import EmailDeliveryError, send_lead_notification
from validation.schemas import validate_contact

public_api = Blueprint("public_api", __name__, url_prefix="/api")


def success(data=None, status=200, meta=None):
    payload = {"ok": True, "data": data}
    if meta is not None:
        payload["meta"] = meta
    return jsonify(payload), status


def error(code, message, status, fields=None):
    detail = {"code": code, "message": message}
    if fields:
        detail["fields"] = fields
    return jsonify({"ok": False, "error": detail}), status


def feature_enabled(name):
    feature = FeatureFlag.query.filter_by(feature_name=name).first()
    return bool(feature and feature.is_enabled)


@public_api.get("/features")
def features():
    known = ("services", "portfolio", "case_studies", "testimonials", "blog")
    values = {item.feature_name: item.is_enabled for item in FeatureFlag.query.filter(FeatureFlag.feature_name.in_(known)).all()}
    return success({name: bool(values.get(name, False)) for name in known})


@public_api.post("/contact")
@limiter.limit("5 per hour")
def contact():
    if not request.is_json:
        return error("unsupported_media_type", "Send the form as JSON.", 415)
    data, errors = validate_contact(request.get_json(silent=True))
    if errors:
        return error("validation_error", "Please correct the highlighted fields.", 422, errors)
    supplied_key = request.headers.get("Idempotency-Key", "").strip()
    idempotency_key = hashlib.sha256(supplied_key.encode()).hexdigest() if supplied_key else None
    if idempotency_key:
        existing = Lead.query.filter_by(idempotency_key=idempotency_key).first()
        if existing:
            return success({"id": existing.id, "message": "Your inquiry was already received."}, 200)
    lead = Lead(**data, idempotency_key=idempotency_key)
    db.session.add(lead)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = Lead.query.filter_by(idempotency_key=idempotency_key).first()
        return success({"id": existing.id if existing else None, "message": "Your inquiry was already received."}, 200)
    try:
        send_lead_notification(lead)
    except EmailDeliveryError:
        return success({"id": lead.id, "message": "Your inquiry was saved. Notification delivery is delayed.", "notification_delayed": True}, 202)
    return success({"id": lead.id, "message": "Thank you. Your inquiry has been received."}, 201)


def gated_list(feature, query):
    if not feature_enabled(feature):
        return error("not_found", "This section is not available.", 404)
    return success([serialize(item) for item in query.all()])


@public_api.get("/services")
def services():
    return gated_list("services", Service.query.filter_by(is_enabled=True).order_by(Service.display_order, Service.id))


@public_api.get("/portfolio")
def portfolio():
    return gated_list("portfolio", PortfolioProject.query.filter_by(is_published=True).order_by(PortfolioProject.created_at.desc()))


@public_api.get("/case-studies")
def case_studies():
    return gated_list("case_studies", CaseStudy.query.filter_by(is_published=True).order_by(CaseStudy.is_featured.desc(), CaseStudy.created_at.desc()))


@public_api.get("/case-studies/<slug>")
def case_study(slug):
    if not feature_enabled("case_studies"):
        return error("not_found", "This section is not available.", 404)
    item = CaseStudy.query.filter_by(slug=slug, is_published=True).first()
    return success(serialize(item)) if item else error("not_found", "Case study not found.", 404)


@public_api.get("/testimonials")
def testimonials():
    return gated_list("testimonials", Testimonial.query.filter_by(is_published=True).order_by(Testimonial.created_at.desc()))


@public_api.get("/blog")
def blog():
    return gated_list("blog", BlogPost.query.filter_by(is_published=True).order_by(BlogPost.published_at.desc()))


@public_api.get("/slideshow")
def slideshow():
    return success([serialize(item) for item in SlideshowImage.query.order_by(SlideshowImage.sort_order, SlideshowImage.id).limit(15).all()])


@public_api.get("/profile")
def profile():
    item = SiteProfile.query.first()
    return success(serialize(item) if item else None)


@public_api.get("/content/<key>")
def content(key):
    if key not in {"hero", "kpis", "about", "contact"}:
        return error("not_found", "Content not found.", 404)
    item = ContentBlock.query.filter_by(key=key).first()
    return success(serialize(item) if item else None)

