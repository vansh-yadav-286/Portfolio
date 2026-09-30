from sqlalchemy.orm import Session

from app.models.contact import ContactMessage, ContactStatus
from app.schemas.contact import ContactMessageCreate, ContactMessageUpdate
from app.utils.helpers import api_error


def list_messages(db: Session, status_filter: ContactStatus | None = None) -> list[ContactMessage]:
    query = db.query(ContactMessage)
    if status_filter is not None:
        query = query.filter(ContactMessage.status == status_filter)
    return query.order_by(ContactMessage.created_at.desc()).all()


def get_message(db: Session, message_id: int) -> ContactMessage:
    message = db.get(ContactMessage, message_id)
    if message is None:
        raise api_error("Contact message not found", status_code=404)
    return message


def create_message(db: Session, payload: ContactMessageCreate) -> ContactMessage:
    message = ContactMessage(**payload.model_dump())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def update_message_status(
    db: Session, message_id: int, payload: ContactMessageUpdate
) -> ContactMessage:
    message = get_message(db, message_id)
    message.status = payload.status
    db.commit()
    db.refresh(message)
    return message


def delete_message(db: Session, message_id: int) -> None:
    message = get_message(db, message_id)
    db.delete(message)
    db.commit()


def count_unread(db: Session) -> int:
    return db.query(ContactMessage).filter(ContactMessage.status == ContactStatus.unread).count()
