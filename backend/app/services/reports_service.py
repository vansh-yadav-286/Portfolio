"""Query logic behind the admin "User Activity & Reports" dashboard.

Every function here is read-only except update_user_status. Nothing in this
file ever returns a password, password hash, JWT, OAuth token, or OAuth
client secret - see AuthEvent's own docstring for what it deliberately
doesn't store in the first place.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.auth_event import AuthEvent
from app.models.user import User
from app.models.visitor import Visitor
from app.utils.helpers import api_error

PAGE_SIZE_DEFAULT = 25
PAGE_SIZE_MAX = 100
MAX_EXPORT_ROWS = 10000

USER_SORT_COLUMNS = {
    "created_at": User.created_at,
    "name": User.name,
    "email": User.email,
}
EVENT_SORT_COLUMNS = {
    "created_at": AuthEvent.created_at,
}
VISIT_SORT_COLUMNS = {
    "visited_at": Visitor.visited_at,
    "page": Visitor.page,
}


def paginate(page: int, page_size: int) -> tuple[int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), PAGE_SIZE_MAX)
    return page, page_size


def parse_date_range(date_from: datetime | None, date_to: datetime | None) -> tuple[datetime | None, datetime | None]:
    if date_from and date_to and date_from > date_to:
        raise api_error("date_from must not be after date_to", status_code=400)
    return date_from, date_to


def _period_bounds(period: str, date_from: datetime | None, date_to: datetime | None) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today":
        return today_start, now
    if period == "7d":
        return now - timedelta(days=7), now
    if period == "30d":
        return now - timedelta(days=30), now
    if period == "custom":
        if not date_from or not date_to:
            raise api_error("date_from and date_to are required when period=custom", status_code=400)
        return date_from, date_to
    raise api_error("period must be one of: today, 7d, 30d, custom", status_code=400)


def _apply_order(query, sort_columns: dict, sort: str, order: str):
    column = sort_columns.get(sort) or next(iter(sort_columns.values()))
    return query.order_by(column.desc() if order != "asc" else column.asc())


# Best-effort only - not a substitute for a real UA-parsing library. Good
# enough to label a report row "Chrome / Windows" without a new dependency.
def parse_user_agent(user_agent: str | None) -> dict:
    if not user_agent:
        return {"browser": None, "os": None}
    ua = user_agent.lower()

    if "edg/" in ua:
        browser = "Edge"
    elif "firefox/" in ua:
        browser = "Firefox"
    elif "chrome/" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "safari/" in ua and "chrome/" not in ua:
        browser = "Safari"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    else:
        browser = "Other"

    if "windows" in ua:
        os_name = "Windows"
    elif "mac os x" in ua or "macintosh" in ua:
        os_name = "macOS"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        os_name = "iOS"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Other"

    return {"browser": browser, "os": os_name}


def serialize_auth_event(event: AuthEvent) -> dict:
    ua = parse_user_agent(event.user_agent)
    return {
        "id": event.id,
        "user_id": event.user_id,
        "email": event.email,
        "method": event.method,
        "event_type": event.event_type,
        "status": event.status,
        "reason": event.reason,
        "session_ref": event.session_ref,
        "browser": ua["browser"],
        "os": ua["os"],
        "created_at": event.created_at,
    }


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

def get_overview(db: Session, period: str, date_from: datetime | None, date_to: datetime | None) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    period_start, period_end = _period_bounds(period, date_from, date_to)

    def count_signups(since: datetime, until: datetime | None = None) -> int:
        q = db.query(func.count(AuthEvent.id)).filter(
            AuthEvent.event_type == "signup", AuthEvent.status == "success", AuthEvent.created_at >= since
        )
        if until:
            q = q.filter(AuthEvent.created_at <= until)
        return q.scalar() or 0

    def count_logins(status: str, since: datetime, until: datetime | None = None) -> int:
        q = db.query(func.count(AuthEvent.id)).filter(
            AuthEvent.event_type == "login", AuthEvent.status == status, AuthEvent.created_at >= since
        )
        if until:
            q = q.filter(AuthEvent.created_at <= until)
        return q.scalar() or 0

    def provider_breakdown(event_type: str) -> dict:
        rows = (
            db.query(AuthEvent.method, func.count(AuthEvent.id))
            .filter(AuthEvent.event_type == event_type, AuthEvent.status == "success")
            .group_by(AuthEvent.method)
            .all()
        )
        breakdown = {"password": 0, "google": 0, "github": 0}
        for method, count in rows:
            breakdown[method] = count
        return breakdown

    # "Active sessions" is an estimate, not a real session store: a login
    # whose token hasn't expired yet and that has no later logout recorded
    # with the same session_ref. A browser closed without clicking logout
    # will overcount here - this is disclosed in the API response itself
    # (see `active_sessions_note`) so the dashboard can show the same caveat.
    from app.core.config import settings

    token_window_start = now - timedelta(minutes=settings.access_token_expire_minutes)
    recent_logins = (
        db.query(AuthEvent.session_ref, AuthEvent.user_id)
        .filter(
            AuthEvent.event_type == "login",
            AuthEvent.status == "success",
            AuthEvent.created_at >= token_window_start,
            AuthEvent.session_ref.isnot(None),
        )
        .all()
    )
    recent_session_refs = {row.session_ref for row in recent_logins}
    logged_out_refs = set()
    if recent_session_refs:
        logged_out_refs = {
            row[0]
            for row in db.query(AuthEvent.session_ref)
            .filter(AuthEvent.event_type == "logout", AuthEvent.session_ref.in_(recent_session_refs))
            .all()
        }
    active_sessions = len(recent_session_refs - logged_out_refs)

    total_visitors = db.query(func.count(Visitor.id)).scalar() or 0
    unique_visitors_total = db.query(func.count(func.distinct(Visitor.session_id))).scalar() or 0
    unique_visitors_today = (
        db.query(func.count(func.distinct(Visitor.session_id)))
        .filter(Visitor.visited_at >= today_start)
        .scalar()
        or 0
    )
    period_page_views = (
        db.query(func.count(Visitor.id))
        .filter(Visitor.visited_at >= period_start, Visitor.visited_at <= period_end)
        .scalar()
        or 0
    )
    period_unique_visitors = (
        db.query(func.count(func.distinct(Visitor.session_id)))
        .filter(Visitor.visited_at >= period_start, Visitor.visited_at <= period_end)
        .scalar()
        or 0
    )
    period_signups = count_signups(period_start, period_end)
    period_logins_success = count_logins("success", period_start, period_end)
    period_logins_failed = count_logins("failure", period_start, period_end)

    return {
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "signups_today": count_signups(today_start),
        "signups_last_7_days": count_signups(week_start),
        "signups_last_30_days": count_signups(month_start),
        "logins_success_today": count_logins("success", today_start),
        "logins_failed_today": count_logins("failure", today_start),
        "active_sessions_estimate": active_sessions,
        "active_sessions_note": (
            "Estimated from logins within the current token lifetime that have no "
            "recorded logout yet - not a real session store, so a browser closed "
            "without logging out will still be counted until its token expires."
        ),
        "total_page_views": total_visitors,
        "unique_visitors_today": unique_visitors_today,
        "total_unique_visitors": unique_visitors_total,
        "registrations_by_provider": provider_breakdown("signup"),
        "logins_by_provider": provider_breakdown("login"),
        "period": {
            "name": period,
            "start": period_start,
            "end": period_end,
            "signups": period_signups,
            "logins_success": period_logins_success,
            "logins_failed": period_logins_failed,
            "page_views": period_page_views,
            "unique_visitors": period_unique_visitors,
        },
    }


# ---------------------------------------------------------------------------
# Registered users
# ---------------------------------------------------------------------------

def list_users(
    db: Session,
    *,
    q: str | None,
    provider: str | None,
    status: str | None,
    verified: bool | None,
    date_from: datetime | None,
    date_to: datetime | None,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    date_from, date_to = parse_date_range(date_from, date_to)
    page, page_size = paginate(page, page_size)

    last_login_subq = (
        db.query(AuthEvent.user_id, func.max(AuthEvent.created_at).label("last_login"))
        .filter(AuthEvent.event_type == "login", AuthEvent.status == "success")
        .group_by(AuthEvent.user_id)
        .subquery()
    )
    login_count_subq = (
        db.query(AuthEvent.user_id, func.count(AuthEvent.id).label("login_count"))
        .filter(AuthEvent.event_type == "login", AuthEvent.status == "success")
        .group_by(AuthEvent.user_id)
        .subquery()
    )
    last_activity_subq = (
        db.query(AuthEvent.user_id, func.max(AuthEvent.created_at).label("last_activity"))
        .group_by(AuthEvent.user_id)
        .subquery()
    )

    query = (
        db.query(
            User,
            last_login_subq.c.last_login,
            func.coalesce(login_count_subq.c.login_count, 0).label("login_count"),
            last_activity_subq.c.last_activity,
        )
        .outerjoin(last_login_subq, last_login_subq.c.user_id == User.id)
        .outerjoin(login_count_subq, login_count_subq.c.user_id == User.id)
        .outerjoin(last_activity_subq, last_activity_subq.c.user_id == User.id)
    )

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(User.name.ilike(like), User.email.ilike(like)))
    if provider:
        query = query.filter(User.oauth_provider == (None if provider == "password" else provider))
    if status == "active":
        query = query.filter(User.is_active.is_(True))
    elif status == "disabled":
        query = query.filter(User.is_active.is_(False))
    if verified is not None:
        query = query.filter(User.email_verified.is_(verified))
    if date_from:
        query = query.filter(User.created_at >= date_from)
    if date_to:
        query = query.filter(User.created_at <= date_to)

    total = query.order_by(None).count()
    sort_columns = {**USER_SORT_COLUMNS, "last_login": last_login_subq.c.last_login}
    query = _apply_order(query, sort_columns, sort, order)
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for user, last_login, login_count, last_activity in rows:
        items.append(
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "created_at": user.created_at,
                "registration_method": user.oauth_provider or "password",
                "role": user.role.value,
                "is_active": user.is_active,
                "email_verified": user.email_verified,
                "last_login": last_login,
                "login_count": login_count,
                "last_activity": last_activity or user.created_at,
            }
        )
    return items, total


def update_user_status(db: Session, user_id: int, is_active: bool) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise api_error("User not found", status_code=404)
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def get_user_activity(
    db: Session,
    user_id: int,
    *,
    event_type: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    page: int,
    page_size: int,
) -> dict:
    date_from, date_to = parse_date_range(date_from, date_to)
    page, page_size = paginate(page, page_size)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise api_error("User not found", status_code=404)

    query = db.query(AuthEvent).filter(AuthEvent.user_id == user_id)
    if event_type:
        query = query.filter(AuthEvent.event_type == event_type)
    if date_from:
        query = query.filter(AuthEvent.created_at >= date_from)
    if date_to:
        query = query.filter(AuthEvent.created_at <= date_to)

    total = query.count()
    rows = (
        query.order_by(AuthEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    timeline = [serialize_auth_event(e) for e in rows]
    # Account creation is always real (it's the user row's own timestamp) even
    # though no AuthEvent was recorded for signups that predate this feature.
    include_creation = page == 1 and not event_type and not date_from
    if include_creation:
        timeline.append(
            {
                "id": None,
                "user_id": user.id,
                "email": user.email,
                "method": user.oauth_provider or "password",
                "event_type": "account_created",
                "status": "success",
                "reason": None,
                "session_ref": None,
                "browser": None,
                "os": None,
                "created_at": user.created_at,
            }
        )

    return {
        "user": {"id": user.id, "name": user.name, "email": user.email, "created_at": user.created_at},
        "items": timeline,
        "total": total,
        "has_tracked_activity": total > 0,
        "note": (
            None
            if total > 0
            else "No activity has been recorded for this account yet. Activity tracking "
            "only covers events from when this feature was enabled onward - earlier "
            "logins and signups were never recorded and cannot be reconstructed."
        ),
    }


# ---------------------------------------------------------------------------
# Signup history / login history / failed logins (all AuthEvent-backed)
# ---------------------------------------------------------------------------

def list_auth_events(
    db: Session,
    *,
    event_type: str | None,
    method: str | None,
    status: str | None,
    user_id: int | None,
    q: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    date_from, date_to = parse_date_range(date_from, date_to)
    page, page_size = paginate(page, page_size)

    query = db.query(AuthEvent)
    if event_type:
        query = query.filter(AuthEvent.event_type == event_type)
    if method:
        query = query.filter(AuthEvent.method == method)
    if status:
        query = query.filter(AuthEvent.status == status)
    if user_id:
        query = query.filter(AuthEvent.user_id == user_id)
    if q:
        query = query.filter(AuthEvent.email.ilike(f"%{q.strip()}%"))
    if date_from:
        query = query.filter(AuthEvent.created_at >= date_from)
    if date_to:
        query = query.filter(AuthEvent.created_at <= date_to)

    total = query.count()
    query = _apply_order(query, EVENT_SORT_COLUMNS, sort, order)
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return [serialize_auth_event(e) for e in rows], total


# ---------------------------------------------------------------------------
# Visitor analytics
# ---------------------------------------------------------------------------

def list_visits(
    db: Session,
    *,
    page_filter: str | None,
    session_id: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    date_from, date_to = parse_date_range(date_from, date_to)
    page, page_size = paginate(page, page_size)

    query = db.query(Visitor)
    if page_filter:
        query = query.filter(Visitor.page.ilike(f"%{page_filter.strip()}%"))
    if session_id:
        query = query.filter(Visitor.session_id == session_id)
    if date_from:
        query = query.filter(Visitor.visited_at >= date_from)
    if date_to:
        query = query.filter(Visitor.visited_at <= date_to)

    total = query.count()
    query = _apply_order(query, VISIT_SORT_COLUMNS, sort, order)
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    # A session's first-ever row (lowest id for that session_id) is its first
    # visit; every later row from the same session_id is a "returning" view,
    # computed from existing data rather than a new column.
    session_ids = {r.session_id for r in rows}
    first_ids = {}
    if session_ids:
        first_id_rows = (
            db.query(Visitor.session_id, func.min(Visitor.id))
            .filter(Visitor.session_id.in_(session_ids))
            .group_by(Visitor.session_id)
            .all()
        )
        first_ids = dict(first_id_rows)

    items = []
    for row in rows:
        ua = parse_user_agent(row.user_agent)
        items.append(
            {
                "id": row.id,
                "session_id": row.session_id,
                "page": row.page,
                "referrer": row.referrer,
                "browser": ua["browser"],
                "os": ua["os"],
                "visited_at": row.visited_at,
                "is_returning_visit": first_ids.get(row.session_id) != row.id,
            }
        )
    return items, total


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

EXPORT_FIELDS = {
    "users": ["id", "name", "email", "created_at", "registration_method", "is_active", "email_verified", "last_login", "login_count"],
    "signups": ["id", "user_id", "email", "method", "status", "reason", "created_at"],
    "auth-events": ["id", "user_id", "email", "method", "event_type", "status", "reason", "browser", "os", "created_at"],
    "failed-logins": ["id", "user_id", "email", "method", "reason", "browser", "os", "created_at"],
    "visits": ["id", "session_id", "page", "referrer", "browser", "os", "visited_at", "is_returning_visit"],
}


def get_export_rows(
    db: Session,
    report: str,
    *,
    q: str | None = None,
    method: str | None = None,
    status: str | None = None,
    event_type: str | None = None,
    user_id: int | None = None,
    provider: str | None = None,
    verified: bool | None = None,
    session_id: str | None = None,
    page_filter: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: str = "created_at",
    order: str = "desc",
) -> tuple[list[str], list[dict]]:
    if report not in EXPORT_FIELDS:
        raise api_error("Unknown report type", status_code=400)
    page, page_size = 1, MAX_EXPORT_ROWS

    if report == "users":
        items, _ = list_users(
            db, q=q, provider=provider, status=status, verified=verified,
            date_from=date_from, date_to=date_to,
            sort=sort if sort in USER_SORT_COLUMNS else "created_at", order=order,
            page=page, page_size=page_size,
        )
    elif report == "signups":
        items, _ = list_auth_events(
            db, event_type="signup", method=method, status=status, user_id=user_id, q=q,
            date_from=date_from, date_to=date_to, sort="created_at", order=order,
            page=page, page_size=page_size,
        )
    elif report == "failed-logins":
        items, _ = list_auth_events(
            db, event_type="login", method=method, status="failure", user_id=user_id, q=q,
            date_from=date_from, date_to=date_to, sort="created_at", order=order,
            page=page, page_size=page_size,
        )
    elif report == "auth-events":
        items, _ = list_auth_events(
            db, event_type=event_type, method=method, status=status, user_id=user_id, q=q,
            date_from=date_from, date_to=date_to, sort="created_at", order=order,
            page=page, page_size=page_size,
        )
    else:  # visits
        items, _ = list_visits(
            db, page_filter=page_filter, session_id=session_id, date_from=date_from, date_to=date_to,
            sort=sort if sort in VISIT_SORT_COLUMNS else "visited_at", order=order,
            page=page, page_size=page_size,
        )

    return EXPORT_FIELDS[report], items
