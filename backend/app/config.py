from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://studymate:studymate@postgres:5432/studymate"
    chroma_host: str = "chroma"
    chroma_port: int = 8000
    chroma_collection: str = "studymate_chunks"

    gemini_api_key: str | None = None
    gemini_llm_model: str = "gemini-1.5-flash"
    gemini_embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768

    jwt_secret_key: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    upload_dir: str = "uploads"
    max_upload_mb: int = 25
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
