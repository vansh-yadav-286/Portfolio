from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import SafeUrl


class CertificateBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    issuer: str = Field(min_length=1, max_length=200)
    issue_date: date | None = None
    credential_id: str | None = Field(default=None, max_length=200)
    credential_url: SafeUrl = None
    image_url: SafeUrl = None
    pdf_url: SafeUrl = None
    display_order: int = Field(default=0, ge=0, le=100000)


class CertificateCreate(CertificateBase):
    pass


class CertificateUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    issuer: str | None = Field(default=None, min_length=1, max_length=200)
    issue_date: date | None = None
    credential_id: str | None = Field(default=None, max_length=200)
    credential_url: SafeUrl = None
    image_url: SafeUrl = None
    pdf_url: SafeUrl = None
    display_order: int | None = Field(default=None, ge=0, le=100000)


class CertificateOut(CertificateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
