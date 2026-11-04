from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class OAuthLoginCode(Base):
    """A short-lived, single-use code handed to the browser in the OAuth
    callback redirect so it can fetch its real JWT via POST /api/auth/oauth/exchange.
    The code itself grants nothing beyond "fetch the token for the user it
    points to, once" - it is deleted the moment it's redeemed or expires.
    """

    __tablename__ = "oauth_login_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
