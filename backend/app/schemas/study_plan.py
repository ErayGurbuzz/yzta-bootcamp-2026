from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class StudyPlanGenerateRequest(BaseModel):
    course_ids: list[int] = Field(min_length=1)
    duration_days: int = Field(default=14, ge=3, le=60)
    daily_minutes: int = Field(default=60, ge=15, le=600)
    study_days: list[int] = Field(default=[0, 1, 2, 3, 4, 5, 6], min_length=1)
    schedule_mode: str = Field(default="auto", pattern="^(auto|manual)$")
    availability: list[dict] = Field(default_factory=list)
    goal: str = Field(default="Konuları pekiştirmek ve quiz başarısını artırmak", min_length=3, max_length=500)

    @field_validator("study_days")
    @classmethod
    def validate_study_days(cls, days: list[int]) -> list[int]:
        unique = sorted(set(days))
        if any(day < 0 or day > 6 for day in unique):
            raise ValueError("Çalışma günleri 0 ile 6 arasında olmalıdır")
        return unique


class StudyTaskUpdateRequest(BaseModel):
    completed: bool


class StudyDayFinishRequest(BaseModel):
    date: str


class StudyScheduleUpdateRequest(BaseModel):
    daily_minutes: int = Field(ge=15, le=600)
    study_days: list[int] = Field(min_length=1)
    schedule_mode: str = Field(default="manual", pattern="^(auto|manual)$")
    availability: list[dict] = Field(default_factory=list)


class StudyPlanResponse(BaseModel):
    id: int
    title: str
    document_ids: list[int]
    plan_data: dict
    created_at: datetime

    model_config = {"from_attributes": True}
