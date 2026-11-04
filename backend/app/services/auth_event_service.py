from sqlalchemy.orm import Session

from app.models.auth_event import AuthEvent
from app.models.user import User
from app.services.analytics_service import hash_ip

# Keeps the raw user-agent string capped; no attempt at a full UA parse here -
# see reports_service.parse_user_agent for the display-time best-effort split.
USER_AGENT_MAX_LEN = 300


def infer_method(user: User) -> str:
    return user.oauth_provider or "password"


def record_event(
    db: Session,
    *,
    method: str,
    event_type: str,
    status: str,
    user: User | None = None,
    email: str | None = None,
    reason: str | None = None,
    session_ref: str | None = None,
    user_agent: str | None = None,
    ip: str | None = None,
) -> AuthEvent:
    """Appends one row to auth_events. Never pass a password, token, or OAuth
    secret in `reason` - it's meant for short, safe categories like
    "invalid_credentials", not raw provider error payloads.
    """
    event = AuthEvent(
        user_id=user.id if user else None,
        email=(email or (user.email if user else None)),
        method=method,
        event_type=event_type,
        status=status,
        reason=reason,
        session_ref=session_ref,
        user_agent=(user_agent[:USER_AGENT_MAX_LEN] if user_agent else None),
        ip_hash=hash_ip(ip),
    )
    db.add(event)
    db.commit()
    return event
