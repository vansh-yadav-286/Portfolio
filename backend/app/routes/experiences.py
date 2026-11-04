from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database.database import get_db
from app.models.user import User
from app.schemas.experience import ExperienceCreate, ExperienceOut, ExperienceUpdate
from app.services import experience_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/experiences", tags=["experiences"])


@router.get("")
def list_experiences(db: Session = Depends(get_db)):
    experiences = experience_service.list_experiences(db)
    return success_response(
        [ExperienceOut.model_validate(e) for e in experiences], "Experiences retrieved"
    )


@router.get("/{experience_id}")
def get_experience(experience_id: int, db: Session = Depends(get_db)):
    experience = experience_service.get_experience(db, experience_id)
    return success_response(ExperienceOut.model_validate(experience), "Experience retrieved")


@router.post("", status_code=201)
def create_experience(
    payload: ExperienceCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    experience = experience_service.create_experience(db, payload)
    return success_response(
        ExperienceOut.model_validate(experience), "Experience created", status_code=201
    )


@router.put("/{experience_id}")
def update_experience(
    experience_id: int,
    payload: ExperienceUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    experience = experience_service.update_experience(db, experience_id, payload)
    return success_response(ExperienceOut.model_validate(experience), "Experience updated")


@router.delete("/{experience_id}")
def delete_experience(
    experience_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    experience_service.delete_experience(db, experience_id)
    return success_response(None, "Experience deleted")
