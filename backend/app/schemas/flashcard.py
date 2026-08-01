from datetime import datetime

from pydantic import BaseModel, Field


class FlashcardGenerateRequest(BaseModel):
    document_id: int
    card_count: int = Field(default=10, ge=3, le=30)


class FlashcardReviewRequest(BaseModel):
    is_learned: bool


class FlashcardResponse(BaseModel):
    id: int
    front: str
    back: str
    topic: str
    source_page: int | None = None
    is_learned: bool
    review_count: int
    created_at: datetime
    last_reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}


class FlashcardCollectionResponse(BaseModel):
    cards: list[FlashcardResponse]
    total: int
    learned: int
    remaining: int
