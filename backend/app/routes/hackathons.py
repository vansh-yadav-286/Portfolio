from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database.database import get_db
from app.models.user import User
from app.schemas.hackathon import HackathonCreate, HackathonOut, HackathonUpdate
from app.services import hackathon_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/hackathons", tags=["hackathons"])


@router.get("")
def list_visible_hackathons(db: Session = Depends(get_db)):
    items = hackathon_service.list_public(db)
    return success_response([HackathonOut.model_validate(i) for i in items], "Hackathons retrieved")


@router.get("/manage")
def list_all_hackathons(db: Session = Depends(get_db), _admin: User = Depends(get_current_admin)):
    items = hackathon_service.list_all(db)
    return success_response([HackathonOut.model_validate(i) for i in items], "Hackathons retrieved")


@router.post("", status_code=201)
def create_hackathon(
    payload: HackathonCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    item = hackathon_service.create_hackathon(db, payload)
    return success_response(HackathonOut.model_validate(item), "Hackathon created", status_code=201)


@router.put("/{hackathon_id}")
def update_hackathon(
    hackathon_id: int,
    payload: HackathonUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    item = hackathon_service.update_hackathon(db, hackathon_id, payload)
    return success_response(HackathonOut.model_validate(item), "Hackathon updated")


@router.delete("/{hackathon_id}")
def delete_hackathon(
    hackathon_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    hackathon_service.delete_hackathon(db, hackathon_id)
    return success_response(None, "Hackathon deleted")
