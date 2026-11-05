import httpx

from app.core.config import settings

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
    from urllib.parse import urlencode

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
    from urllib.parse import urlencode

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
