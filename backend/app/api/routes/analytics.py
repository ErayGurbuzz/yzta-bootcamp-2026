from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.document import Document
from app.models.quiz import Quiz, QuizAnswer, QuizAttempt, QuizQuestion
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def analytics_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attempt_rows = (
        db.query(QuizAttempt, Quiz, Document, Course)
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .join(Document, Document.id == Quiz.document_id)
        .join(Course, Course.id == Document.course_id)
        .filter(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.completed_at.asc())
        .all()
    )

    answer_rows = (
        db.query(QuizAnswer, QuizAttempt, Quiz, QuizQuestion, Document, Course)
        .join(QuizAttempt, QuizAttempt.id == QuizAnswer.attempt_id)
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .join(QuizQuestion, QuizQuestion.id == QuizAnswer.question_id)
        .join(Document, Document.id == Quiz.document_id)
        .join(Course, Course.id == Document.course_id)
        .filter(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.completed_at.desc(), QuizAnswer.id.desc())
        .all()
    )

    total_attempts = len(attempt_rows)
    total_questions = sum(attempt.total_questions for attempt, *_ in attempt_rows)
    total_correct = sum(attempt.score for attempt, *_ in attempt_rows)
    average_score = round(sum(attempt.percentage for attempt, *_ in attempt_rows) / total_attempts, 1) if total_attempts else 0
    accuracy = round(total_correct * 100 / total_questions, 1) if total_questions else 0
    course_ids = {course.id for _, _, _, course in attempt_rows}

    course_stats = defaultdict(lambda: {"attempts": 0, "correct": 0, "total": 0, "last_activity": None})
    for attempt, _, _, course in attempt_rows:
        stats = course_stats[(course.id, course.title)]
        stats["attempts"] += 1
        stats["correct"] += attempt.score
        stats["total"] += attempt.total_questions
        stats["last_activity"] = attempt.completed_at

    topic_stats = defaultdict(lambda: {"correct": 0, "wrong": 0, "pages": set(), "courses": set(), "last_wrong_at": None})
    recent_mistakes = []
    for answer, attempt, _, question, document, course in answer_rows:
        topic = answer.topic.strip() or "Genel"
        stats = topic_stats[topic]
        stats["courses"].add(course.title)
        if answer.source_page:
            stats["pages"].add(answer.source_page)
        if answer.is_correct:
            stats["correct"] += 1
        else:
            stats["wrong"] += 1
            if stats["last_wrong_at"] is None:
                stats["last_wrong_at"] = attempt.completed_at
            if len(recent_mistakes) < 12:
                recent_mistakes.append(
                    {
                        "answer_id": answer.id,
                        "course_title": course.title,
                        "document_name": document.original_filename,
                        "topic": topic,
                        "question": question.question_text,
                        "user_answer": answer.user_answer,
                        "correct_answer": answer.correct_answer,
                        "explanation": answer.explanation,
                        "source_page": answer.source_page,
                        "completed_at": attempt.completed_at,
                    }
                )

    topics = []
    for topic, stats in topic_stats.items():
        total = stats["correct"] + stats["wrong"]
        topics.append(
            {
                "topic": topic,
                "correct": stats["correct"],
                "wrong": stats["wrong"],
                "total": total,
                "accuracy": round(stats["correct"] * 100 / total, 1) if total else 0,
                "pages": sorted(stats["pages"]),
                "courses": sorted(stats["courses"]),
                "last_wrong_at": stats["last_wrong_at"],
            }
        )
    topics.sort(key=lambda item: (-item["wrong"], item["accuracy"], item["topic"].lower()))

    courses = []
    for (course_id, title), stats in course_stats.items():
        courses.append(
            {
                "course_id": course_id,
                "course_title": title,
                "attempts": stats["attempts"],
                "correct": stats["correct"],
                "total": stats["total"],
                "accuracy": round(stats["correct"] * 100 / stats["total"], 1) if stats["total"] else 0,
                "last_activity": stats["last_activity"],
            }
        )
    courses.sort(key=lambda item: (item["accuracy"], -item["attempts"]))

    trend = [
        {
            "attempt_id": attempt.id,
            "date": attempt.completed_at,
            "percentage": attempt.percentage,
            "score": attempt.score,
            "total": attempt.total_questions,
            "course_title": course.title,
        }
        for attempt, _, _, course in attempt_rows[-16:]
    ]

    weak_topics = [topic for topic in topics if topic["wrong"] > 0][:3]
    recommendations = [
        {
            "topic": topic["topic"],
            "course": topic["courses"][0] if topic["courses"] else None,
            "message": f"{topic['topic']} konusunda %{topic['accuracy']} başarı. "
            + (f"Önce {', '.join(str(page) for page in topic['pages'][:4])}. sayfaları tekrar et; " if topic["pages"] else "Konu notlarını tekrar et; ")
            + "ardından kısa bir tekrar quiz'i çöz.",
        }
        for topic in weak_topics
    ]

    return {
        "generated_at": datetime.utcnow(),
        "summary": {
            "total_attempts": total_attempts,
            "total_questions": total_questions,
            "total_correct": total_correct,
            "average_score": average_score,
            "accuracy": accuracy,
            "courses_studied": len(course_ids),
        },
        "trend": trend,
        "courses": courses,
        "topics": topics,
        "recent_mistakes": recent_mistakes,
        "recommendations": recommendations,
    }
