from datetime import datetime

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    technologies: str = Field(default="", max_length=500, description="Comma-separated list, e.g. 'Python,AI,LLMs'")
    image_url: str | None = None
    github_url: str | None = None
    live_url: str | None = None
    category: str | None = Field(default=None, max_length=120)
    featured: bool = False


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    technologies: str | None = Field(default=None, max_length=500)
    image_url: str | None = None
    github_url: str | None = None
    live_url: str | None = None
    category: str | None = Field(default=None, max_length=120)
    featured: bool | None = None


class ProjectOut(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
