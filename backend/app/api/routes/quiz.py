from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.document import Document
from app.models.quiz import Quiz, QuizAttempt
from app.models.user import User
from app.schemas.quiz import QuizDetailResponse, QuizGenerateRequest, QuizHistoryItem, QuizSubmitRequest, QuizSubmitResponse
from app.services.embedding_service import MissingGeminiKeyError
from app.services.quiz_service import QuizService

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/generate", response_model=QuizDetailResponse, status_code=201)
def generate_quiz(payload: QuizGenerateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = db.query(Document).filter(Document.id == payload.document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "ready":
        raise HTTPException(status_code=400, detail=f"Document is not ready. Current status: {document.status}")

    try:
        quiz = QuizService().generate_quiz(
            db=db,
            user_id=current_user.id,
            document_id=document.id,
            question_count=payload.question_count,
            difficulty=payload.difficulty,
            question_type=payload.question_type,
        )
    except MissingGeminiKeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return quiz


@router.get("/{quiz_id}", response_model=QuizDetailResponse)
def get_quiz(quiz_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == current_user.id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


@router.post("/{quiz_id}/submit", response_model=QuizSubmitResponse)
def submit_quiz(quiz_id: int, payload: QuizSubmitRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == current_user.id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    submitted = {item.question_id: item.answer for item in payload.answers}
    result = QuizService().submit_quiz(db=db, user_id=current_user.id, quiz=quiz, submitted=submitted)
    return result


@router.get("/history/list", response_model=list[QuizHistoryItem])
def history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(50)
        .all()
    )
