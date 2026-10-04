from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database.database import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services import project_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_projects(featured: bool = Query(default=False), db: Session = Depends(get_db)):
    projects = project_service.list_projects(db, featured_only=featured)
    return success_response([ProjectOut.model_validate(p) for p in projects], "Projects retrieved")


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    return success_response(ProjectOut.model_validate(project), "Project retrieved")


@router.post("", status_code=201)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    project = project_service.create_project(db, payload)
    return success_response(ProjectOut.model_validate(project), "Project created", status_code=201)


@router.put("/{project_id}")
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    project = project_service.update_project(db, project_id, payload)
    return success_response(ProjectOut.model_validate(project), "Project updated")


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    project_service.delete_project(db, project_id)
    return success_response(None, "Project deleted")
