import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Project Information
    PROJECT_NAME: str = "AnyStream Video Platform"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Security & Tokens
    SECRET_KEY: str = "insecure-dev-secret-key-change-in-production-minimum-32-chars-long"
    DOWNLOAD_TOKEN_EXPIRE_MINUTES: int = 30
    IP_HASH_SALT: str = "dev-salt-rotate-regularly"

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Database & Redis
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/anystream"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/anystream"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Worker & Storage Quotas
    STORAGE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../storage/tmp"))
    MAX_FILE_SIZE_BYTES: int = 2 * 1024 * 1024 * 1024  # 2 GB
    MAX_VIDEO_DURATION_SECONDS: int = 10800  # 3 hours
    JOB_EXPIRY_MINUTES: int = 25  # Automatic file eviction window
    FILE_CLEANUP_INTERVAL_SECONDS: int = 300  # 5 minutes

    # Rate Limiting & Abuse Prevention
    MAX_CONCURRENT_JOBS_PER_IP: int = 2
    RATE_LIMIT_EXTRACT_PER_MINUTE: int = 15
    RATE_LIMIT_JOB_PER_MINUTE: int = 5
    CLOUDFLARE_TURNSTILE_SECRET_KEY: str = ""
    CLOUDFLARE_TURNSTILE_VERIFY_URL: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    # SSRF & Networking Restrictions
    ALLOWED_SCHEMES: List[str] = ["http", "https"]
    ALLOWLISTED_DOMAINS: List[str] = []  # Empty means all public domain names are permitted
    DENYLISTED_DOMAINS: List[str] = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "metadata.google.internal",
        "instance-data",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

