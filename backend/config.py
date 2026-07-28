import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def normalize_database_url(value: str) -> str:
    if value.startswith("postgres://"):
        return "postgresql://" + value[len("postgres://") :]
    return value


def validate_origin(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("FRONTEND_URL must be an absolute http(s) origin")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("FRONTEND_URL must contain an origin only")
    return f"{parsed.scheme}://{parsed.netloc}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
    DATABASE_URL_RAW = os.getenv("DATABASE_URL", "")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(
        DATABASE_URL_RAW or "sqlite:///local.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
    SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    # Transitional aliases keep existing deployments working while keys are rotated.
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_MEDIA_BUCKET = os.getenv("SUPABASE_MEDIA_BUCKET", "site-media")
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "")
    CONTACT_NOTIFICATION_TO = os.getenv("CONTACT_NOTIFICATION_TO", "")
    FRONTEND_URL = validate_origin(os.getenv("FRONTEND_URL", "http://localhost:5500"))
    # Allows a 5 MB image plus multipart form overhead; image bytes are checked separately.
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    RATELIMIT_STORAGE_URI = "memory://"
    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False

    @classmethod
    def validate(cls):
        required = {
            "SECRET_KEY": cls.SECRET_KEY,
            "DATABASE_URL": cls.DATABASE_URL_RAW,
            "SUPABASE_URL": cls.SUPABASE_URL,
            "SUPABASE_PUBLISHABLE_KEY": cls.SUPABASE_PUBLISHABLE_KEY,
            "SUPABASE_SECRET_KEY": cls.SUPABASE_SECRET_KEY,
            "RESEND_API_KEY": cls.RESEND_API_KEY,
            "RESEND_FROM_EMAIL": cls.RESEND_FROM_EMAIL,
            "CONTACT_NOTIFICATION_TO": cls.CONTACT_NOTIFICATION_TO,
            "FRONTEND_URL": cls.FRONTEND_URL,
        }
        missing = [name for name, value in required.items() if not value]
        if missing or cls.SECRET_KEY == "development-only-change-me":
            missing = sorted(set(missing + (["SECRET_KEY"] if cls.SECRET_KEY == "development-only-change-me" else [])))
            raise RuntimeError("Missing required production settings: " + ", ".join(missing))


CONFIGS = {"development": DevelopmentConfig, "production": ProductionConfig}

