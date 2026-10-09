import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint(
            "oauth_provider", "oauth_provider_id", name="uq_users_oauth_provider_identity"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # Null for accounts created through Google/GitHub OAuth, which have no password.
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # "google" / "github" / None for password-only accounts.
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    oauth_provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # True for OAuth accounts, since the provider already verified ownership of the
    # email at signup. False for password accounts - this app has no email
    # verification flow for those, so it would be dishonest to default it True.
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Admin-controlled kill switch (see PATCH /api/admin/reports/users/{id}/status).
    # Enforced in auth_service.authenticate_user, the OAuth exchange route, and
    # get_current_user, so a disabled account can neither log in again nor keep
    # using a token it already holds.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.user
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
