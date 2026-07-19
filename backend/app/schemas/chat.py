from datetime import datetime
from pydantic import BaseModel, Field


class ChatAskRequest(BaseModel):
    document_id: int
    question: str = Field(min_length=2)
    mode: str = Field(default="default", description="default | simple | examples")
    top_k: int = Field(default=5, ge=1, le=10)


class MultiChatAskRequest(BaseModel):
    document_ids: list[int] = Field(min_length=1)
    question: str = Field(min_length=2)
    mode: str = Field(default="default")
    top_k: int = Field(default=5, ge=1, le=10)


class SourceChunk(BaseModel):
    document_id: int
    chunk_id: str
    page: int
    text_preview: str
    distance: float | None = None


class ChatAskResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


class ChatHistoryResponse(BaseModel):
    id: int
    document_id: int | None
    question: str
    answer: str
    mode: str
    source_chunks: list | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
