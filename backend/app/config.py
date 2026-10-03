from pydantic import field_validator
from pydantic_settings import BaseSettings

from app.database_url import normalize_async_database_url


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Contract Obligation Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database (PostgreSQL for production)
    DATABASE_URL: str = "postgresql+asyncpg://localhost:5432/contract_assistant"

    @field_validator("DATABASE_URL")
    @classmethod
    def use_async_postgresql_driver(cls, value: str) -> str:
        return normalize_async_database_url(value)

    # AI/LLM (Groq AI - OpenAI compatible)
    GROQ_API_KEY: str = "placeholder_key"
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: list = [".pdf", ".docx"]

    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
