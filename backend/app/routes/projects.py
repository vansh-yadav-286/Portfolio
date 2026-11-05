from fastapi import APIRouter, Depends, Query

from app.core.dependencies import CurrentUser, get_current_admin, verify_csrf
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services import project_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_projects(featured: bool = Query(default=False)):
    projects = project_service.list_projects(featured_only=featured)
    return success_response([ProjectOut.model_validate(p) for p in projects], "Projects retrieved")


@router.get("/{project_id}")
def get_project(project_id: int):
    project = project_service.get_project(project_id)
    return success_response(ProjectOut.model_validate(project), "Project retrieved")


@router.post("", status_code=201, dependencies=[Depends(verify_csrf)])
def create_project(payload: ProjectCreate, _admin: CurrentUser = Depends(get_current_admin)):
    project = project_service.create_project(payload)
    return success_response(ProjectOut.model_validate(project), "Project created", status_code=201)


@router.put("/{project_id}", dependencies=[Depends(verify_csrf)])
def update_project(project_id: int, payload: ProjectUpdate, _admin: CurrentUser = Depends(get_current_admin)):
    project = project_service.update_project(project_id, payload)
    return success_response(ProjectOut.model_validate(project), "Project updated")


@router.delete("/{project_id}", dependencies=[Depends(verify_csrf)])
def delete_project(project_id: int, _admin: CurrentUser = Depends(get_current_admin)):
    project_service.delete_project(project_id)
    return success_response(None, "Project deleted")
