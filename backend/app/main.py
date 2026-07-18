from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.db.session import Base, engine
from app import models  # noqa: F401
from app.api.routes import analytics, auth, courses, documents, chat, evaluation, flashcards, quiz, study_plans

settings = get_settings()

app = FastAPI(
    title="StudyMate API",
    description="RAG tabanlı kişisel öğrenme asistanı: PDF soru-cevap, kaynak gösterme, quiz ve yanlış analizi.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(evaluation.router)
app.include_router(analytics.router)
app.include_router(flashcards.router)
app.include_router(study_plans.router)
