from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.study_plan import StudyPlan
from app.models.user import User
from app.schemas.study_plan import StudyDayFinishRequest, StudyPlanGenerateRequest, StudyPlanResponse, StudyScheduleUpdateRequest, StudyTaskUpdateRequest
from app.services.study_plan_service import StudyPlanService

router = APIRouter(prefix="/study-plans", tags=["study-plans"])


@router.post("/generate", response_model=StudyPlanResponse, status_code=201)
def generate_plan(payload: StudyPlanGenerateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    courses = db.query(Course).filter(Course.user_id == current_user.id, Course.id.in_(payload.course_ids)).all()
    if len(courses) != len(set(payload.course_ids)):
        raise HTTPException(status_code=404, detail="Seçilen derslerden biri bulunamadı")
    document_ids, plan_data = StudyPlanService().generate(
        db=db,
        user_id=current_user.id,
        courses=courses,
        duration_days=payload.duration_days,
        daily_minutes=payload.daily_minutes,
        study_days=payload.study_days,
        goal=payload.goal,
        schedule_mode=payload.schedule_mode,
        availability=payload.availability,
    )
    course_title = courses[0].title if len(courses) == 1 else f"{len(courses)} Ders"
    plan = StudyPlan(user_id=current_user.id, document_ids=document_ids, title=f"{course_title} • {payload.duration_days} Günlük Plan", plan_data=plan_data)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _recalculate(data: dict) -> dict:
    days = data.get("days", [])
    completed = sum(1 for day in days for task in day.get("tasks", []) if task.get("completed"))
    total = sum(len(day.get("tasks", [])) for day in days)
    data["completed_tasks"] = completed
    data["total_tasks"] = total
    data["progress"] = round(completed * 100 / total) if total else 0
    data["total_study_days"] = len(days)
    if days:
        data["end_date"] = days[-1]["date"]
    return data


def _next_available_date(after_date, availability: dict):
    from datetime import timedelta
    candidate = after_date + timedelta(days=1)
    while candidate.weekday() not in availability:
        candidate += timedelta(days=1)
    return candidate


def _redistribute(data: dict, from_date: str) -> dict:
    from datetime import date
    days = data.get("days", [])
    availability = {int(item["weekday"]): item for item in data.get("availability", []) if item.get("enabled", True)}
    if not availability:
        return data
    fixed_days = [day for day in days if day["date"] <= from_date]
    future_days = [day for day in days if day["date"] > from_date]
    pending = []
    for day in fixed_days:
        if day["date"] == from_date:
            pending.extend([task for task in day["tasks"] if not task.get("completed")])
            day["tasks"] = [task for task in day["tasks"] if task.get("completed")]
            day["total_minutes"] = sum(task["duration_minutes"] for task in day["tasks"])
    for day in future_days:
        pending.extend([task for task in day["tasks"] if not task.get("completed")])

    rebuilt = []
    cursor_date = date.fromisoformat(from_date)
    original_end = date.fromisoformat(data.get("end_date", from_date))
    while pending:
        cursor_date = _next_available_date(cursor_date, availability)
        settings = availability[cursor_date.weekday()]
        capacity = int(settings["minutes"])
        tasks, used = [], 0
        while pending and (used + pending[0]["duration_minutes"] <= capacity or not tasks):
            task = pending.pop(0)
            tasks.append(task)
            used += task["duration_minutes"]
        StudyPlanService._assign_task_times(tasks, settings["start_time"])
        rebuilt.append({"date": cursor_date.isoformat(), "day_number": len(fixed_days) + len(rebuilt) + 1, "capacity_minutes": capacity, "start_time": settings["start_time"], "end_time": settings["end_time"], "total_minutes": used, "status": "planned", "finished_at": None, "tasks": tasks})

    data["days"] = fixed_days + rebuilt
    new_end = date.fromisoformat(data["days"][-1]["date"]) if data["days"] else original_end
    extension = max(0, (new_end - original_end).days)
    alerts = [alert for alert in data.get("alerts", []) if alert.get("type") not in ("extension", "intensity")]
    if extension:
        alerts.append({"type": "extension", "message": f"Tamamlanmayan görevler nedeniyle plan {extension} gün uzadı: {original_end.isoformat()} → {new_end.isoformat()}."})
    dense_days = [day for day in rebuilt if day["total_minutes"] >= day["capacity_minutes"] * 0.9]
    if dense_days:
        alerts.append({"type": "intensity", "message": "Yaklaşan çalışma günleri dolu görünüyor. Planın tekrar uzamaması için müsait saatlerinizi artırabilirsiniz."})
    data["alerts"] = alerts
    return _recalculate(data)


@router.get("", response_model=list[StudyPlanResponse])
def list_plans(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(StudyPlan).filter(StudyPlan.user_id == current_user.id).order_by(StudyPlan.created_at.desc()).limit(20).all()


@router.get("/{plan_id}", response_model=StudyPlanResponse)
def get_plan(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id, StudyPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Çalışma planı bulunamadı")
    return plan


@router.patch("/{plan_id}/tasks/{task_id}", response_model=StudyPlanResponse)
def update_task(plan_id: int, task_id: str, payload: StudyTaskUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id, StudyPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Çalışma planı bulunamadı")
    data = dict(plan.plan_data)
    days = [dict(day) for day in data.get("days", [])]
    found = False
    for day in days:
        tasks = [dict(task) for task in day.get("tasks", [])]
        for task in tasks:
            if task.get("id") == task_id:
                task["completed"] = payload.completed
                task["completed_at"] = datetime.utcnow().isoformat() if payload.completed else None
                found = True
        day["tasks"] = tasks
    if not found:
        raise HTTPException(status_code=404, detail="Plan görevi bulunamadı")
    completed = sum(1 for day in days for task in day["tasks"] if task.get("completed"))
    total = sum(len(day["tasks"]) for day in days)
    data["days"] = days
    data["completed_tasks"] = completed
    data["progress"] = round(completed * 100 / total) if total else 0
    plan.plan_data = data
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/{plan_id}/finish-day", response_model=StudyPlanResponse)
def finish_day(plan_id: int, payload: StudyDayFinishRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id, StudyPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Çalışma planı bulunamadı")
    data = dict(plan.plan_data)
    target = next((day for day in data.get("days", []) if day["date"] == payload.date), None)
    if not target:
        raise HTTPException(status_code=404, detail="Plan günü bulunamadı")
    incomplete = sum(1 for task in target.get("tasks", []) if not task.get("completed"))
    target["status"] = "finished"
    target["finished_at"] = datetime.utcnow().isoformat()
    if incomplete:
        data = _redistribute(data, payload.date)
        data.setdefault("alerts", []).insert(0, {"type": "carryover", "message": f"{incomplete} tamamlanmamış görev sonraki uygun çalışma günlerine aktarıldı."})
    else:
        data = _recalculate(data)
        data["alerts"] = [alert for alert in data.get("alerts", []) if alert.get("type") != "carryover"]
    plan.plan_data = data
    db.commit()
    db.refresh(plan)
    return plan


@router.patch("/{plan_id}/schedule", response_model=StudyPlanResponse)
def update_schedule(plan_id: int, payload: StudyScheduleUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from datetime import date

    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id, StudyPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Çalışma planı bulunamadı")
    data = dict(plan.plan_data)
    availability_map = StudyPlanService._availability_map(payload.study_days, payload.daily_minutes, payload.schedule_mode, payload.availability)
    data["daily_minutes"] = payload.daily_minutes
    data["study_days"] = payload.study_days
    data["schedule_mode"] = payload.schedule_mode
    data["availability"] = list(availability_map.values())
    data = _redistribute(data, date.today().isoformat())
    data.setdefault("alerts", []).insert(0, {"type": "schedule", "message": "Müsaitlik saatleriniz değiştiği için kalan çalışma programı yeniden oluşturuldu."})
    plan.plan_data = data
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=204)
def delete_plan(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id, StudyPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Çalışma planı bulunamadı")
    db.delete(plan)
    db.commit()
    return None
