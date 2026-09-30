import hashlib

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.certificate import Certificate
from app.models.contact import ContactMessage, ContactStatus
from app.models.project import Project
from app.models.visitor import Visitor
from app.schemas.visitor import VisitCreate


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256((ip + settings.secret_key).encode("utf-8")).hexdigest()[:32]


def record_visit(
    db: Session, payload: VisitCreate, user_agent: str | None, ip: str | None
) -> Visitor:
    visitor = Visitor(
        session_id=payload.session_id,
        page=payload.page,
        referrer=payload.referrer,
        user_agent=user_agent,
        ip_hash=hash_ip(ip),
    )
    db.add(visitor)
    db.commit()
    db.refresh(visitor)
    return visitor


def get_overview(db: Session) -> dict:
    top_pages_rows = (
        db.query(Visitor.page, func.count(Visitor.id).label("visits"))
        .group_by(Visitor.page)
        .order_by(func.count(Visitor.id).desc())
        .limit(10)
        .all()
    )
    return {
        "total_projects": db.query(Project).count(),
        "total_certificates": db.query(Certificate).count(),
        "total_messages": db.query(ContactMessage).count(),
        "unread_messages": db.query(ContactMessage)
        .filter(ContactMessage.status == ContactStatus.unread)
        .count(),
        "total_visitors": db.query(Visitor).count(),
        "unique_sessions": db.query(Visitor.session_id).distinct().count(),
        "top_pages": [{"page": page, "visits": visits} for page, visits in top_pages_rows],
    }
