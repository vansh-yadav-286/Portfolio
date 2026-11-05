import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def create_session_token(email: str, name: str, role: str, provider: str) -> tuple[str, str]:
    """Issues a signed, stateless session token (no server-side storage - there is
    no database). Returns (token, csrf). `csrf` is also embedded in the token so a
    later request can be checked against it without looking anything up - see
    core/dependencies.py::verify_csrf.
    """
    csrf = secrets.token_urlsafe(24)
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.session_max_age_minutes)
    payload = {
        "sub": email,
        "name": name,
        "role": role,
        "provider": provider,
        "csrf": csrf,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.session_secret, algorithm="HS256")
    return token, csrf


def decode_session_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.session_secret, algorithms=["HS256"])
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid or expired session") from exc


def sign_oauth_state(data: dict) -> str:
    """Signs an OAuth `state` payload so it can be trusted on the callback
    without server-side storage. The value is also echoed back in a cookie
    (see routes/auth.py) so the callback can verify the same browser that
    started the flow is the one completing it, which is what actually
    defends against OAuth CSRF - the signature alone only proves we created it.
    """
    payload = {**data, "iat": int(time.time())}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(settings.session_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def verify_oauth_state(token: str, max_age_seconds: int) -> dict:
    try:
        body, signature = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Malformed OAuth state") from exc

    expected_signature = hmac.new(settings.session_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid OAuth state signature")

    padded = body + "=" * (-len(body) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    if time.time() - payload.get("iat", 0) > max_age_seconds:
        raise ValueError("OAuth state expired")
    return payload
