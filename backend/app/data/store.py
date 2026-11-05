import json
import os
import tempfile
from pathlib import Path

from app.utils.helpers import api_error

DATA_DIR = Path(__file__).resolve().parent


def _path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def read_all(name: str) -> list[dict]:
    path = _path(name)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_all(name: str, items: list[dict]) -> None:
    """Atomic write (temp file + rename) so a crash mid-write can't leave a
    half-written, corrupt JSON file. NOTE: this is not durable on Render - the
    filesystem resets on every redeploy (and isn't guaranteed to survive a
    plain restart either, depending on plan). Treat anything written here as
    gone the next time the service redeploys; it is not a real database.
    """
    path = _path(name)
    fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, prefix=f".{name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, default=str)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def get_one(name: str, item_id: int, not_found_message: str) -> dict:
    for item in read_all(name):
        if item["id"] == item_id:
            return item
    raise api_error(not_found_message, status_code=404)


def _next_id(items: list[dict]) -> int:
    return (max((item["id"] for item in items), default=0)) + 1


def create(name: str, data: dict) -> dict:
    items = read_all(name)
    new_item = {"id": _next_id(items), **data}
    items.append(new_item)
    _write_all(name, items)
    return new_item


def update(name: str, item_id: int, changes: dict, not_found_message: str) -> dict:
    items = read_all(name)
    for i, item in enumerate(items):
        if item["id"] == item_id:
            items[i] = {**item, **changes}
            _write_all(name, items)
            return items[i]
    raise api_error(not_found_message, status_code=404)


def delete(name: str, item_id: int, not_found_message: str) -> None:
    items = read_all(name)
    remaining = [item for item in items if item["id"] != item_id]
    if len(remaining) == len(items):
        raise api_error(not_found_message, status_code=404)
    _write_all(name, remaining)
