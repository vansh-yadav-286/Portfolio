from datetime import date, datetime

from pydantic import BaseModel, Field


class CertificateBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    issuer: str = Field(min_length=1, max_length=200)
    issue_date: date | None = None
    credential_id: str | None = Field(default=None, max_length=200)
    credential_url: str | None = None
    image_url: str | None = None
    pdf_url: str | None = None


class CertificateCreate(CertificateBase):
    pass


class CertificateUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    issuer: str | None = Field(default=None, min_length=1, max_length=200)
    issue_date: date | None = None
    credential_id: str | None = Field(default=None, max_length=200)
    credential_url: str | None = None
    image_url: str | None = None
    pdf_url: str | None = None


class CertificateOut(CertificateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
