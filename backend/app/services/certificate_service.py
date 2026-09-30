from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.schemas.certificate import CertificateCreate, CertificateUpdate
from app.utils.helpers import api_error


def list_certificates(db: Session) -> list[Certificate]:
    return db.query(Certificate).order_by(Certificate.created_at.desc()).all()


def get_certificate(db: Session, certificate_id: int) -> Certificate:
    certificate = db.get(Certificate, certificate_id)
    if certificate is None:
        raise api_error("Certificate not found", status_code=404)
    return certificate


def create_certificate(db: Session, payload: CertificateCreate) -> Certificate:
    certificate = Certificate(**payload.model_dump())
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate


def update_certificate(
    db: Session, certificate_id: int, payload: CertificateUpdate
) -> Certificate:
    certificate = get_certificate(db, certificate_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(certificate, field, value)
    db.commit()
    db.refresh(certificate)
    return certificate


def delete_certificate(db: Session, certificate_id: int) -> None:
    certificate = get_certificate(db, certificate_id)
    db.delete(certificate)
    db.commit()
