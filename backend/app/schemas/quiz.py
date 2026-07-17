from datetime import datetime
from pydantic import BaseModel, Field


class QuizGenerateRequest(BaseModel):
    document_id: int
    question_count: int = Field(default=5, ge=1, le=15)
    difficulty: str = Field(default="medium", description="easy | medium | hard")
    question_type: str = Field(default="mcq", description="mcq | true_false")


class QuizQuestionResponse(BaseModel):
    id: int
    question_text: str
    question_type: str
    options: list[str]
    topic: str
    source_page: int | None = None

    model_config = {"from_attributes": True}


class QuizDetailResponse(BaseModel):
    id: int
    document_id: int
    title: str
    difficulty: str
    question_count: int
    questions: list[QuizQuestionResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class QuizAnswerInput(BaseModel):
    question_id: int
    answer: str


class QuizSubmitRequest(BaseModel):
    answers: list[QuizAnswerInput]


class QuizAnswerResult(BaseModel):
    question_id: int
    question_text: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str
    topic: str
    source_page: int | None = None


class QuizSubmitResponse(BaseModel):
    attempt_id: int
    score: int
    total_questions: int
    percentage: float
    weak_topic: str | None = None
    recommendation: str | None = None
    answers: list[QuizAnswerResult]


class QuizHistoryItem(BaseModel):
    id: int
    quiz_id: int
    score: int
    total_questions: int
    percentage: float
    weak_topic: str | None = None
    recommendation: str | None = None
    completed_at: datetime

    model_config = {"from_attributes": True}
