import hmac
import logging
import secrets
from urllib.parse import quote, urlparse

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.core.security import sign_oauth_state, verify_oauth_state
from app.database.database import get_db
from app.models.user import User
from app.schemas.user import OAuthExchangeRequest, Token, UserLogin, UserOut, UserRegister
from app.services import oauth_service
from app.services.auth_service import authenticate_user, issue_token, register_user
from app.utils.helpers import api_error, success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

OAUTH_STATE_COOKIE = "oauth_state"
OAUTH_STATE_MAX_AGE = 600  # 10 minutes to complete the provider's consent screen


@router.post("/register")
def register(payload: UserRegister, db: Session = Depends(get_db)):
    user = register_user(db, payload)
    return success_response(
        UserOut.model_validate(user),
        "Account created successfully",
        status_code=201,
    )


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, payload)
    token = Token(access_token=issue_token(user))

    return success_response(
        token.model_dump(),
        "Login successful",
    )


@router.post("/token")
@limiter.limit("5/minute")
def token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    payload = UserLogin(
        email=form_data.username,
        password=form_data.password,
    )

    user = authenticate_user(db, payload)
    access_token = issue_token(user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return success_response(
        UserOut.model_validate(current_user),
        "Current user",
    )


@router.post("/logout")
def logout():
    # JWTs are stateless; the client discards the token.
    # Documented here for API completeness / a future token-blacklist
    # if one becomes necessary.
    return success_response(None, "Logged out successfully")


# ---------------------------------------------------------------------------
# Google / GitHub OAuth
#
# The frontend's "Continue with Google/GitHub" buttons navigate the whole
# page to the /login route below (not a fetch() call - the provider's
# consent screen can't be shown inside an XHR). The browser ends up back on
# /callback, which redirects to the frontend with either ?oauth_error=<message>
# or ?oauth=success&code=<one-time code>.
#
# That code is deliberately NOT the access token, and the redirect carries no
# email/identity claim for the frontend to trust - the frontend must POST the
# code to /oauth/exchange below, which looks it up server-side and only then
# returns a real JWT, identical in shape to what /api/auth/login returns.
# Putting the JWT itself in a URL would leak it into browser history, the
# Referer header and both hosts' access logs; this way the only thing exposed
# there is a 60-second, single-use code that is worthless once redeemed.
# ---------------------------------------------------------------------------


def _is_secure_backend() -> bool:
    return urlparse(settings.backend_url).scheme == "https"


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
        httponly=True,
        secure=_is_secure_backend(),
        samesite="lax",
    )
    return response


def _finish_oauth(
    request: Request,
    provider: str,
    code: str | None,
    state: str | None,
    error: str | None,
    db: Session,
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
        user = oauth_service.find_or_create_oauth_user(db, provider, profile)
    except oauth_service.OAuthError as exc:
        return error_redirect(str(exc), redirect_base)
    except Exception:
        logger.exception("OAuth callback failed for provider %s", provider)
        return error_redirect("Something went wrong during login. Please try again.", redirect_base)

    login_code = oauth_service.create_login_code(db, user)
    response = RedirectResponse(f"{redirect_base}/?oauth=success&code={quote(login_code)}", status_code=302)
    response.delete_cookie(OAUTH_STATE_COOKIE)
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
    db: Session = Depends(get_db),
):
    return _finish_oauth(request, "google", code, state, error, db)


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
    db: Session = Depends(get_db),
):
    return _finish_oauth(request, "github", code, state, error, db)


@router.post("/oauth/exchange")
@limiter.limit("10/minute")
def oauth_exchange(request: Request, payload: OAuthExchangeRequest, db: Session = Depends(get_db)):
    user = oauth_service.consume_login_code(db, payload.code)
    if not user:
        raise api_error("That login code is invalid or has expired. Please log in again.", status_code=400)

    token = Token(access_token=issue_token(user))
    return success_response(token.model_dump(), "Login successful")