from datetime import datetime

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.document import Document
from app.models.flashcard import Flashcard, FlashcardDeck
from app.models.user import User
from app.services.flashcard_service import FlashcardService


def _create_course_and_document(
    db: Session,
    user: User,
    *,
    status: str = "ready",
) -> tuple[Course, Document]:
    course = Course(
        user_id=user.id,
        title="Algoritmalar",
        description="Sprint 3 test dersi",
    )
    db.add(course)
    db.flush()

    document = Document(
        user_id=user.id,
        course_id=course.id,
        filename="algoritmalar.pdf",
        original_filename="Algoritmalar.pdf",
        file_path="/tmp/algoritmalar.pdf",
        status=status,
        page_count=5,
    )
    db.add(document)
    db.commit()
    db.refresh(course)
    db.refresh(document)
    return course, document


def test_flashcard_generate_rejects_document_that_is_not_ready(
    client,
    db: Session,
    current_user: User,
):
    _, document = _create_course_and_document(
        db,
        current_user,
        status="processing",
    )

    response = client.post(
        "/flashcards/generate",
        json={"document_id": document.id, "card_count": 5},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Flashcard üretmek için doküman hazır olmalıdır"
    )


def test_flashcard_generate_returns_created_cards(
    client,
    db: Session,
    current_user: User,
    monkeypatch,
):
    _, document = _create_course_and_document(db, current_user)

    def fake_generate(self, *, db, user_id, document_id, card_count):
        deck = FlashcardDeck(
            user_id=user_id,
            document_id=document_id,
            title="Test çalışma seti",
        )
        db.add(deck)
        db.flush()

        card = Flashcard(
            deck_id=deck.id,
            front="Big-O nedir?",
            back="Algoritmanın büyüme hızını ifade eder.",
            topic="Karmaşıklık",
            source_page=2,
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        return [card]

    monkeypatch.setattr(FlashcardService, "generate", fake_generate)

    response = client.post(
        "/flashcards/generate",
        json={"document_id": document.id, "card_count": 5},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["total"] == 1
    assert body["learned"] == 0
    assert body["remaining"] == 1
    assert body["cards"][0]["topic"] == "Karmaşıklık"
    assert body["cards"][0]["source_page"] == 2


def test_flashcard_review_updates_progress(
    client,
    db: Session,
    current_user: User,
):
    _, document = _create_course_and_document(db, current_user)

    deck = FlashcardDeck(
        user_id=current_user.id,
        document_id=document.id,
        title="Test Deck",
    )
    db.add(deck)
    db.flush()

    card = Flashcard(
        deck_id=deck.id,
        front="Stack nedir?",
        back="LIFO veri yapısıdır.",
        topic="Veri Yapıları",
        source_page=1,
        is_learned=False,
        review_count=0,
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    response = client.patch(
        f"/flashcards/{card.id}/review",
        json={"is_learned": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_learned"] is True
    assert body["review_count"] == 1
    assert body["last_reviewed_at"] is not None


def test_user_cannot_review_another_users_flashcard(
    client,
    db: Session,
    current_user: User,
):
    other_user = User(
        email="other-user@studymate.local",
        hashed_password="test-only-hash",
    )
    db.add(other_user)
    db.flush()

    _, other_document = _create_course_and_document(db, other_user)
    other_deck = FlashcardDeck(
        user_id=other_user.id,
        document_id=other_document.id,
        title="Başka kullanıcının destesi",
    )
    db.add(other_deck)
    db.flush()

    other_card = Flashcard(
        deck_id=other_deck.id,
        front="Soru",
        back="Cevap",
        topic="Genel",
        created_at=datetime.utcnow(),
    )
    db.add(other_card)
    db.commit()
    db.refresh(other_card)

    response = client.patch(
        f"/flashcards/{other_card.id}/review",
        json={"is_learned": True},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Flashcard bulunamadı"
