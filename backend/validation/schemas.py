import re
from urllib.parse import urlparse

import bleach
from email_validator import EmailNotValidError, validate_email

ALLOWED_SERVICES = {
    "HR Systems & Automation",
    "Payroll Automation",
    "Attendance Systems",
    "Excel/VBA Tooling",
    "Power BI Dashboards",
    "Other",
}


def clean_text(value, maximum, minimum=0):
    if not isinstance(value, str):
        return "", "Must be text."
    cleaned = " ".join(value.split())
    if len(cleaned) < minimum:
        return cleaned, f"Must be at least {minimum} characters."
    if len(cleaned) > maximum:
        return cleaned, f"Must be no more than {maximum} characters."
    return cleaned, None


def validate_contact(payload):
    expected = {"name", "email", "phone", "service_interest", "message"}
    if not isinstance(payload, dict):
        return {}, {"form": "A JSON object is required."}
    extras = set(payload) - expected
    errors = {}
    if extras:
        errors["form"] = "Unexpected fields were supplied."

    data = {}
    data["name"], errors_name = clean_text(payload.get("name", ""), 120, 2)
    data["phone"], errors_phone = clean_text(payload.get("phone", ""), 40)
    data["service_interest"], errors_service = clean_text(payload.get("service_interest", ""), 120, 2)
    data["message"], errors_message = clean_text(payload.get("message", ""), 3000, 20)
    raw_email, errors_email = clean_text(payload.get("email", ""), 254, 3)

    for field, error in (("name", errors_name), ("phone", errors_phone), ("service_interest", errors_service), ("message", errors_message), ("email", errors_email)):
        if error:
            errors[field] = error

    if not errors_email:
        try:
            data["email"] = validate_email(raw_email, check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            errors["email"] = "Enter a valid email address."

    if data.get("phone") and not re.fullmatch(r"[0-9+().\-\s]{7,40}", data["phone"]):
        errors["phone"] = "Enter a valid phone number."
    if data.get("service_interest") not in ALLOWED_SERVICES:
        errors["service_interest"] = "Select a valid service."
    return data, errors


def normalize_optional_email(value):
    value = (value or "").strip().lower()
    if not value:
        return None
    try:
        return validate_email(value, check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise ValueError("Enter a valid email address.") from exc


def valid_phone(value):
    return not value or bool(re.fullmatch(r"[0-9+().\-\s]{7,40}", value))


def valid_http_url(value, allowed_hosts=None):
    if not value:
        return True
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    if allowed_hosts and not any(parsed.hostname == host or parsed.hostname.endswith("." + host) for host in allowed_hosts):
        return False
    return True


def valid_youtube_url(value):
    return valid_http_url(value, {"youtube.com", "youtu.be", "youtube-nocookie.com"})


def sanitize_rich_html(value):
    return bleach.clean(
        value or "",
        tags={"p", "br", "strong", "em", "ul", "ol", "li", "h2", "h3", "blockquote", "a"},
        attributes={"a": ["href", "title", "rel"]},
        protocols={"https"},
        strip=True,
    )

