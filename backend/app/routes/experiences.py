from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, get_current_admin, verify_csrf
from app.schemas.experience import ExperienceCreate, ExperienceOut, ExperienceUpdate
from app.services import experience_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/experiences", tags=["experiences"])


@router.get("")
def list_experiences():
    experiences = experience_service.list_experiences()
    return success_response(
        [ExperienceOut.model_validate(e) for e in experiences], "Experiences retrieved"
    )


@router.get("/{experience_id}")
def get_experience(experience_id: int):
    experience = experience_service.get_experience(experience_id)
    return success_response(ExperienceOut.model_validate(experience), "Experience retrieved")


@router.post("", status_code=201, dependencies=[Depends(verify_csrf)])
def create_experience(payload: ExperienceCreate, _admin: CurrentUser = Depends(get_current_admin)):
    experience = experience_service.create_experience(payload)
    return success_response(
        ExperienceOut.model_validate(experience), "Experience created", status_code=201
    )


@router.put("/{experience_id}", dependencies=[Depends(verify_csrf)])
def update_experience(
    experience_id: int, payload: ExperienceUpdate, _admin: CurrentUser = Depends(get_current_admin)
):
    experience = experience_service.update_experience(experience_id, payload)
    return success_response(ExperienceOut.model_validate(experience), "Experience updated")


@router.delete("/{experience_id}", dependencies=[Depends(verify_csrf)])
def delete_experience(experience_id: int, _admin: CurrentUser = Depends(get_current_admin)):
    experience_service.delete_experience(experience_id)
    return success_response(None, "Experience deleted")
