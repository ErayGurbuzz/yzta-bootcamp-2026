from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class CourseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class CourseResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
