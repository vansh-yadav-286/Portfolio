from datetime import datetime, timezone

from app.data import store
from app.schemas.hackathon import HackathonCreate, HackathonUpdate
from app.utils.helpers import api_error

STORE = "hackathons"

# Columns that can never be cleared to null.
REQUIRED_FIELDS = {"title", "type", "is_visible", "display_order"}


def _ordered(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda h: (h["display_order"], h["id"]))


def list_public() -> list[dict]:
    return _ordered([h for h in store.read_all(STORE) if h.get("is_visible")])


def list_all() -> list[dict]:
    return _ordered(store.read_all(STORE))


def get_hackathon(hackathon_id: int) -> dict:
    return store.get_one(STORE, hackathon_id, "Hackathon or workshop not found")


def _dump(payload) -> dict:
    # exclude_unset=True, same as the original SQLAlchemy-backed implementation -
    # a field the client never sent is left out entirely rather than written as
    # its Pydantic default, so create() below fills it from the model default.
    data = payload.model_dump(exclude_unset=True)
    if "subitems" in data and data["subitems"] is not None:
        data["subitems"] = [dict(s) for s in data["subitems"]]
    return data


def create_hackathon(payload: HackathonCreate) -> dict:
    now = datetime.now(timezone.utc)
    # Defaults for any field the client omitted (exclude_unset dropped them above).
    data = {**payload.model_dump(), **_dump(payload), "created_at": now, "updated_at": now}
    return store.create(STORE, data)


def update_hackathon(hackathon_id: int, payload: HackathonUpdate) -> dict:
    changes = _dump(payload)
    for field, value in changes.items():
        if value is None and field in REQUIRED_FIELDS:
            raise api_error(f"{field} cannot be empty", status_code=422)
    changes["updated_at"] = datetime.now(timezone.utc)
    return store.update(STORE, hackathon_id, changes, "Hackathon or workshop not found")


def delete_hackathon(hackathon_id: int) -> None:
    store.delete(STORE, hackathon_id, "Hackathon or workshop not found")
