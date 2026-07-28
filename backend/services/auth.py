import functools
import hmac
import secrets

import jwt
import requests
from flask import current_app, g, jsonify, redirect, request, url_for


class AuthenticationError(Exception):
    pass


def _publishable_key():
    return current_app.config.get("SUPABASE_PUBLISHABLE_KEY") or current_app.config.get("SUPABASE_ANON_KEY", "")


def authenticate_with_supabase(email, password):
    response = requests.post(
        f"{current_app.config['SUPABASE_URL']}/auth/v1/token",
        params={"grant_type": "password"},
        headers={
            "apikey": _publishable_key(),
            "Content-Type": "application/json",
        },
        json={"email": email, "password": password},
        timeout=10,
    )
    if response.status_code != 200:
        raise AuthenticationError("Invalid credentials")
    payload = response.json()
    if not payload.get("access_token"):
        raise AuthenticationError("Invalid authentication response")
    return payload


def verify_access_token(token):
    if not token:
        raise AuthenticationError("Missing token")
    supabase_url = current_app.config["SUPABASE_URL"]
    issuer = f"{supabase_url}/auth/v1"
    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        if algorithm in {"RS256", "ES256"}:
            client = jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_jwk_set=True, lifespan=600)
            signing_key = client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[algorithm],
                audience="authenticated",
                issuer=issuer,
                options={"require": ["exp", "iss", "sub", "role"]},
            )
        elif algorithm == "HS256":
            response = requests.get(
                f"{issuer}/user",
                headers={"apikey": _publishable_key(), "Authorization": f"Bearer {token}"},
                timeout=8,
            )
            if response.status_code != 200:
                raise AuthenticationError("Invalid token")
            claims = jwt.decode(token, options={"verify_signature": False, "verify_exp": True})
            if claims.get("iss") != issuer or claims.get("role") != "authenticated" or not claims.get("sub"):
                raise AuthenticationError("Invalid claims")
        else:
            raise AuthenticationError("Unsupported token algorithm")
    except (jwt.PyJWTError, requests.RequestException, ValueError) as exc:
        raise AuthenticationError("Invalid token") from exc
    if claims.get("role") != "authenticated":
        raise AuthenticationError("Insufficient role")
    return claims


def _get_token():
    return request.cookies.get("admin_access_token")


def require_admin(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        try:
            g.admin_claims = verify_access_token(_get_token())
        except AuthenticationError:
            return jsonify({"ok": False, "error": {"code": "unauthorized", "message": "Authentication is required."}}), 401
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not valid_csrf():
            return jsonify({"ok": False, "error": {"code": "csrf_failed", "message": "Security token mismatch."}}), 403
        return view(*args, **kwargs)
    return wrapped


def require_admin_page(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        try:
            g.admin_claims = verify_access_token(_get_token())
        except AuthenticationError:
            return redirect(url_for("admin_pages.login"))
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not valid_csrf():
            return "Security token mismatch.", 403
        return view(*args, **kwargs)
    return wrapped


def new_csrf_token():
    return secrets.token_urlsafe(32)


def valid_csrf():
    cookie_value = request.cookies.get("admin_csrf", "")
    request_value = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
    return bool(cookie_value and request_value and hmac.compare_digest(cookie_value, request_value))

