import hmac
import logging
import secrets
from urllib.parse import quote, urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, oauth2_scheme
from app.core.rate_limit import get_client_ip, limiter
from app.core.security import decode_access_token, sign_oauth_state, verify_oauth_state
from app.database.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import OAuthExchangeRequest, Token, UserLogin, UserOut, UserRegister
from app.services import audit_service, auth_event_service, oauth_service
from app.services.auth_service import authenticate_user, issue_token, register_user
from app.utils.helpers import api_error, success_response

logger = logging.getLogger(__name__)


def _sid_from_token(token_str: str) -> str | None:
    try:
        return decode_access_token(token_str).get("sid")
    except ValueError:
        return None

router = APIRouter(prefix="/api/auth", tags=["auth"])

OAUTH_STATE_COOKIE = "oauth_state"
OAUTH_STATE_MAX_AGE = 600  # 10 minutes to complete the provider's consent screen


@router.post("/register")
def register(request: Request, payload: UserRegister, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent")
    ip = get_client_ip(request)
    try:
        user = register_user(db, payload)
    except HTTPException as exc:
        # Only a reliably-identified outcome (the email is already taken) is
        # worth recording as a failed signup - a 422 never reaches here, since
        # FastAPI rejects a malformed payload before this function runs.
        if exc.status_code == 409:
            auth_event_service.record_event(
                db, method="password", event_type="signup", status="failure",
                email=payload.email, reason="email_already_registered",
                user_agent=ua, ip=ip,
            )
        raise

    auth_event_service.record_event(
        db, method="password", event_type="signup", status="success",
        user=user, user_agent=ua, ip=ip,
    )
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
    ua = request.headers.get("user-agent")
    ip = get_client_ip(request)
    try:
        user = authenticate_user(db, payload)
    except HTTPException as exc:
        auth_event_service.record_event(
            db, method="password", event_type="login", status="failure",
            email=payload.email,
            reason="account_disabled" if exc.status_code == 403 else "invalid_credentials",
            user_agent=ua, ip=ip,
        )
        raise

    access_token = issue_token(user)
    auth_event_service.record_event(
        db, method="password", event_type="login", status="success",
        user=user, session_ref=_sid_from_token(access_token), user_agent=ua, ip=ip,
    )
    if user.role == UserRole.admin:
        audit_service.record(db, admin_id=user.id, action="admin_login")
    return success_response(
        Token(access_token=access_token).model_dump(),
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
    ua = request.headers.get("user-agent")
    ip = get_client_ip(request)
    try:
        user = authenticate_user(db, payload)
    except HTTPException as exc:
        auth_event_service.record_event(
            db, method="password", event_type="login", status="failure",
            email=payload.email,
            reason="account_disabled" if exc.status_code == 403 else "invalid_credentials",
            user_agent=ua, ip=ip,
        )
        raise

    access_token = issue_token(user)
    auth_event_service.record_event(
        db, method="password", event_type="login", status="success",
        user=user, session_ref=_sid_from_token(access_token), user_agent=ua, ip=ip,
    )
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
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    raw_token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    auth_event_service.record_event(
        db,
        method=auth_event_service.infer_method(current_user),
        event_type="logout",
        status="success",
        user=current_user,
        session_ref=_sid_from_token(raw_token),
        user_agent=request.headers.get("user-agent"),
        ip=get_client_ip(request),
    )
    # JWTs are otherwise stateless; the client discards the token. This only
    # records that the event happened, it doesn't revoke the token itself.
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
    ua = request.headers.get("user-agent")
    ip = get_client_ip(request)
    profile: dict | None = None

    try:
        if provider == "google":
            token_data = oauth_service.exchange_google_code(code)
            profile = oauth_service.fetch_google_profile(token_data["access_token"])
        else:
            token_data = oauth_service.exchange_github_code(code)
            profile = oauth_service.fetch_github_profile(token_data["access_token"])
        user, created = oauth_service.find_or_create_oauth_user(db, provider, profile)
    except oauth_service.OAuthError as exc:
        # Reliably identifiable: the provider rejected the code, or the
        # account-linking policy refused this attempt. Login, not signup -
        # nothing was ever created, so there's no signup to log as failed.
        auth_event_service.record_event(
            db, method=provider, event_type="login", status="failure",
            email=(profile or {}).get("email"), reason="oauth_error",
            user_agent=ua, ip=ip,
        )
        return error_redirect(str(exc), redirect_base)
    except Exception:
        logger.exception("OAuth callback failed for provider %s", provider)
        auth_event_service.record_event(
            db, method=provider, event_type="login", status="failure",
            email=(profile or {}).get("email"), reason="provider_error",
            user_agent=ua, ip=ip,
        )
        return error_redirect("Something went wrong during login. Please try again.", redirect_base)

    if created:
        # The account row was just inserted - this is the one, authoritative
        # point a signup is recorded. A retried/duplicated callback for the
        # same provider identity lands in the `if user:` branch above instead
        # (created=False), so it can never double-count a signup.
        auth_event_service.record_event(
            db, method=provider, event_type="signup", status="success",
            user=user, user_agent=ua, ip=ip,
        )

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
        # Not reliably attributable to any account (the code is simply gone by
        # now, e.g. the visitor abandoned the flow) - not worth recording as a
        # failed login, that would conflate an expired code with a rejected one.
        raise api_error("That login code is invalid or has expired. Please log in again.", status_code=400)

    ua = request.headers.get("user-agent")
    ip = get_client_ip(request)
    if not user.is_active:
        auth_event_service.record_event(
            db, method=auth_event_service.infer_method(user), event_type="login", status="failure",
            user=user, reason="account_disabled", user_agent=ua, ip=ip,
        )
        raise api_error("This account has been disabled.", status_code=403)

    access_token = issue_token(user)
    auth_event_service.record_event(
        db, method=auth_event_service.infer_method(user), event_type="login", status="success",
        user=user, session_ref=_sid_from_token(access_token), user_agent=ua, ip=ip,
    )
    token = Token(access_token=access_token)
    return success_response(token.model_dump(), "Login successful")