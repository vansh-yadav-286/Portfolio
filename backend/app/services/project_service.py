from datetime import datetime, timezone

from app.data import store
from app.schemas.project import ProjectCreate, ProjectUpdate

STORE = "projects"


def list_projects(featured_only: bool = False) -> list[dict]:
    items = store.read_all(STORE)
    if featured_only:
        items = [p for p in items if p.get("featured")]
    return sorted(items, key=lambda p: (p["display_order"], p["id"]))


def get_project(project_id: int) -> dict:
    return store.get_one(STORE, project_id, "Project not found")


def create_project(payload: ProjectCreate) -> dict:
    now = datetime.now(timezone.utc)
    data = {**payload.model_dump(), "created_at": now, "updated_at": now}
    return store.create(STORE, data)


def update_project(project_id: int, payload: ProjectUpdate) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    changes["updated_at"] = datetime.now(timezone.utc)
    return store.update(STORE, project_id, changes, "Project not found")


def delete_project(project_id: int) -> None:
    store.delete(STORE, project_id, "Project not found")
