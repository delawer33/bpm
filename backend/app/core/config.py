from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "BPM"
    debug: bool = True

    # Database
    db_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bpm"
    redis_url: str = "redis://redis:6379/0"

    # RabbitMQ
    rabbitmq_url: str = "amqp://rabbit:rabbit@localhost:5672/%2F"
    rabbitmq_exchange: str = "bpm.events"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "bpm-tracks"
    minio_secure: bool = False
    minio_presign_expire_seconds: int = 3600
    
    minio_max_preview_bytes: int = 10 * 1024 * 1024   # 10 MB
    minio_max_main_bytes: int = 50 * 1024 * 1024    # 50 MB
    minio_max_stems_bytes: int = 400 * 1024 * 1024  # 400 MB
    minio_max_image_bytes: int = 5 * 1024 * 1024    # 5 MB

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours (access token)
    jwt_refresh_expire_days: int = 7  # 7 days (refresh token)


@lru_cache
def get_settings() -> Settings:
    return Settings()
