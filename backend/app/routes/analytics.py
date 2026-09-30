from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database.database import get_db
from app.models.user import User
from app.schemas.visitor import VisitCreate
from app.services import analytics_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/visit", status_code=201)
def record_visit(payload: VisitCreate, request: Request, db: Session = Depends(get_db)):
    visitor = analytics_service.record_visit(
        db,
        payload,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    return success_response({"id": visitor.id}, "Visit recorded", status_code=201)


@router.get("")
def get_analytics(db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    overview = analytics_service.get_overview(db)
    return success_response(overview, "Analytics retrieved")
