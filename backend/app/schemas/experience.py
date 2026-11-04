from datetime import date as Date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import SafeUrl


class ExperienceBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    organization: str = Field(min_length=1, max_length=200)
    experience_type: str = Field(min_length=1, max_length=100)
    start_date: Date | None = None
    end_date: Date | None = None
    is_current: bool = False
    description: str = Field(min_length=1, max_length=2000)
    link_url: SafeUrl = None
    display_order: int = Field(default=0, ge=0, le=100000)


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceUpdate(BaseModel):
    # Every field is optional for partial updates. Required columns are checked in the
    # service so that sending null for them returns a clear error instead of a database error.
    title: str | None = Field(default=None, min_length=1, max_length=200)
    organization: str | None = Field(default=None, min_length=1, max_length=200)
    experience_type: str | None = Field(default=None, min_length=1, max_length=100)
    start_date: Date | None = None
    end_date: Date | None = None
    is_current: bool | None = None
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    link_url: SafeUrl = None
    display_order: int | None = Field(default=None, ge=0, le=100000)


class ExperienceOut(ExperienceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
