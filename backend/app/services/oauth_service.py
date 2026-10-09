import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.oauth_login_code import OAuthLoginCode
from app.models.user import User, UserRole

# How long a one-time login code (see create_login_code/consume_login_code)
# stays redeemable. It only ever needs to survive one redirect hop from the
# backend callback to the frontend, which then immediately exchanges it.
LOGIN_CODE_TTL_SECONDS = 60

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

HTTP_TIMEOUT = 10


class OAuthError(Exception):
    """A problem with the OAuth exchange that is safe to show the visitor."""


def oauth_configured(provider: str) -> bool:
    if provider == "google":
        return bool(settings.google_client_id and settings.google_client_secret)
    if provider == "github":
        return bool(settings.github_client_id and settings.github_client_secret)
    return False


def google_redirect_uri() -> str:
    return f"{settings.backend_url.rstrip('/')}/api/auth/google/callback"


def github_redirect_uri() -> str:
    return f"{settings.backend_url.rstrip('/')}/api/auth/github/callback"


def build_google_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def build_github_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": github_redirect_uri(),
        "scope": "read:user user:email",
        "state": state,
        "allow_signup": "true",
    }
    return f"{GITHUB_AUTH_URL}?{urlencode(params)}"


def exchange_google_code(code: str) -> dict:
    resp = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": google_redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=HTTP_TIMEOUT,
    )
    if resp.status_code != 200:
        raise OAuthError("Google did not accept that login attempt. Please try again.")
    data = resp.json()
    if "access_token" not in data:
        raise OAuthError("Google did not accept that login attempt. Please try again.")
    return data


def fetch_google_profile(access_token: str) -> dict:
    resp = httpx.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=HTTP_TIMEOUT,
    )
    if resp.status_code != 200:
        raise OAuthError("Could not read your Google profile. Please try again.")
    data = resp.json()
    return {
        "provider_id": str(data["sub"]),
        "email": data.get("email"),
        # Google only returns an email it has itself verified ownership of.
        "email_verified": bool(data.get("email_verified")),
        "name": data.get("name") or (data.get("email") or "Google User").split("@")[0],
    }


def exchange_github_code(code: str) -> dict:
    resp = httpx.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "code": code,
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "redirect_uri": github_redirect_uri(),
        },
        timeout=HTTP_TIMEOUT,
    )
    if resp.status_code != 200:
        raise OAuthError("GitHub did not accept that login attempt. Please try again.")
    payload = resp.json()
    if "access_token" not in payload:
        raise OAuthError(payload.get("error_description") or "GitHub login failed. Please try again.")
    return payload


def fetch_github_profile(access_token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }
    user_resp = httpx.get(GITHUB_USER_URL, headers=headers, timeout=HTTP_TIMEOUT)
    if user_resp.status_code != 200:
        raise OAuthError("Could not read your GitHub profile. Please try again.")
    user = user_resp.json()

    # GitHub users can keep their email private, so the profile's own `email`
    # field may be null. The emails endpoint (needs the user:email scope we
    # requested) tells us which address, if any, GitHub has verified.
    email = user.get("email")
    email_verified = False
    emails_resp = httpx.get(GITHUB_EMAILS_URL, headers=headers, timeout=HTTP_TIMEOUT)
    if emails_resp.status_code == 200:
        entries = emails_resp.json()
        primary = next((e for e in entries if e.get("primary") and e.get("verified")), None)
        verified = primary or next((e for e in entries if e.get("verified")), None)
        if verified:
            email, email_verified = verified["email"], True

    if not email:
        raise OAuthError(
            "Your GitHub account has no email address we can use to sign you in. "
            "Verify an email on GitHub and try again."
        )

    return {
        "provider_id": str(user["id"]),
        "email": email,
        "email_verified": email_verified,
        "name": user.get("name") or user.get("login") or "GitHub User",
    }


def find_or_create_oauth_user(db: Session, provider: str, profile: dict) -> User:
    provider_id = profile["provider_id"]
    email = (profile.get("email") or "").strip().lower()
    if not email:
        raise OAuthError("Your account has no email address we can use to sign you in.")

    user = (
        db.query(User)
        .filter(User.oauth_provider == provider, User.oauth_provider_id == provider_id)
        .first()
    )
    if user:
        return user

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        if existing.oauth_provider and existing.oauth_provider != provider:
            raise OAuthError(
                "This email is already linked to a different sign-in method. "
                "Please use that method to log in."
            )
        if not profile.get("email_verified"):
            # Email strings matching isn't proof of ownership on its own - only link
            # accounts when the provider itself has verified the address.
            raise OAuthError(
                "An account with this email already exists. Please log in with your "
                "password instead."
            )
        existing.oauth_provider = provider
        existing.oauth_provider_id = provider_id
        db.commit()
        db.refresh(existing)
        return existing

    user = User(
        name=profile.get("name") or "New User",
        email=email,
        password_hash=None,
        role=UserRole.user,
        oauth_provider=provider,
        oauth_provider_id=provider_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _hash_code(raw_code: str) -> str:
    return hashlib.sha256(raw_code.encode()).hexdigest()


def create_login_code(db: Session, user: User) -> str:
    """Mints a one-time code the OAuth callback can hand to the browser in a
    redirect. The code is NOT a session credential by itself - it only lets
    the holder call /api/auth/oauth/exchange once, within LOGIN_CODE_TTL_SECONDS,
    to receive the real JWT. This keeps the access token itself out of the URL.
    """
    raw_code = secrets.token_urlsafe(32)
    db.add(
        OAuthLoginCode(
            code_hash=_hash_code(raw_code),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=LOGIN_CODE_TTL_SECONDS),
        )
    )
    db.commit()
    return raw_code


def consume_login_code(db: Session, raw_code: str) -> Optional[User]:
    """Redeems a one-time login code, returning the user it was issued for.
    The backing row is deleted whether or not it was still valid, so a code
    can never be used twice (and expired rows don't pile up over time).
    """
    now = datetime.now(timezone.utc)
    db.query(OAuthLoginCode).filter(OAuthLoginCode.expires_at < now).delete()

    row = db.query(OAuthLoginCode).filter(OAuthLoginCode.code_hash == _hash_code(raw_code)).first()
    if not row:
        db.commit()
        return None

    user = db.query(User).filter(User.id == row.user_id).first()
    db.delete(row)
    db.commit()
    return user
