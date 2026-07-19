from datetime import datetime
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    course_id: int
    filename: str
    original_filename: str
    status: str
    page_count: int
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentStatusResponse(BaseModel):
    id: int
    status: str
    page_count: int
    chunk_count: int
    error_message: str | None = None
