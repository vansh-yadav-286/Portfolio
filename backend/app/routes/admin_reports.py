import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database.database import get_db
from app.models.user import User
from app.schemas.reports import UserStatusUpdate
from app.services import audit_service, reports_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/admin/reports", tags=["admin-reports"])


@router.get("/overview")
def overview(
    period: str = Query("today", pattern="^(today|7d|30d|custom)$"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    data = reports_service.get_overview(db, period, date_from, date_to)
    return success_response(data, "Overview retrieved")


@router.get("/users")
def list_users(
    q: str | None = None,
    provider: str | None = Query(None, pattern="^(password|google|github)$"),
    status: str | None = Query(None, pattern="^(active|disabled)$"),
    verified: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: str = "created_at",
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(reports_service.PAGE_SIZE_DEFAULT, ge=1, le=reports_service.PAGE_SIZE_MAX),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    items, total = reports_service.list_users(
        db, q=q, provider=provider, status=status, verified=verified,
        date_from=date_from, date_to=date_to, sort=sort, order=order, page=page, page_size=page_size,
    )
    return success_response(
        {"items": items, "total": total, "page": page, "page_size": page_size}, "Users retrieved"
    )


@router.patch("/users/{user_id}/status")
def change_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = reports_service.update_user_status(db, user_id, payload.is_active)
    audit_service.record(
        db, admin_id=admin.id, action="change_account_status", target_type="user", target_id=user_id
    )
    return success_response(
        {"id": user.id, "is_active": user.is_active}, "Account status updated"
    )


@router.get("/users/{user_id}/activity")
def user_activity(
    user_id: int,
    event_type: str | None = Query(None, pattern="^(signup|login|logout)$"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(reports_service.PAGE_SIZE_DEFAULT, ge=1, le=reports_service.PAGE_SIZE_MAX),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    data = reports_service.get_user_activity(
        db, user_id, event_type=event_type, date_from=date_from, date_to=date_to, page=page, page_size=page_size
    )
    return success_response(data, "User activity retrieved")


@router.get("/signups")
def signups(
    method: str | None = Query(None, pattern="^(password|google|github)$"),
    status: str | None = Query(None, pattern="^(success|failure)$"),
    q: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: str = "created_at",
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(reports_service.PAGE_SIZE_DEFAULT, ge=1, le=reports_service.PAGE_SIZE_MAX),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    items, total = reports_service.list_auth_events(
        db, event_type="signup", method=method, status=status, user_id=None, q=q,
        date_from=date_from, date_to=date_to, sort=sort, order=order, page=page, page_size=page_size,
    )
    return success_response(
        {"items": items, "total": total, "page": page, "page_size": page_size}, "Signup history retrieved"
    )


@router.get("/auth-events")
def auth_events(
    event_type: str | None = Query(None, pattern="^(signup|login|logout)$"),
    method: str | None = Query(None, pattern="^(password|google|github)$"),
    status: str | None = Query(None, pattern="^(success|failure)$"),
    user_id: int | None = None,
    q: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: str = "created_at",
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(reports_service.PAGE_SIZE_DEFAULT, ge=1, le=reports_service.PAGE_SIZE_MAX),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    items, total = reports_service.list_auth_events(
        db, event_type=event_type, method=method, status=status, user_id=user_id, q=q,
        date_from=date_from, date_to=date_to, sort=sort, order=order, page=page, page_size=page_size,
    )
    return success_response(
        {"items": items, "total": total, "page": page, "page_size": page_size}, "Authentication history retrieved"
    )


@router.get("/failed-logins")
def failed_logins(
    method: str | None = Query(None, pattern="^(password|google|github)$"),
    user_id: int | None = None,
    q: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(reports_service.PAGE_SIZE_DEFAULT, ge=1, le=reports_service.PAGE_SIZE_MAX),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    items, total = reports_service.list_auth_events(
        db, event_type="login", method=method, status="failure", user_id=user_id, q=q,
        date_from=date_from, date_to=date_to, sort="created_at", order=order, page=page, page_size=page_size,
    )
    return success_response(
        {"items": items, "total": total, "page": page, "page_size": page_size}, "Failed login attempts retrieved"
    )


@router.get("/visits")
def visits(
    page_filter: str | None = None,
    session_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: str = "visited_at",
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(reports_service.PAGE_SIZE_DEFAULT, ge=1, le=reports_service.PAGE_SIZE_MAX),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    items, total = reports_service.list_visits(
        db, page_filter=page_filter, session_id=session_id, date_from=date_from, date_to=date_to,
        sort=sort, order=order, page=page, page_size=page_size,
    )
    return success_response(
        {"items": items, "total": total, "page": page, "page_size": page_size}, "Visitor analytics retrieved"
    )


def _csv_safe(value) -> str:
    text = "" if value is None else str(value)
    # Spreadsheet formula-injection guard: a cell a user-controlled field could
    # make start with =, +, -, or @ gets neutralized when opened in Excel/Sheets.
    if text and text[0] in ("=", "+", "-", "@"):
        return "'" + text
    return text


@router.get("/export")
def export(
    report: str = Query(..., pattern="^(users|signups|auth-events|failed-logins|visits)$"),
    q: str | None = None,
    method: str | None = Query(None, pattern="^(password|google|github)$"),
    status: str | None = None,
    event_type: str | None = Query(None, pattern="^(signup|login|logout)$"),
    user_id: int | None = None,
    provider: str | None = Query(None, pattern="^(password|google|github)$"),
    verified: bool | None = None,
    session_id: str | None = None,
    page_filter: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: str = "created_at",
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    fieldnames, rows = reports_service.get_export_rows(
        db, report, q=q, method=method, status=status, event_type=event_type, user_id=user_id,
        provider=provider, verified=verified, session_id=session_id, page_filter=page_filter,
        date_from=date_from, date_to=date_to, sort=sort, order=order,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(fieldnames)
    for row in rows:
        writer.writerow([_csv_safe(row.get(field)) for field in fieldnames])
    buffer.seek(0)

    audit_service.record(db, admin_id=admin.id, action=f"export_csv:{report}", target_type="report")

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    # report name is constrained to the fixed pattern above, so this is already
    # a safe filename - no further sanitization needed.
    filename = f"{report}-{timestamp}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
