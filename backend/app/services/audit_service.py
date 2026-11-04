from sqlalchemy.orm import Session

from app.models.admin_audit_log import AdminAuditLog


def record(
    db: Session,
    *,
    admin_id: int,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    outcome: str = "success",
) -> AdminAuditLog:
    entry = AdminAuditLog(
        admin_id=admin_id, action=action, target_type=target_type, target_id=target_id, outcome=outcome
    )
    db.add(entry)
    db.commit()
    return entry
