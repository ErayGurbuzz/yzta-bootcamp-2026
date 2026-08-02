from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.document import Document
from app.models.quiz import Quiz, QuizAnswer, QuizAttempt, QuizQuestion
from app.models.user import User


def _create_quiz_history(db: Session, user: User) -> None:
    course = Course(
        user_id=user.id,
        title="Veri Yapıları",
        description="Analytics test dersi",
    )
    db.add(course)
    db.flush()

    document = Document(
        user_id=user.id,
        course_id=course.id,
        filename="veri-yapilari.pdf",
        original_filename="Veri Yapıları.pdf",
        file_path="/tmp/veri-yapilari.pdf",
        status="ready",
        page_count=8,
    )
    db.add(document)
    db.flush()

    quiz = Quiz(
        user_id=user.id,
        document_id=document.id,
        title="Veri Yapıları Quiz",
        difficulty="medium",
        question_count=2,
    )
    db.add(quiz)
    db.flush()

    q1 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="Stack hangi prensiple çalışır?",
        question_type="mcq",
        options=["FIFO", "LIFO", "Random", "Priority"],
        correct_answer="LIFO",
        explanation="Stack LIFO prensibini kullanır.",
        topic="Stack",
        source_page=2,
    )
    q2 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="Queue hangi prensiple çalışır?",
        question_type="mcq",
        options=["FIFO", "LIFO", "Random", "Priority"],
        correct_answer="FIFO",
        explanation="Queue FIFO prensibini kullanır.",
        topic="Queue",
        source_page=4,
    )
    db.add_all([q1, q2])
    db.flush()

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        score=1,
        total_questions=2,
        percentage=50.0,
        weak_topic="Queue",
        recommendation="Queue konusunu tekrar et.",
    )
    db.add(attempt)
    db.flush()

    db.add_all(
        [
            QuizAnswer(
                attempt_id=attempt.id,
                question_id=q1.id,
                user_answer="LIFO",
                is_correct=True,
                correct_answer="LIFO",
                explanation=q1.explanation,
                topic="Stack",
                source_page=2,
            ),
            QuizAnswer(
                attempt_id=attempt.id,
                question_id=q2.id,
                user_answer="LIFO",
                is_correct=False,
                correct_answer="FIFO",
                explanation=q2.explanation,
                topic="Queue",
                source_page=4,
            ),
        ]
    )
    db.commit()


def test_analytics_empty_state(client):
    response = client.get("/analytics/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_attempts"] == 0
    assert body["summary"]["total_questions"] == 0
    assert body["summary"]["total_correct"] == 0
    assert body["summary"]["average_score"] == 0
    assert body["summary"]["accuracy"] == 0
    assert body["recommendations"] == []


def test_analytics_calculates_accuracy_and_weak_topic(
    client,
    db: Session,
    current_user: User,
):
    _create_quiz_history(db, current_user)

    response = client.get("/analytics/overview")

    assert response.status_code == 200
    body = response.json()

    assert body["summary"]["total_attempts"] == 1
    assert body["summary"]["total_questions"] == 2
    assert body["summary"]["total_correct"] == 1
    assert body["summary"]["average_score"] == 50.0
    assert body["summary"]["accuracy"] == 50.0
    assert body["summary"]["courses_studied"] == 1

    topics = {item["topic"]: item for item in body["topics"]}
    assert topics["Stack"]["accuracy"] == 100.0
    assert topics["Queue"]["accuracy"] == 0.0
    assert topics["Queue"]["wrong"] == 1

    assert body["recommendations"][0]["topic"] == "Queue"
    assert body["recent_mistakes"][0]["topic"] == "Queue"
    assert body["recent_mistakes"][0]["source_page"] == 4


def test_analytics_maps_blank_topic_to_genel(
    client,
    db: Session,
    current_user: User,
):
    course = Course(user_id=current_user.id, title="Test")
    db.add(course)
    db.flush()

    document = Document(
        user_id=current_user.id,
        course_id=course.id,
        filename="test.pdf",
        original_filename="test.pdf",
        file_path="/tmp/test.pdf",
        status="ready",
        page_count=1,
    )
    db.add(document)
    db.flush()

    quiz = Quiz(
        user_id=current_user.id,
        document_id=document.id,
        title="Test Quiz",
        question_count=1,
    )
    db.add(quiz)
    db.flush()

    question = QuizQuestion(
        quiz_id=quiz.id,
        question_text="Test?",
        options=["A", "B"],
        correct_answer="A",
        explanation="A",
        topic="Genel",
        source_page=1,
    )
    db.add(question)
    db.flush()

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=current_user.id,
        score=0,
        total_questions=1,
        percentage=0.0,
    )
    db.add(attempt)
    db.flush()

    answer = QuizAnswer(
        attempt_id=attempt.id,
        question_id=question.id,
        user_answer="B",
        is_correct=False,
        correct_answer="A",
        explanation="A",
        topic="   ",
        source_page=1,
    )
    db.add(answer)
    db.commit()

    response = client.get("/analytics/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["topics"][0]["topic"] == "Genel"
