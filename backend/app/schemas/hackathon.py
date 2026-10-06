from datetime import date as Date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import SafeUrl

HackathonType = Literal["hackathon", "workshop"]
# Icon keys map to inline SVGs in frontend/js/script.js. Anything else is rejected.
HackathonIcon = Literal["bolt", "layers", "clock", "trophy", "book", "code", "globe", "users"]


class HackathonSubItem(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    certificate_url: SafeUrl = None


class HackathonBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: HackathonType
    description: str = Field(default="", max_length=2000)
    organizer: str | None = Field(default=None, max_length=200)
    date: Date | None = None
    location: str | None = Field(default=None, max_length=200)
    icon: HackathonIcon | None = None
    image_url: SafeUrl = None
    certificate_url: SafeUrl = None
    event_url: SafeUrl = None
    subitems: list[HackathonSubItem] | None = Field(default=None, max_length=20)
    is_visible: bool = True
    display_order: int = Field(default=0, ge=0, le=100000)


class HackathonCreate(HackathonBase):
    pass


class HackathonUpdate(BaseModel):
    # Every field is optional. Required columns are checked in the service so that
    # sending null for them returns a clear error instead of a database error.
    title: str | None = Field(default=None, min_length=1, max_length=200)
    type: HackathonType | None = None
    description: str | None = Field(default=None, max_length=2000)
    organizer: str | None = Field(default=None, max_length=200)
    date: Date | None = None
    location: str | None = Field(default=None, max_length=200)
    icon: HackathonIcon | None = None
    image_url: SafeUrl = None
    certificate_url: SafeUrl = None
    event_url: SafeUrl = None
    subitems: list[HackathonSubItem] | None = Field(default=None, max_length=20)
    is_visible: bool | None = None
    display_order: int | None = Field(default=None, ge=0, le=100000)


class HackathonOut(HackathonBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
