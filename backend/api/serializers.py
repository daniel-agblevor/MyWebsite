from datetime import date, datetime

from models import BlogPost, CaseStudy, ContentBlock, FeatureFlag, Lead, PortfolioProject, Service, SiteProfile, SlideshowImage, Testimonial


def iso(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def serialize(item):
    if isinstance(item, FeatureFlag):
        return {"feature_name": item.feature_name, "is_enabled": item.is_enabled}
    if isinstance(item, Lead):
        return {key: iso(getattr(item, key)) for key in ("id", "name", "email", "phone", "service_interest", "message", "status", "created_at")}
    if isinstance(item, Service):
        keys = ("id", "title", "short_description", "client_problem", "solution", "capabilities", "cta_label", "cta_context", "is_featured", "display_order")
    elif isinstance(item, PortfolioProject):
        keys = ("id", "title", "description", "external_link", "tech_pills", "youtube_video_url", "created_at")
    elif isinstance(item, CaseStudy):
        keys = ("id", "slug", "title", "summary", "context", "challenge", "constraints", "approach", "solution", "outcome", "tools", "reflection", "is_featured", "created_at")
    elif isinstance(item, Testimonial):
        keys = ("id", "client_name", "company", "quote", "rating", "created_at")
    elif isinstance(item, BlogPost):
        keys = ("id", "title", "excerpt", "full_content", "linkedin_url", "published_at")
    elif isinstance(item, SlideshowImage):
        keys = ("id", "image_url", "caption", "alt_text", "sort_order")
    elif isinstance(item, SiteProfile):
        keys = ("id", "profile_photo_url", "intro_video_url", "display_name", "specialty", "location", "phone", "email")
    elif isinstance(item, ContentBlock):
        keys = ("id", "key", "title", "body", "data")
    else:
        raise TypeError(f"No serializer for {type(item)!r}")
    return {key: iso(getattr(item, key)) for key in keys}

