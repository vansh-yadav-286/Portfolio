from datetime import datetime, timezone

from app.data import store
from app.schemas.certificate import CertificateCreate, CertificateUpdate

STORE = "certificates"


def list_certificates() -> list[dict]:
    items = store.read_all(STORE)
    return sorted(items, key=lambda c: (c["display_order"], c["id"]))


def get_certificate(certificate_id: int) -> dict:
    return store.get_one(STORE, certificate_id, "Certificate not found")


def create_certificate(payload: CertificateCreate) -> dict:
    now = datetime.now(timezone.utc)
    data = {**payload.model_dump(), "created_at": now, "updated_at": now}
    return store.create(STORE, data)


def update_certificate(certificate_id: int, payload: CertificateUpdate) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    changes["updated_at"] = datetime.now(timezone.utc)
    return store.update(STORE, certificate_id, changes, "Certificate not found")


def delete_certificate(certificate_id: int) -> None:
    store.delete(STORE, certificate_id, "Certificate not found")
