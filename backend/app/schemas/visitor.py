from datetime import datetime

from pydantic import BaseModel, Field


class VisitCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    page: str = Field(min_length=1, max_length=300)
    referrer: str | None = Field(default=None, max_length=500)


class VisitorOut(BaseModel):
    id: int
    session_id: str
    page: str
    referrer: str | None
    visited_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsSummary(BaseModel):
    total_visitors: int
    unique_sessions: int
    top_pages: list[dict]
