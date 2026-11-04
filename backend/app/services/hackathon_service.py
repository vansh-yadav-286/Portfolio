from sqlalchemy.orm import Session

from app.models.hackathon import Hackathon
from app.schemas.hackathon import HackathonCreate, HackathonUpdate
from app.utils.helpers import api_error

# Columns that can never be cleared to null.
REQUIRED_FIELDS = {"title", "type", "is_visible", "display_order"}


def _ordered(query):
    return query.order_by(Hackathon.display_order.asc(), Hackathon.id.asc())


def list_public(db: Session) -> list[Hackathon]:
    return _ordered(db.query(Hackathon).filter(Hackathon.is_visible.is_(True))).all()


def list_all(db: Session) -> list[Hackathon]:
    return _ordered(db.query(Hackathon)).all()


def get_hackathon(db: Session, hackathon_id: int) -> Hackathon:
    item = db.get(Hackathon, hackathon_id)
    if item is None:
        raise api_error("Hackathon or workshop not found", status_code=404)
    return item


def _dump(payload) -> dict:
    data = payload.model_dump(exclude_unset=True)
    if "subitems" in data and data["subitems"] is not None:
        data["subitems"] = [dict(s) for s in data["subitems"]]
    return data


def create_hackathon(db: Session, payload: HackathonCreate) -> Hackathon:
    item = Hackathon(**_dump(payload))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_hackathon(db: Session, hackathon_id: int, payload: HackathonUpdate) -> Hackathon:
    item = get_hackathon(db, hackathon_id)
    for field, value in _dump(payload).items():
        if value is None and field in REQUIRED_FIELDS:
            raise api_error(f"{field} cannot be empty", status_code=422)
        if field == "subitems":
            value = [dict(s) for s in value] if value is not None else None
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_hackathon(db: Session, hackathon_id: int) -> None:
    item = get_hackathon(db, hackathon_id)
    db.delete(item)
    db.commit()
