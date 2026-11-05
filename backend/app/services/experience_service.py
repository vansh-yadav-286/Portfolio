from datetime import datetime, timezone

from app.data import store
from app.schemas.experience import ExperienceCreate, ExperienceUpdate
from app.utils.helpers import api_error

STORE = "experiences"

# Columns that can never be cleared to null.
REQUIRED_FIELDS = {"title", "organization", "experience_type", "description", "is_current", "display_order"}


def list_experiences() -> list[dict]:
    items = store.read_all(STORE)
    return sorted(items, key=lambda e: (e["display_order"], e["id"]))


def get_experience(experience_id: int) -> dict:
    return store.get_one(STORE, experience_id, "Experience not found")


def create_experience(payload: ExperienceCreate) -> dict:
    now = datetime.now(timezone.utc)
    data = {**payload.model_dump(), "created_at": now, "updated_at": now}
    return store.create(STORE, data)


def update_experience(experience_id: int, payload: ExperienceUpdate) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is None and field in REQUIRED_FIELDS:
            raise api_error(f"{field} cannot be empty", status_code=422)
    changes["updated_at"] = datetime.now(timezone.utc)
    return store.update(STORE, experience_id, changes, "Experience not found")


def delete_experience(experience_id: int) -> None:
    store.delete(STORE, experience_id, "Experience not found")
