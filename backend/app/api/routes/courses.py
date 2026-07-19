from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.user import User
from app.schemas.course import CourseCreate, CourseResponse, CourseUpdate

router = APIRouter(prefix="/courses", tags=["courses"])


def _normalized_title(title: str) -> str:
    return title.strip()


def _course_title_exists(db: Session, user_id: int, title: str, exclude_course_id: int | None = None) -> bool:
    query = db.query(Course.id).filter(
        Course.user_id == user_id,
        func.lower(func.trim(Course.title)) == _normalized_title(title).lower(),
    )
    if exclude_course_id is not None:
        query = query.filter(Course.id != exclude_course_id)
    return query.first() is not None


@router.post("", response_model=CourseResponse, status_code=201)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    title = _normalized_title(payload.title)
    if _course_title_exists(db, current_user.id, title):
        raise HTTPException(status_code=409, detail="Bu isimde bir ders zaten mevcut")

    course = Course(user_id=current_user.id, title=title, description=payload.description)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("", response_model=list[CourseResponse])
def list_courses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Course).filter(Course.user_id == current_user.id).order_by(Course.created_at.desc()).all()


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(course_id: int, payload: CourseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course = db.query(Course).filter(Course.id == course_id, Course.user_id == current_user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if payload.title is not None:
        title = _normalized_title(payload.title)
        if _course_title_exists(db, current_user.id, title, exclude_course_id=course.id):
            raise HTTPException(status_code=409, detail="Bu isimde bir ders zaten mevcut")
        course.title = title
    if payload.description is not None:
        course.description = payload.description
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    course = db.query(Course).filter(Course.id == course_id, Course.user_id == current_user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()
    return None
