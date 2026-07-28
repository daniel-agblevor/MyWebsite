from datetime import datetime, timezone

from sqlalchemy import CheckConstraint

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Lead(db.Model):
    __tablename__ = "leads"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False, index=True)
    phone = db.Column(db.String(40), nullable=True)
    service_interest = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="new", index=True)
    idempotency_key = db.Column(db.String(128), unique=True, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    __table_args__ = (CheckConstraint("status IN ('new', 'contacted', 'closed')", name="lead_status"),)


class FeatureFlag(db.Model):
    __tablename__ = "feature_flags"
    id = db.Column(db.Integer, primary_key=True)
    feature_name = db.Column(db.String(64), nullable=False, unique=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=False)


class Service(TimestampMixin, db.Model):
    __tablename__ = "services"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    short_description = db.Column(db.String(320), nullable=False)
    client_problem = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text, nullable=False)
    capabilities = db.Column(db.JSON, nullable=False, default=list)
    cta_label = db.Column(db.String(80), nullable=False, default="Discuss this service")
    cta_context = db.Column(db.String(120), nullable=False)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)


class PortfolioProject(TimestampMixin, db.Model):
    __tablename__ = "portfolio_projects"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    external_link = db.Column(db.String(500), nullable=True)
    tech_pills = db.Column(db.JSON, nullable=False, default=list)
    youtube_video_url = db.Column(db.String(500), nullable=True)
    is_published = db.Column(db.Boolean, nullable=False, default=False)


class CaseStudy(TimestampMixin, db.Model):
    __tablename__ = "case_studies"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(180), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(500), nullable=False)
    context = db.Column(db.Text, nullable=False)
    challenge = db.Column(db.Text, nullable=False)
    constraints = db.Column(db.Text, nullable=False)
    approach = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text, nullable=False)
    outcome = db.Column(db.Text, nullable=False)
    tools = db.Column(db.JSON, nullable=False, default=list)
    reflection = db.Column(db.Text, nullable=False)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    is_published = db.Column(db.Boolean, nullable=False, default=False)

    @property
    def content(self):
        return {key: getattr(self, key) for key in ("context", "challenge", "constraints", "approach", "solution", "outcome", "reflection")}


class Testimonial(TimestampMixin, db.Model):
    __tablename__ = "testimonials"
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(180), nullable=False)
    quote = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)
    is_published = db.Column(db.Boolean, nullable=False, default=False)
    __table_args__ = (CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="testimonial_rating"),)


class BlogPost(TimestampMixin, db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    excerpt = db.Column(db.String(600), nullable=False)
    full_content = db.Column(db.Text, nullable=False)
    linkedin_url = db.Column(db.String(500), nullable=True)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    is_published = db.Column(db.Boolean, nullable=False, default=False)


class SlideshowImage(TimestampMixin, db.Model):
    __tablename__ = "slideshow_images"
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(700), nullable=False)
    storage_path = db.Column(db.String(700), nullable=True)
    caption = db.Column(db.String(300), nullable=False)
    alt_text = db.Column(db.String(300), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0, index=True)


class SiteProfile(TimestampMixin, db.Model):
    __tablename__ = "site_profiles"
    id = db.Column(db.Integer, primary_key=True)
    profile_photo_url = db.Column(db.String(700), nullable=True)
    profile_photo_path = db.Column(db.String(700), nullable=True)
    intro_video_url = db.Column(db.String(500), nullable=True)
    display_name = db.Column(db.String(160), nullable=True)
    specialty = db.Column(db.String(200), nullable=True)
    location = db.Column(db.String(160), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(254), nullable=True)


class ContentBlock(TimestampMixin, db.Model):
    __tablename__ = "content_blocks"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True, index=True)
    title = db.Column(db.String(240), nullable=True)
    body = db.Column(db.Text, nullable=True)
    data = db.Column(db.JSON, nullable=False, default=dict)

