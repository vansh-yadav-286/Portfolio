from pydantic import BaseModel, EmailStr, Field


class ContactMessageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    subject: str = Field(default="Portfolio contact form", max_length=200)
    message: str = Field(min_length=1, max_length=5000)
