from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database.database import get_db
from app.models.user import User
from app.schemas.certificate import CertificateCreate, CertificateOut, CertificateUpdate
from app.services import certificate_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


@router.get("")
def list_certificates(db: Session = Depends(get_db)):
    certificates = certificate_service.list_certificates(db)
    return success_response(
        [CertificateOut.model_validate(c) for c in certificates], "Certificates retrieved"
    )


@router.get("/{certificate_id}")
def get_certificate(certificate_id: int, db: Session = Depends(get_db)):
    certificate = certificate_service.get_certificate(db, certificate_id)
    return success_response(CertificateOut.model_validate(certificate), "Certificate retrieved")


@router.post("", status_code=201)
def create_certificate(
    payload: CertificateCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    certificate = certificate_service.create_certificate(db, payload)
    return success_response(
        CertificateOut.model_validate(certificate), "Certificate created", status_code=201
    )


@router.put("/{certificate_id}")
def update_certificate(
    certificate_id: int,
    payload: CertificateUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    certificate = certificate_service.update_certificate(db, certificate_id, payload)
    return success_response(CertificateOut.model_validate(certificate), "Certificate updated")


@router.delete("/{certificate_id}")
def delete_certificate(
    certificate_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    certificate_service.delete_certificate(db, certificate_id)
    return success_response(None, "Certificate deleted")
