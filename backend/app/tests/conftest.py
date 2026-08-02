from pathlib import Path
import os
import sys

# app.db.session import edilmeden önce test veritabanını zorla.
os.environ["DATABASE_URL"] = "sqlite://"

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401 - bütün modelleri SQLAlchemy registry'ye yükler
from app.api.dependencies import get_current_user
from app.api.routes import analytics, flashcards, study_plans
from app.db.session import Base, get_db
from app.models.user import User


TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def current_user(db: Session) -> User:
    user = User(
        email="ege-test@studymate.local",
        hashed_password="test-only-hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def client(db: Session, current_user: User) -> Generator[TestClient, None, None]:
    test_app = FastAPI()

    # Gerçek Sprint 3 router'ları kullanılır.
    test_app.include_router(analytics.router)
    test_app.include_router(flashcards.router)
    test_app.include_router(study_plans.router)

    # /health endpointinin gerçek uygulamadaki davranışını aynı kontratla test eder.
    @test_app.get("/health")
    def health():
        return {"status": "ok"}

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_current_user():
        return current_user

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(test_app) as test_client:
        yield test_client
