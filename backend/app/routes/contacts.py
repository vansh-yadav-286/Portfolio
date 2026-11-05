from fastapi import APIRouter, Request

from app.core.rate_limit import limiter
from app.schemas.contact import ContactMessageCreate
from app.services import contact_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("", status_code=201)
@limiter.limit("5/minute")
def submit_message(request: Request, payload: ContactMessageCreate):
    # Forwarded by email, not stored - there is no database and so no admin
    # inbox to browse later. See services/contact_service.py.
    contact_service.send_message(payload)
    return success_response(None, "Message sent successfully", status_code=201)
