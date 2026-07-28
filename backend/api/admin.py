from datetime import datetime

from flask import Blueprint, current_app, jsonify, make_response, request

from api.public import error, success
from api.serializers import serialize
from extensions import db, limiter
from models import BlogPost, CaseStudy, ContentBlock, FeatureFlag, Lead, PortfolioProject, Service, SiteProfile, SlideshowImage, Testimonial
from services.auth import AuthenticationError, authenticate_with_supabase, new_csrf_token, require_admin
from services.storage import StorageError, delete_image_safely, path_from_public_url, upload_image
from validation.schemas import normalize_optional_email, sanitize_rich_html, valid_http_url, valid_phone, valid_youtube_url

admin_api = Blueprint("admin_api", __name__, url_prefix="/api/admin")

MODEL_CONFIG = {
    "services": (Service, {"title", "short_description", "client_problem", "solution", "capabilities", "cta_label", "cta_context", "is_featured", "display_order", "is_enabled"}),
    "portfolio": (PortfolioProject, {"title", "description", "external_link", "tech_pills", "youtube_video_url", "is_published"}),
    "case-studies": (CaseStudy, {"slug", "title", "summary", "context", "challenge", "constraints", "approach", "solution", "outcome", "tools", "reflection", "is_featured", "is_published"}),
    "testimonials": (Testimonial, {"client_name", "company", "quote", "rating", "is_published"}),
    "blog": (BlogPost, {"title", "excerpt", "full_content", "linkedin_url", "published_at", "is_published"}),
    "slideshow": (SlideshowImage, {"image_url", "caption", "alt_text", "sort_order"}),
    "content-blocks": (ContentBlock, {"key", "title", "body", "data"}),
}


def set_auth_cookies(response, auth_payload, csrf_token):
    secure = not current_app.debug
    max_age = int(auth_payload.get("expires_in", 3600))
    response.set_cookie("admin_access_token", auth_payload["access_token"], max_age=max_age, secure=secure, httponly=True, samesite="Strict", path="/")
    response.set_cookie("admin_csrf", csrf_token, max_age=max_age, secure=secure, httponly=False, samesite="Strict", path="/")
    return response


@admin_api.post("/login")
@limiter.limit("10 per 15 minutes")
def login():
    payload = request.get_json(silent=True) or request.form
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    if not email or not password:
        return error("validation_error", "Email and password are required.", 422)
    try:
        auth_payload = authenticate_with_supabase(email, password)
    except AuthenticationError:
        return error("invalid_credentials", "Email or password is incorrect.", 401)
    csrf_token = new_csrf_token()
    response = make_response(jsonify({"ok": True, "data": {"csrf_token": csrf_token}}), 200)
    return set_auth_cookies(response, auth_payload, csrf_token)


@admin_api.post("/logout")
@require_admin
def logout():
    response = make_response(jsonify({"ok": True, "data": None}))
    response.delete_cookie("admin_access_token", path="/")
    response.delete_cookie("admin_csrf", path="/")
    return response


