import os
from typing import List, Optional
from pydantic import model_validator
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

    # Caching
    CACHE_TTL_SECONDS: int = 900  # 15 minutes (successful extraction)
    CACHE_ERROR_TTL_SECONDS: int = 30  # Max 30 seconds for failed extractions

    # Reverse Proxy & Client IP
    TRUSTED_PROXY_COUNT: int = 1
    TRUSTED_PROXIES: List[str] = ["127.0.0.1", "::1"]

    # Admin Management
    ADMIN_API_KEY: str = "anystream-admin-default-key-change-in-prod"

    # Worker & Storage Quotas
    STORAGE_BACKEND: str = "local"  # "local" or "r2"
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET: str = "anystream-files"
    STORAGE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../storage/tmp"))
    MAX_FILE_SIZE_BYTES: int = 2 * 1024 * 1024 * 1024  # 2 GB
    MIN_FREE_DISK_BYTES: int = 1024 * 1024 * 1024  # 1 GB
    MAX_VIDEO_DURATION_SECONDS: int = 10800  # 3 hours
    JOB_EXPIRY_MINUTES: int = 30  # Automatic file eviction window (30 minutes)
    FILE_CLEANUP_INTERVAL_SECONDS: int = 300  # 5 minutes

    # Rate Limiting & Abuse Prevention
    GLOBAL_CONCURRENCY_CAP: int = 20
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
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Refuses to start in production if insecure default secrets are used."""
        if self.ENVIRONMENT == "production":
            insecure_secret_markers = [
                "insecure", "change-in-production", "secret-key", "default", "123456"
            ]
            if len(self.SECRET_KEY) < 32 or any(m in self.SECRET_KEY.lower() for m in insecure_secret_markers):
                raise ValueError(
                    "FATAL SECURITY: In production mode, SECRET_KEY must be a cryptographically strong secret with >= 32 characters."
                )
            if len(self.IP_HASH_SALT) < 16 or "dev-salt" in self.IP_HASH_SALT.lower():
                raise ValueError(
                    "FATAL SECURITY: In production mode, IP_HASH_SALT must be configured with >= 16 characters and not use dev default."
                )
            if self.ADMIN_API_KEY and "default" in self.ADMIN_API_KEY.lower():
                raise ValueError(
                    "FATAL SECURITY: In production mode, ADMIN_API_KEY must not use default credentials."
                )
        return self


settings = Settings()

