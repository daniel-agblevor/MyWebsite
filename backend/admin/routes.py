import json
from datetime import date, datetime

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for

from api.admin import MODEL_CONFIG, coerce_payload, set_auth_cookies
from extensions import db, limiter
from models import FeatureFlag, Lead, SiteProfile
from services.auth import AuthenticationError, authenticate_with_supabase, new_csrf_token, require_admin_page
from services.storage import StorageError, delete_image_safely, path_from_public_url, upload_image
from validation.schemas import normalize_optional_email, valid_http_url, valid_phone, valid_youtube_url

admin_pages = Blueprint("admin_pages", __name__, url_prefix="/admin")


@admin_pages.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per 15 minutes")
def login():
    if request.method == "GET":
        return render_template("login.html")
    try:
        payload = authenticate_with_supabase(request.form.get("email", "").strip().lower(), request.form.get("password", ""))
    except AuthenticationError:
        flash("Email or password is incorrect.", "error")
        return render_template("login.html"), 401
    csrf_token = new_csrf_token()
    response = make_response(redirect(url_for("admin_pages.dashboard")))
    return set_auth_cookies(response, payload, csrf_token)


@admin_pages.get("")
@require_admin_page
def dashboard():
    status = request.args.get("status", "")
    query = Lead.query
    if status in {"new", "contacted", "closed"}:
        query = query.filter_by(status=status)
    page = max(1, request.args.get("page", 1, type=int))
    leads = query.order_by(Lead.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    flags = {item.feature_name: item.is_enabled for item in FeatureFlag.query.all()}
    return render_template("dashboard.html", leads=leads, flags=flags, status=status, csrf_token=request.cookies.get("admin_csrf", ""))


@admin_pages.post("/leads/<int:lead_id>")
@require_admin_page
def update_lead(lead_id):
    lead = db.session.get(Lead, lead_id)
    status = request.form.get("status")
    if not lead or status not in {"new", "contacted", "closed"}:
        flash("The lead update could not be applied.", "error")
    else:
        lead.status = status
        db.session.commit()
        flash("Lead status updated.", "success")
    return redirect(url_for("admin_pages.dashboard"))


@admin_pages.post("/features/<name>")
@require_admin_page
def update_feature(name):
    if name not in {"services", "portfolio", "case_studies", "testimonials", "blog"}:
        flash("Feature not found.", "error")
    else:
        item = FeatureFlag.query.filter_by(feature_name=name).first() or FeatureFlag(feature_name=name)
        item.is_enabled = request.form.get("is_enabled") == "true"
        db.session.add(item)
        db.session.commit()
        flash("Public section updated.", "success")
    return redirect(url_for("admin_pages.dashboard"))


@admin_pages.route("/content/<kind>", methods=["GET", "POST"])
@require_admin_page
def content(kind):
    if kind not in MODEL_CONFIG:
        return "Content type not found.", 404
    model = MODEL_CONFIG[kind][0]
    if request.method == "POST":
        try:
            _model, data = coerce_payload(kind, json.loads(request.form.get("payload", "{}")))
            if kind == "slideshow":
                data["storage_path"] = path_from_public_url(data.get("image_url"))
            db.session.add(model(**data))
            db.session.commit()
            flash("Content item created.", "success")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            db.session.rollback()
            flash(str(exc), "error")
    items = model.query.order_by(model.id.desc()).limit(100).all()
    allowed = MODEL_CONFIG[kind][1]
    item_payloads = {
        item.id: {
            key: (value.isoformat() if isinstance(value, (date, datetime)) else value)
            for key in allowed
            if (value := getattr(item, key, None)) is not None
        }
        for item in items
    }
    return render_template("content.html", kind=kind, items=items, item_payloads=item_payloads, csrf_token=request.cookies.get("admin_csrf", ""))


@admin_pages.route("/profile", methods=["GET", "POST"])
@require_admin_page
def profile():
    item = SiteProfile.query.first() or SiteProfile()
    if request.method == "POST":
        photo_url = request.form.get("profile_photo_url", "").strip()
        intro_url = request.form.get("intro_video_url", "").strip()
        upload = request.files.get("profile_image")
        if photo_url and not valid_http_url(photo_url):
            flash("Profile image URL must be a valid HTTPS URL.", "error")
            return render_template("profile.html", profile=item, csrf_token=request.cookies.get("admin_csrf", "")), 422
        if intro_url and not valid_youtube_url(intro_url):
            flash("Introduction video must be a valid HTTPS YouTube URL.", "error")
            return render_template("profile.html", profile=item, csrf_token=request.cookies.get("admin_csrf", "")), 422
        phone = request.form.get("phone", "").strip()
        if not valid_phone(phone):
            flash("Enter a valid phone number.", "error")
            return render_template("profile.html", profile=item, csrf_token=request.cookies.get("admin_csrf", "")), 422
        try:
            email = normalize_optional_email(request.form.get("email"))
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("profile.html", profile=item, csrf_token=request.cookies.get("admin_csrf", "")), 422
        values = {
            "display_name": request.form.get("display_name", "").strip(),
            "specialty": request.form.get("specialty", "").strip(),
            "location": request.form.get("location", "").strip(),
            "phone": phone,
            "email": email or "",
        }
        limits = {"display_name": 160, "specialty": 200, "location": 160, "phone": 40, "email": 254}
        if any(len(value) > limits[key] for key, value in values.items()):
            flash("One or more profile fields are too long.", "error")
            return render_template("profile.html", profile=item, csrf_token=request.cookies.get("admin_csrf", "")), 422

        old_path = item.profile_photo_path or path_from_public_url(item.profile_photo_url)
        new_path = old_path
        uploaded_path = None
        if upload and upload.filename:
            try:
                stored = upload_image(upload, "profile")
            except StorageError as exc:
                flash(str(exc), "error")
                return render_template("profile.html", profile=item, csrf_token=request.cookies.get("admin_csrf", "")), 422
            photo_url = stored.url
            new_path = stored.path
            uploaded_path = stored.path
        elif photo_url != (item.profile_photo_url or ""):
            new_path = path_from_public_url(photo_url)

        for key, value in values.items():
            setattr(item, key, value or None)
        item.profile_photo_url = photo_url or None
        item.profile_photo_path = new_path
        item.intro_video_url = intro_url or None
        db.session.add(item)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            delete_image_safely(uploaded_path)
            raise
        if old_path and old_path != new_path:
            delete_image_safely(old_path)
        flash("Site profile updated.", "success")
        return redirect(url_for("admin_pages.profile"))
    return render_template("profile.html", profile=item, csrf_token=request.cookies.get("admin_csrf", ""))


@admin_pages.post("/content/<kind>/<int:item_id>")
@require_admin_page
def edit_content(kind, item_id):
    if kind not in MODEL_CONFIG:
        return "Content type not found.", 404
    model = MODEL_CONFIG[kind][0]
    item = db.session.get(model, item_id)
    if not item:
        flash("Content item not found.", "error")
        return redirect(url_for("admin_pages.content", kind=kind))
    if request.form.get("action") == "delete":
        stored_path = (item.storage_path or path_from_public_url(item.image_url)) if kind == "slideshow" else None
        db.session.delete(item)
        db.session.commit()
        delete_image_safely(stored_path)
        flash("Content item deleted.", "success")
        return redirect(url_for("admin_pages.content", kind=kind))
    try:
        _model, data = coerce_payload(kind, json.loads(request.form.get("payload", "{}")))
        old_path = None
        if kind == "slideshow" and "image_url" in data:
            old_path = item.storage_path or path_from_public_url(item.image_url)
            data["storage_path"] = path_from_public_url(data["image_url"])
        for key, value in data.items():
            setattr(item, key, value)
        db.session.commit()
        if old_path and old_path != getattr(item, "storage_path", None):
            delete_image_safely(old_path)
        flash("Content item updated.", "success")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        db.session.rollback()
        flash(str(exc), "error")
    return redirect(url_for("admin_pages.content", kind=kind))


@admin_pages.post("/logout")
@require_admin_page
def logout():
    response = make_response(redirect(url_for("admin_pages.login")))
    response.delete_cookie("admin_access_token", path="/")
    response.delete_cookie("admin_csrf", path="/")
    return response

