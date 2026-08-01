from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.document import Document
from app.models.flashcard import Flashcard, FlashcardDeck
from app.models.user import User
from app.schemas.flashcard import FlashcardCollectionResponse, FlashcardGenerateRequest, FlashcardResponse, FlashcardReviewRequest
from app.services.flashcard_service import FlashcardService

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


def _collection(cards: list[Flashcard]) -> dict:
    learned = sum(1 for card in cards if card.is_learned)
    return {"cards": cards, "total": len(cards), "learned": learned, "remaining": len(cards) - learned}


@router.get("", response_model=FlashcardCollectionResponse)
def list_flashcards(document_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Flashcard).join(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id).filter(FlashcardDeck.user_id == current_user.id)
    if document_id is not None:
        query = query.filter(FlashcardDeck.document_id == document_id)
    cards = query.order_by(Flashcard.is_learned.asc(), Flashcard.created_at.desc()).all()
    return _collection(cards)


@router.post("/generate", response_model=FlashcardCollectionResponse, status_code=201)
def generate_flashcards(payload: FlashcardGenerateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document = db.query(Document).filter(Document.id == payload.document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Doküman bulunamadı")
    if document.status != "ready":
        raise HTTPException(status_code=400, detail="Flashcard üretmek için doküman hazır olmalıdır")
    try:
        FlashcardService().generate(db=db, user_id=current_user.id, document_id=document.id, card_count=payload.card_count)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    cards = db.query(Flashcard).join(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id).filter(FlashcardDeck.user_id == current_user.id, FlashcardDeck.document_id == document.id).order_by(Flashcard.is_learned.asc(), Flashcard.created_at.desc()).all()
    return _collection(cards)


@router.patch("/{card_id}/review", response_model=FlashcardResponse)
def review_flashcard(card_id: int, payload: FlashcardReviewRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    card = db.query(Flashcard).join(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id).filter(Flashcard.id == card_id, FlashcardDeck.user_id == current_user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard bulunamadı")
    card.is_learned = payload.is_learned
    card.review_count += 1
    card.last_reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(card)
    return card


@router.delete("/{card_id}", status_code=204)
def delete_flashcard(card_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    card = db.query(Flashcard).join(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id).filter(Flashcard.id == card_id, FlashcardDeck.user_id == current_user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard bulunamadı")
    db.delete(card)
    db.commit()
    return None