@admin_api.get("/leads")
@require_admin
def leads():
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except ValueError:
        return error("validation_error", "Pagination values must be integers.", 422)
    query = Lead.query
    status = request.args.get("status")
    if status:
        if status not in {"new", "contacted", "closed"}:
            return error("validation_error", "Invalid lead status.", 422)
        query = query.filter_by(status=status)
    pagination = query.order_by(Lead.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return success([serialize(item) for item in pagination.items], meta={"page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages})


@admin_api.get("/leads/<int:lead_id>")
@require_admin
def lead_detail(lead_id):
    lead = db.session.get(Lead, lead_id)
    return success(serialize(lead)) if lead else error("not_found", "Lead not found.", 404)


@admin_api.patch("/leads/<int:lead_id>")
@require_admin
def update_lead(lead_id):
    lead = db.session.get(Lead, lead_id)
    if not lead:
        return error("not_found", "Lead not found.", 404)
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in {"new", "contacted", "closed"}:
        return error("validation_error", "Status must be new, contacted, or closed.", 422, {"status": "Choose a valid status."})
    lead.status = status
    db.session.commit()
    return success(serialize(lead))


@admin_api.patch("/features/<name>")
@require_admin
def update_feature(name):
    if name not in {"services", "portfolio", "case_studies", "testimonials", "blog"}:
        return error("not_found", "Feature not found.", 404)
    enabled = (request.get_json(silent=True) or {}).get("is_enabled")
    if not isinstance(enabled, bool):
        return error("validation_error", "is_enabled must be a boolean.", 422)
    item = FeatureFlag.query.filter_by(feature_name=name).first() or FeatureFlag(feature_name=name)
    item.is_enabled = enabled
    db.session.add(item)
    db.session.commit()
    return success(serialize(item))


def coerce_payload(kind, payload):
    model, allowed = MODEL_CONFIG[kind]
    if not isinstance(payload, dict) or not payload:
        raise ValueError("A non-empty JSON object is required.")
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError("Unexpected fields: " + ", ".join(sorted(unknown)))
    data = {key: value for key, value in payload.items() if key in allowed}
    for key in ("capabilities", "tech_pills", "tools"):
        if key in data and (not isinstance(data[key], list) or not all(isinstance(value, str) for value in data[key])):
            raise ValueError(f"{key} must be a list of text values.")
    if "data" in data and not isinstance(data["data"], dict):
        raise ValueError("data must be an object.")
    for key in ("external_link", "linkedin_url", "image_url"):
        if data.get(key) and not valid_http_url(data[key]):
            raise ValueError(f"{key} must be a valid HTTPS URL.")
    if data.get("youtube_video_url") and not valid_youtube_url(data["youtube_video_url"]):
        raise ValueError("youtube_video_url must be a valid HTTPS YouTube URL.")
    if "full_content" in data:
        data["full_content"] = sanitize_rich_html(data["full_content"])
    if data.get("published_at") and isinstance(data["published_at"], str):
        data["published_at"] = datetime.fromisoformat(data["published_at"].replace("Z", "+00:00"))
    if "rating" in data and data["rating"] is not None and int(data["rating"]) not in range(1, 6):
        raise ValueError("rating must be between 1 and 5.")
    return model, data


@admin_api.route("/content/<kind>", methods=["GET", "POST"])
@require_admin
def collection(kind):
    if kind not in MODEL_CONFIG:
        return error("not_found", "Content type not found.", 404)
    model = MODEL_CONFIG[kind][0]
    if request.method == "GET":
        page = max(1, request.args.get("page", 1, type=int))
        pagination = model.query.order_by(model.id.desc()).paginate(page=page, per_page=25, error_out=False)
        return success([serialize(item) for item in pagination.items], meta={"page": page, "total": pagination.total, "pages": pagination.pages})
    try:
        model, data = coerce_payload(kind, request.get_json(silent=True))
        if kind == "slideshow":
            data["storage_path"] = path_from_public_url(data.get("image_url"))
        item = model(**data)
        db.session.add(item)
        db.session.commit()
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return error("validation_error", str(exc), 422)
    return success(serialize(item), 201)


@admin_api.route("/content/<kind>/<int:item_id>", methods=["GET", "PATCH", "DELETE"])
@require_admin
def collection_item(kind, item_id):
    if kind not in MODEL_CONFIG:
        return error("not_found", "Content type not found.", 404)
    model = MODEL_CONFIG[kind][0]
    item = db.session.get(model, item_id)
    if not item:
        return error("not_found", "Content item not found.", 404)
    if request.method == "GET":
        return success(serialize(item))
    if request.method == "DELETE":
        stored_path = (item.storage_path or path_from_public_url(item.image_url)) if kind == "slideshow" else None
        db.session.delete(item)
        db.session.commit()
        delete_image_safely(stored_path)
        return success(None)
    try:
        _model, data = coerce_payload(kind, request.get_json(silent=True))
        old_path = None
        if kind == "slideshow" and "image_url" in data:
            old_path = item.storage_path or path_from_public_url(item.image_url)
            data["storage_path"] = path_from_public_url(data["image_url"])
        for key, value in data.items():
            setattr(item, key, value)
        db.session.commit()
        if old_path and old_path != getattr(item, "storage_path", None):
            delete_image_safely(old_path)
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return error("validation_error", str(exc), 422)
    return success(serialize(item))


@admin_api.route("/profile", methods=["GET", "PATCH"])
@require_admin
def profile():
    item = SiteProfile.query.first() or SiteProfile()
    if request.method == "GET":
        return success(serialize(item))
    payload = request.get_json(silent=True) or {}
    allowed = {"profile_photo_url", "intro_video_url", "display_name", "specialty", "location", "phone", "email"}
    if set(payload) - allowed:
        return error("validation_error", "Unexpected profile fields.", 422)
    if payload.get("profile_photo_url") and not valid_http_url(payload["profile_photo_url"]):
        return error("validation_error", "Profile photo must use a valid HTTPS URL.", 422)
    if payload.get("intro_video_url") and not valid_youtube_url(payload["intro_video_url"]):
        return error("validation_error", "Intro video must be a valid YouTube URL.", 422)
    if "phone" in payload:
        phone = str(payload.get("phone") or "").strip()
        if not valid_phone(phone):
            return error("validation_error", "Enter a valid phone number.", 422)
        payload["phone"] = phone or None
    if "email" in payload:
        try:
            payload["email"] = normalize_optional_email(payload.get("email"))
        except ValueError as exc:
            return error("validation_error", str(exc), 422)
    old_path = item.profile_photo_path or path_from_public_url(item.profile_photo_url)
    if "profile_photo_url" in payload:
        item.profile_photo_path = path_from_public_url(payload["profile_photo_url"])
    elif old_path and not item.profile_photo_path:
        item.profile_photo_path = old_path
    for key, value in payload.items():
        setattr(item, key, value)
    db.session.add(item)
    db.session.commit()
    if old_path and old_path != item.profile_photo_path:
        delete_image_safely(old_path)
    return success(serialize(item))


@admin_api.post("/media")
@require_admin
def media_upload():
    file = request.files.get("image")
    if not file:
        return error("validation_error", "Choose an image to upload.", 422)
    try:
        stored = upload_image(file, request.form.get("folder", "uploads"))
    except StorageError as exc:
        return error("upload_failed", str(exc), 422)
    return success({"url": stored.url, "path": stored.path}, 201)

