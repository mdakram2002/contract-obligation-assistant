from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Contract Obligation Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database (PostgreSQL for production)
    DATABASE_URL: str = "postgresql+asyncpg://localhost:5432/contract_assistant"

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
