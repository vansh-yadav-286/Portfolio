from sqlalchemy.orm import Session

from app.models.experience import Experience
from app.schemas.experience import ExperienceCreate, ExperienceUpdate
from app.utils.helpers import api_error

# Columns that can never be cleared to null.
REQUIRED_FIELDS = {"title", "organization", "experience_type", "description", "is_current", "display_order"}


def _ordered(query):
    return query.order_by(Experience.display_order.asc(), Experience.id.asc())


def list_experiences(db: Session) -> list[Experience]:
    return _ordered(db.query(Experience)).all()


def get_experience(db: Session, experience_id: int) -> Experience:
    item = db.get(Experience, experience_id)
    if item is None:
        raise api_error("Experience not found", status_code=404)
    return item


def create_experience(db: Session, payload: ExperienceCreate) -> Experience:
    item = Experience(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_experience(db: Session, experience_id: int, payload: ExperienceUpdate) -> Experience:
    item = get_experience(db, experience_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is None and field in REQUIRED_FIELDS:
            raise api_error(f"{field} cannot be empty", status_code=422)
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_experience(db: Session, experience_id: int) -> None:
    item = get_experience(db, experience_id)
    db.delete(item)
    db.commit()
