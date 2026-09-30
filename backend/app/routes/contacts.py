from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.database.database import get_db
from app.models.contact import ContactStatus
from app.models.user import User
from app.schemas.contact import ContactMessageCreate, ContactMessageOut, ContactMessageUpdate
from app.services import contact_service
from app.utils.helpers import success_response

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("", status_code=201)
def submit_message(payload: ContactMessageCreate, db: Session = Depends(get_db)):
    message = contact_service.create_message(db, payload)
    return success_response(
        ContactMessageOut.model_validate(message), "Message sent successfully", status_code=201
    )


@router.get("")
def list_messages(
    status: ContactStatus | None = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    messages = contact_service.list_messages(db, status_filter=status)
    return success_response(
        [ContactMessageOut.model_validate(m) for m in messages], "Messages retrieved"
    )


@router.get("/{message_id}")
def get_message(
    message_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    message = contact_service.get_message(db, message_id)
    return success_response(ContactMessageOut.model_validate(message), "Message retrieved")


@router.patch("/{message_id}")
def update_message(
    message_id: int,
    payload: ContactMessageUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    message = contact_service.update_message_status(db, message_id, payload)
    return success_response(ContactMessageOut.model_validate(message), "Message updated")


@router.delete("/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    contact_service.delete_message(db, message_id)
    return success_response(None, "Message deleted")
