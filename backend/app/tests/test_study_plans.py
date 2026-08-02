from datetime import date

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.study_plan import StudyPlan
from app.models.user import User
from app.services.study_plan_service import StudyPlanService


def _create_course(db: Session, user: User, title: str = "Python") -> Course:
    course = Course(
        user_id=user.id,
        title=title,
        description="Study Plan test dersi",
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def _sample_plan_data() -> dict:
    today = date.today().isoformat()
    return {
        "goal": "Quiz başarısını artırmak",
        "duration_days": 7,
        "daily_minutes": 60,
        "study_days": [0, 1, 2, 3, 4, 5, 6],
        "schedule_mode": "auto",
        "availability": [
            {
                "weekday": i,
                "enabled": True,
                "minutes": 60,
                "start_time": "19:00",
                "end_time": "20:00",
            }
            for i in range(7)
        ],
        "days": [
            {
                "date": today,
                "day_number": 1,
                "capacity_minutes": 60,
                "start_time": "19:00",
                "end_time": "20:00",
                "total_minutes": 30,
                "status": "planned",
                "finished_at": None,
                "tasks": [
                    {
                        "id": "task-1",
                        "title": "Stack tekrar et",
                        "topic": "Stack",
                        "duration_minutes": 30,
                        "completed": False,
                        "completed_at": None,
                    }
                ],
            }
        ],
        "completed_tasks": 0,
        "total_tasks": 1,
        "progress": 0,
        "total_study_days": 1,
        "end_date": today,
        "alerts": [],
    }


def test_generate_study_plan(
    client,
    db: Session,
    current_user: User,
    monkeypatch,
):
    course = _create_course(db, current_user)

    def fake_generate(
        self,
        *,
        db,
        user_id,
        courses,
        duration_days,
        daily_minutes,
        study_days,
        goal,
        schedule_mode="auto",
        availability=None,
    ):
        return [], _sample_plan_data()

    monkeypatch.setattr(StudyPlanService, "generate", fake_generate)

    response = client.post(
        "/study-plans/generate",
        json={
            "course_ids": [course.id],
            "duration_days": 7,
            "daily_minutes": 60,
            "study_days": [0, 1, 2, 3, 4, 5, 6],
            "schedule_mode": "auto",
            "availability": [],
            "goal": "Quiz başarısını artırmak",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Python • 7 Günlük Plan"
    assert body["plan_data"]["progress"] == 0
    assert body["plan_data"]["total_tasks"] == 1


def test_generate_plan_rejects_another_users_course(
    client,
    db: Session,
    current_user: User,
):
    other_user = User(
        email="plan-other@studymate.local",
        hashed_password="test-only-hash",
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    other_course = _create_course(db, other_user, title="Başka Ders")

    response = client.post(
        "/study-plans/generate",
        json={
            "course_ids": [other_course.id],
            "duration_days": 7,
            "daily_minutes": 60,
            "study_days": [0, 2, 4],
            "goal": "Test hedefi",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Seçilen derslerden biri bulunamadı"


def test_update_study_task_recalculates_progress(
    client,
    db: Session,
    current_user: User,
):
    plan = StudyPlan(
        user_id=current_user.id,
        document_ids=[],
        title="Test Planı",
        plan_data=_sample_plan_data(),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    response = client.patch(
        f"/study-plans/{plan.id}/tasks/task-1",
        json={"completed": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["plan_data"]["completed_tasks"] == 1
    assert body["plan_data"]["progress"] == 100
    assert body["plan_data"]["days"][0]["tasks"][0]["completed"] is True
    assert body["plan_data"]["days"][0]["tasks"][0]["completed_at"] is not None


def test_user_cannot_open_another_users_plan(
    client,
    db: Session,
    current_user: User,
):
    other_user = User(
        email="private-plan@studymate.local",
        hashed_password="test-only-hash",
    )
    db.add(other_user)
    db.flush()

    other_plan = StudyPlan(
        user_id=other_user.id,
        document_ids=[],
        title="Özel Plan",
        plan_data=_sample_plan_data(),
    )
    db.add(other_plan)
    db.commit()
    db.refresh(other_plan)

    response = client.get(f"/study-plans/{other_plan.id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Çalışma planı bulunamadı"
