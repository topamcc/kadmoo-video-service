"""Environment configuration (Pydantic Settings)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = Field(default="", description="X-API-Key for incoming requests")
    host: str = "0.0.0.0"
    port: int = 4100
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    webhook_hmac_secret: str = Field(default="", alias="WEBHOOK_HMAC_SECRET")

    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_storage_bucket: str = Field(default="studio-assets", alias="SUPABASE_STORAGE_BUCKET")

    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    elevenlabs_default_voice_id: str = Field(
        default="",
        alias="ELEVENLABS_DEFAULT_VOICE_ID",
        description="Used when no voice_sample_url and no cached voice_id",
    )

    ltx_model_path: str = Field(default="", alias="LTX_MODEL_PATH")
    ltx_upscaler_path: str = Field(default="", alias="LTX_UPSCALER_PATH")
    fp8_quantization: bool = Field(default=False, alias="FP8_QUANTIZATION")
    ltx_stub_mode: bool = Field(
        default=True,
        alias="LTX_STUB_MODE",
        description="If true, use FFmpeg slideshow + audio instead of real LTX-2 (dev / no GPU)",
    )

    celery_broker_url: str | None = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(default=None, alias="CELERY_RESULT_BACKEND")

    job_timeout_seconds: int = Field(default=600, alias="JOB_TIMEOUT_SECONDS")
    temp_dir: str = Field(default="/tmp/kadmoo-video", alias="TEMP_DIR")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def celery_broker_url(settings: Settings) -> str:
    return settings.celery_broker_url or settings.redis_url


def celery_result_backend(settings: Settings) -> str:
    return settings.celery_result_backend or settings.redis_url
