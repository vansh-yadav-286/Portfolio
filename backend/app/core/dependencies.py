from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status

from app.core.security import decode_session_token

SESSION_COOKIE = "session"

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
)


@dataclass(frozen=True)
class CurrentUser:
    """The authenticated visitor, derived entirely from the signed session
    cookie's claims - there is no database row behind this. `role` was decided
    once, at OAuth callback time, by comparing the verified email against
    ADMIN_EMAIL (see routes/auth.py); it is not re-checked against anything else.
    """

    email: str
    name: str
    role: str
    provider: str
    csrf: str


def get_current_user(request: Request) -> CurrentUser:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise credentials_exception
    try:
        payload = decode_session_token(token)
    except ValueError:
        raise credentials_exception
    email = payload.get("sub")
    if not email:
        raise credentials_exception
    return CurrentUser(
        email=email,
        name=payload.get("name") or email,
        role=payload.get("role") or "user",
        provider=payload.get("provider") or "",
        csrf=payload.get("csrf") or "",
    )


def get_current_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user


def verify_csrf(request: Request, current_user: CurrentUser = Depends(get_current_user)) -> None:
    """Required on every state-changing admin request. The session cookie is
    HttpOnly and sent cross-site (SameSite=None, since the frontend and backend
    are different origins), which on its own gives no CSRF protection - a
    malicious page could still trigger a request that carries it. The frontend
    gets this value once from GET /api/auth/me (never from the cookie, which it
    can't read) and must echo it back on every mutating request; a forged
    cross-site request has no way to read that response, so it can't supply it.
    """
    header_token = request.headers.get("x-csrf-token")
    if not header_token or not current_user.csrf or header_token != current_user.csrf:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing or invalid CSRF token")
