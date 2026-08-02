from collections import defaultdict
from datetime import date, timedelta
from itertools import cycle
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.document import Document
from app.models.flashcard import Flashcard, FlashcardDeck
from app.models.quiz import Quiz, QuizAnswer, QuizAttempt


class StudyPlanService:
    def generate(self, *, db: Session, user_id: int, courses: list[Course], duration_days: int, daily_minutes: int, study_days: list[int], goal: str, schedule_mode: str = "auto", availability: list[dict] | None = None) -> tuple[list[int], dict]:
        course_ids = [course.id for course in courses]
        documents = db.query(Document).filter(Document.user_id == user_id, Document.course_id.in_(course_ids), Document.status == "ready").all()
        document_ids = [document.id for document in documents]
        document_by_id = {document.id: document for document in documents}
        course_by_id = {course.id: course for course in courses}

        answer_rows = (
            db.query(QuizAnswer, Quiz, Document)
            .join(QuizAttempt, QuizAttempt.id == QuizAnswer.attempt_id)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .join(Document, Document.id == Quiz.document_id)
            .filter(QuizAttempt.user_id == user_id, Document.course_id.in_(course_ids))
            .all()
        )
        topic_stats = defaultdict(lambda: {"correct": 0, "wrong": 0, "pages": set(), "document_ids": set()})
        for answer, _, document in answer_rows:
            key = (document.course_id, answer.topic.strip() or "Genel")
            topic_stats[key]["correct" if answer.is_correct else "wrong"] += 1
            topic_stats[key]["document_ids"].add(document.id)
            if answer.source_page:
                topic_stats[key]["pages"].add(answer.source_page)

        flashcard_rows = (
            db.query(Flashcard, FlashcardDeck)
            .join(FlashcardDeck, FlashcardDeck.id == Flashcard.deck_id)
            .filter(FlashcardDeck.user_id == user_id, FlashcardDeck.document_id.in_(document_ids))
            .all()
            if document_ids else []
        )
        flashcard_stats = defaultdict(lambda: {"remaining": 0, "total": 0, "document_ids": set()})
        for card, deck in flashcard_rows:
            document = document_by_id.get(deck.document_id)
            if not document:
                continue
            key = (document.course_id, card.topic.strip() or "Genel")
            flashcard_stats[key]["total"] += 1
            flashcard_stats[key]["document_ids"].add(document.id)
            if not card.is_learned:
                flashcard_stats[key]["remaining"] += 1

        focus_areas = []
        all_keys = set(topic_stats) | set(flashcard_stats)
        for course_id, topic in all_keys:
            quiz = topic_stats[(course_id, topic)]
            cards = flashcard_stats[(course_id, topic)]
            total_answers = quiz["correct"] + quiz["wrong"]
            accuracy = round(quiz["correct"] * 100 / total_answers) if total_answers else None
            priority = quiz["wrong"] * 4 + cards["remaining"] * 2 + (2 if accuracy is not None and accuracy < 60 else 0)
            focus_areas.append({
                "course_id": course_id,
                "course_title": course_by_id[course_id].title,
                "topic": topic,
                "priority": priority,
                "accuracy": accuracy,
                "wrong_answers": quiz["wrong"],
                "remaining_flashcards": cards["remaining"],
                "pages": sorted(quiz["pages"]),
                "document_ids": sorted(quiz["document_ids"] | cards["document_ids"]),
            })

        if not focus_areas:
            for document in documents:
                focus_areas.append({
                    "course_id": document.course_id,
                    "course_title": course_by_id[document.course_id].title,
                    "topic": document.original_filename,
                    "priority": 1,
                    "accuracy": None,
                    "wrong_answers": 0,
                    "remaining_flashcards": 0,
                    "pages": [],
                    "document_ids": [document.id],
                })
        if not focus_areas:
            for course in courses:
                focus_areas.append({"course_id": course.id, "course_title": course.title, "topic": "Genel tekrar", "priority": 1, "accuracy": None, "wrong_answers": 0, "remaining_flashcards": 0, "pages": [], "document_ids": []})

        focus_areas.sort(key=lambda item: (-item["priority"], item["course_title"], item["topic"]))
        weighted_focus = []
        for area in focus_areas:
            weighted_focus.extend([area] * max(1, min(4, area["priority"])))
        focus_cycle = cycle(weighted_focus)

        start = date.today()
        availability_map = self._availability_map(study_days, daily_minutes, schedule_mode, availability or [])
        active_dates = [start + timedelta(days=offset) for offset in range(duration_days) if (start + timedelta(days=offset)).weekday() in availability_map]
        days = []
        task_types = [
            ("review", "Konu tekrarı", 0.40),
            ("flashcard", "Flashcard çalışması", 0.25),
            ("quiz", "Kısa quiz", 0.35),
        ]
        for day_index, study_date in enumerate(active_dates):
            day_settings = availability_map[study_date.weekday()]
            day_minutes = day_settings["minutes"]
            tasks = []
            for task_index, (task_type, label, ratio) in enumerate(task_types):
                area = next(focus_cycle)
                minutes = max(5, round(day_minutes * ratio / 5) * 5)
                page_text = f" • Sayfa {', '.join(str(page) for page in area['pages'][:4])}" if area["pages"] and task_type == "review" else ""
                tasks.append({
                    "id": uuid4().hex,
                    "type": task_type,
                    "title": f"{label}: {area['topic']}",
                    "description": self._description(task_type, area) + page_text,
                    "course_id": area["course_id"],
                    "course_title": area["course_title"],
                    "topic": area["topic"],
                    "duration_minutes": minutes,
                    "document_ids": area["document_ids"],
                    "completed": False,
                    "completed_at": None,
                    "order": task_index,
                })
            self._assign_task_times(tasks, day_settings["start_time"])
            days.append({"date": study_date.isoformat(), "day_number": day_index + 1, "capacity_minutes": day_minutes, "start_time": day_settings["start_time"], "end_time": day_settings["end_time"], "total_minutes": sum(task["duration_minutes"] for task in tasks), "status": "planned", "finished_at": None, "tasks": tasks})

        total_tasks = sum(len(day["tasks"]) for day in days)
        return document_ids, {
            "goal": goal,
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=duration_days - 1)).isoformat(),
            "duration_days": duration_days,
            "daily_minutes": daily_minutes,
            "study_days": study_days,
            "schedule_mode": schedule_mode,
            "availability": list(availability_map.values()),
            "total_study_days": len(days),
            "total_tasks": total_tasks,
            "completed_tasks": 0,
            "progress": 0,
            "alerts": [],
            "focus_areas": focus_areas[:10],
            "days": days,
        }

    @staticmethod
    def _availability_map(study_days: list[int], daily_minutes: int, schedule_mode: str, availability: list[dict]) -> dict:
        provided = {int(item.get("weekday")): item for item in availability if item.get("enabled", True) and item.get("weekday") is not None}
        result = {}
        for weekday in study_days:
            item = provided.get(weekday, {})
            if schedule_mode == "auto":
                start_time = "18:00" if weekday < 5 else "10:00"
                minutes = daily_minutes
            else:
                start_time = str(item.get("start_time", "18:00"))
                minutes = max(15, min(600, int(item.get("minutes", daily_minutes))))
            start_hour, start_minute = (int(value) for value in start_time.split(":"))
            end_total = start_hour * 60 + start_minute + minutes
            result[weekday] = {"weekday": weekday, "enabled": True, "start_time": start_time, "end_time": f"{(end_total // 60) % 24:02d}:{end_total % 60:02d}", "minutes": minutes}
        return result

    @staticmethod
    def _assign_task_times(tasks: list[dict], start_time: str) -> None:
        hour, minute = (int(value) for value in start_time.split(":"))
        cursor = hour * 60 + minute
        for task in tasks:
            task["start_time"] = f"{(cursor // 60) % 24:02d}:{cursor % 60:02d}"
            cursor += task["duration_minutes"]
            task["end_time"] = f"{(cursor // 60) % 24:02d}:{cursor % 60:02d}"

    @staticmethod
    def _description(task_type: str, area: dict) -> str:
        if task_type == "review":
            return "Kaynak notlarını aktif biçimde oku, önemli kavramları kendi cümlelerinle özetle"
        if task_type == "flashcard":
            return f"{area['topic']} kartlarını cevap görünmeden hatırlamaya çalış; zorlandıklarını tekrar kuyruğuna ekle"
        return f"{area['topic']} konusunda kısa bir quiz çöz ve yanlış cevapların açıklamalarını incele"
