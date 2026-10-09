from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AuthEvent(Base):
    """An append-only record of a single authentication-related event
    (signup / login / logout), used only for the admin "User Activity &
    Reports" dashboard. Never stores a password, hash, token, or OAuth
    secret - see the reason/session_ref fields below.
    """

    __tablename__ = "auth_events"
    __table_args__ = (
        Index("ix_auth_events_user_id_created_at", "user_id", "created_at"),
        Index("ix_auth_events_event_type_created_at", "event_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Nullable: a failed login/signup attempt may have no matching account.
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # The email the attempt was associated with, independent of whether it
    # resolved to a real account - lets a failed login still be reported.
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # "password" / "google" / "github"
    method: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # "signup" / "login" / "logout"
    event_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # "success" / "failure"
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # A short, safe category - e.g. "invalid_credentials", "email_already_registered",
    # "provider_error". Never a stack trace, never provider error payloads verbatim.
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Random per-login identifier (the JWT's "sid" claim), not a secret itself and
    # not sufficient to authenticate anything - lets a login/logout pair be
    # correlated in the activity timeline without storing the token.
    session_ref: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
