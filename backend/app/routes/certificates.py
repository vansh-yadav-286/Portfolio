from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, get_current_admin, verify_csrf
from app.schemas.certificate import CertificateCreate, CertificateOut, CertificateUpdate
from app.services import certificate_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


@router.get("")
def list_certificates():
    certificates = certificate_service.list_certificates()
    return success_response(
        [CertificateOut.model_validate(c) for c in certificates], "Certificates retrieved"
    )


@router.get("/{certificate_id}")
def get_certificate(certificate_id: int):
    certificate = certificate_service.get_certificate(certificate_id)
    return success_response(CertificateOut.model_validate(certificate), "Certificate retrieved")


@router.post("", status_code=201, dependencies=[Depends(verify_csrf)])
def create_certificate(payload: CertificateCreate, _admin: CurrentUser = Depends(get_current_admin)):
    certificate = certificate_service.create_certificate(payload)
    return success_response(
        CertificateOut.model_validate(certificate), "Certificate created", status_code=201
    )


@router.put("/{certificate_id}", dependencies=[Depends(verify_csrf)])
def update_certificate(
    certificate_id: int, payload: CertificateUpdate, _admin: CurrentUser = Depends(get_current_admin)
):
    certificate = certificate_service.update_certificate(certificate_id, payload)
    return success_response(CertificateOut.model_validate(certificate), "Certificate updated")


@router.delete("/{certificate_id}", dependencies=[Depends(verify_csrf)])
def delete_certificate(certificate_id: int, _admin: CurrentUser = Depends(get_current_admin)):
    certificate_service.delete_certificate(certificate_id)
    return success_response(None, "Certificate deleted")
