from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ContactMessage
from app.schemas import ContactMessageCreate, ContactMessageOut
from app.security import get_current_admin

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("", response_model=ContactMessageOut, status_code=status.HTTP_201_CREATED)
def submit_contact_message(payload: ContactMessageCreate, db: Session = Depends(get_db)):
    message = ContactMessage(**payload.model_dump())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("", response_model=list[ContactMessageOut])
def list_contact_messages(
    db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)
):
    return db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).all()


@router.get("/{message_id}", response_model=ContactMessageOut)
def get_contact_message(
    message_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    message = db.get(ContactMessage, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not message.is_read:
        message.is_read = True
        db.commit()
        db.refresh(message)
    return message


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact_message(
    message_id: int,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    message = db.get(ContactMessage, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(message)
    db.commit()
