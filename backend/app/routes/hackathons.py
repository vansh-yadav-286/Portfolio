from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, get_current_admin, verify_csrf
from app.schemas.hackathon import HackathonCreate, HackathonOut, HackathonUpdate
from app.services import hackathon_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/hackathons", tags=["hackathons"])


@router.get("")
def list_visible_hackathons():
    items = hackathon_service.list_public()
    return success_response([HackathonOut.model_validate(i) for i in items], "Hackathons retrieved")


@router.get("/manage")
def list_all_hackathons(_admin: CurrentUser = Depends(get_current_admin)):
    items = hackathon_service.list_all()
    return success_response([HackathonOut.model_validate(i) for i in items], "Hackathons retrieved")


@router.post("", status_code=201, dependencies=[Depends(verify_csrf)])
def create_hackathon(payload: HackathonCreate, _admin: CurrentUser = Depends(get_current_admin)):
    item = hackathon_service.create_hackathon(payload)
    return success_response(HackathonOut.model_validate(item), "Hackathon created", status_code=201)


@router.put("/{hackathon_id}", dependencies=[Depends(verify_csrf)])
def update_hackathon(
    hackathon_id: int, payload: HackathonUpdate, _admin: CurrentUser = Depends(get_current_admin)
):
    item = hackathon_service.update_hackathon(hackathon_id, payload)
    return success_response(HackathonOut.model_validate(item), "Hackathon updated")


@router.delete("/{hackathon_id}", dependencies=[Depends(verify_csrf)])
def delete_hackathon(hackathon_id: int, _admin: CurrentUser = Depends(get_current_admin)):
    hackathon_service.delete_hackathon(hackathon_id)
    return success_response(None, "Hackathon deleted")
