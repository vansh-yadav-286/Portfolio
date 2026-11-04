from datetime import datetime

from pydantic import BaseModel, Field


class VisitCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    page: str = Field(min_length=1, max_length=300)
    referrer: str | None = Field(default=None, max_length=500)

