import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "PulseWatch"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/pulsewatch"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Security & Auth
    SECRET_KEY: str = "pulsewatch-super-secret-development-key-change-in-production-12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Ingestion constraints
    MAX_INGEST_BATCH_SIZE: int = 500
    MAX_LOG_MESSAGE_LENGTH: int = 10000
    RATE_LIMIT_PER_MINUTE: int = 1200  # Default requests per minute per API key
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Email / SMTP Settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "alerts@pulsewatch.dev"


settings = Settings()
