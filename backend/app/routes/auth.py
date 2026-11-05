import hmac
import logging
import secrets
from urllib.parse import quote, urlparse

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.dependencies import SESSION_COOKIE, CurrentUser, get_current_user, verify_csrf
from app.core.rate_limit import limiter
from app.core.security import create_session_token, sign_oauth_state, verify_oauth_state
from app.schemas.user import MeOut
from app.services import oauth_service
from app.utils.helpers import api_error, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

OAUTH_STATE_COOKIE = "oauth_state"
OAUTH_STATE_MAX_AGE = 600  # 10 minutes to complete the provider's consent screen


# ---------------------------------------------------------------------------
# Google / GitHub OAuth - the only login methods. There is no database: no
# password login, no user table. A successful login issues a signed, stateless
# session cookie whose claims (email/name/role/provider) are trusted as-is on
# every later request - nothing is looked up server-side. "role" is decided
# once, right here, by comparing the provider-verified email against
# ADMIN_EMAIL; it is never re-derived from anywhere else.
#
# The frontend's "Continue with Google/GitHub" buttons navigate the whole page
# to the /login route below (not a fetch() call - the provider's consent
# screen can't be shown inside an XHR). The browser ends up back on /callback,
# which sets the session cookie directly on its redirect response and sends
# the browser to the frontend with just `?oauth=success` (or `?oauth_error=...`
# on failure) - no code or token ever appears in a URL, browser history, or
# Referer header.
# ---------------------------------------------------------------------------


def _is_secure_backend() -> bool:
    return urlparse(settings.backend_url).scheme == "https"


def _cookie_kwargs() -> dict:
    # Frontend (Vercel) and backend (Render) are different origins in
    # production, so the session cookie must be SameSite=None to be sent on
    # cross-site fetch() calls - which in turn requires Secure=True (browsers
    # reject SameSite=None without it). Locally both run on localhost (same
    # registrable domain, different port), which is same-site, so Lax +
    # non-secure works for http development.
    secure = _is_secure_backend()
    return {"httponly": True, "secure": secure, "samesite": "none" if secure else "lax"}


def _validated_redirect_base(redirect: str | None) -> str:
    allowed = settings.frontend_origins
    fallback = allowed[0] if allowed else settings.frontend_url.rstrip("/")
    if not redirect:
        return fallback
    parsed = urlparse(redirect)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return origin if origin in allowed else fallback


def _start_oauth(provider: str, redirect: str | None) -> RedirectResponse:
    if not oauth_service.oauth_configured(provider):
        raise api_error(f"{provider.capitalize()} login is not configured on this server", status_code=503)

    redirect_base = _validated_redirect_base(redirect)
    state = sign_oauth_state(
        {"nonce": secrets.token_urlsafe(16), "provider": provider, "redirect": redirect_base}
    )
    authorize_url = (
        oauth_service.build_google_authorize_url(state)
        if provider == "google"
        else oauth_service.build_github_authorize_url(state)
    )

    response = RedirectResponse(authorize_url, status_code=302)
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=OAUTH_STATE_MAX_AGE,
        **_cookie_kwargs(),
    )
    return response


def _finish_oauth(
    request: Request,
    provider: str,
    code: str | None,
    state: str | None,
    error: str | None,
) -> RedirectResponse:
    fallback_redirect = settings.frontend_origins[0] if settings.frontend_origins else settings.frontend_url.rstrip("/")

    def error_redirect(message: str, redirect_base: str = fallback_redirect) -> RedirectResponse:
        response = RedirectResponse(f"{redirect_base}/?oauth_error={quote(message)}", status_code=302)
        response.delete_cookie(OAUTH_STATE_COOKIE)
        return response

    if error:
        return error_redirect("Login was cancelled.")

    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)
    # The state must match the cookie set when the flow started on this same
    # browser - this is what actually stops an attacker from replaying a
    # captured callback URL into a victim's session (CSRF), not just the signature.
    if not code or not state or not cookie_state or not hmac.compare_digest(state, cookie_state):
        return error_redirect("Your login session expired or is invalid. Please try again.")

    try:
        payload = verify_oauth_state(state, max_age_seconds=OAUTH_STATE_MAX_AGE)
    except ValueError:
        return error_redirect("Your login session expired. Please try again.")

    if payload.get("provider") != provider:
        return error_redirect("Invalid login session. Please try again.")

    redirect_base = _validated_redirect_base(payload.get("redirect"))

    try:
        if provider == "google":
            token_data = oauth_service.exchange_google_code(code)
            profile = oauth_service.fetch_google_profile(token_data["access_token"])
        else:
            token_data = oauth_service.exchange_github_code(code)
            profile = oauth_service.fetch_github_profile(token_data["access_token"])
    except oauth_service.OAuthError as exc:
        return error_redirect(str(exc), redirect_base)
    except Exception:
        logger.exception("OAuth callback failed for provider %s", provider)
        return error_redirect("Something went wrong during login. Please try again.", redirect_base)

    email = (profile.get("email") or "").strip().lower()
    if not email:
        return error_redirect("Your account has no email address we can use to sign you in.", redirect_base)
    if not profile.get("email_verified"):
        # Never grant access on an unverified email - a string match isn't proof
        # of ownership, only the provider's own verification is.
        return error_redirect(
            "Your email on this provider isn't verified. Verify it and try again.", redirect_base
        )

    role = "admin" if email == settings.admin_email.strip().lower() else "user"
    session_token, _ = create_session_token(
        email=email, name=profile.get("name") or email, role=role, provider=provider
    )

    response = RedirectResponse(f"{redirect_base}/?oauth=success", status_code=302)
    response.delete_cookie(OAUTH_STATE_COOKIE)
    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        max_age=settings.session_max_age_minutes * 60,
        **_cookie_kwargs(),
    )
    return response


@router.get("/google/login")
@limiter.limit("10/minute")
def google_login(request: Request, redirect: str | None = None):
    return _start_oauth("google", redirect)


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    return _finish_oauth(request, "google", code, state, error)


@router.get("/github/login")
@limiter.limit("10/minute")
def github_login(request: Request, redirect: str | None = None):
    return _start_oauth("github", redirect)


@router.get("/github/callback")
def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    return _finish_oauth(request, "github", code, state, error)


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)):
    return success_response(
        MeOut(
            email=current_user.email,
            name=current_user.name,
            role=current_user.role,
            provider=current_user.provider,
            csrf_token=current_user.csrf,
        ),
        "Current user",
    )


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout():
    # JWTs are otherwise stateless; there is no server-side revocation list.
    # This only clears the browser's copy of the cookie.
    response = success_response(None, "Logged out successfully")
    response.delete_cookie(SESSION_COOKIE)
    return response
