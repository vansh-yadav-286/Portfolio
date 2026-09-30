from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.contact import ContactStatus


class ContactMessageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    subject: str = Field(default="Portfolio contact form", max_length=200)
    message: str = Field(min_length=1, max_length=5000)


class ContactMessageUpdate(BaseModel):
    status: ContactStatus


class ContactMessageOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    subject: str
    message: str
    status: ContactStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
