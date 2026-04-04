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
    ltx_python_bin: str = Field(
        default="",
        alias="LTX_PYTHON_BIN",
        description="Python with torch+diffusers for scripts/ltx_i2v_scene.py (e.g. LTX-2 .venv)",
    )
    ltx_hf_model_id: str = Field(
        default="Lightricks/LTX-2.3",
        alias="LTX_HF_MODEL_ID",
        description="Hugging Face model id fallback when using from_pretrained",
    )
    ltx_use_spatial_upscaler: bool = Field(
        default=False,
        alias="LTX_USE_SPATIAL_UPSCALER",
        description="If true and LTX_UPSCALER_PATH set, run spatial upscale subprocess after concat",
    )
    replicate_api_token: str = Field(
        default="",
        alias="REPLICATE_API_TOKEN",
        description="Optional: MusicGen BGM via Replicate",
    )
    ltx_repo_path: str = Field(
        default="",
        alias="LTX_REPO_PATH",
        description="Path to cloned Lightricks/LTX-2 repo for optional LoRA training jobs",
    )
    ltx_official_i2v_module: str = Field(
        default="",
        alias="LTX_OFFICIAL_I2V_MODULE",
        description=(
            "If set with LTX_REPO_PATH, try `python -m <module>` for I2V before Diffusers script "
            "(module name depends on upstream LTX-2 version)"
        ),
    )
    ltx_distilled_lora_path: str = Field(
        default="",
        alias="LTX_DISTILLED_LORA_PATH",
        description="Optional distilled LoRA .safetensors for two-stage / official pipelines",
    )
    ltx_gemma_root: str = Field(
        default="",
        alias="LTX_GEMMA_ROOT",
        description="Root directory of Gemma text encoder files (required for official ltx_pipelines CLI)",
    )
    ltx_use_official_pipelines: bool = Field(
        default=False,
        alias="LTX_USE_OFFICIAL_PIPELINES",
        description=(
            "If true, scripts prefer Lightricks `python -m ltx_pipelines.*` when assets are set "
            "(see docs/LTX2-ASSET-CHECKLIST.md)"
        ),
    )
    ltx_distilled_lora_strength: float = Field(
        default=0.8,
        ge=0.0,
        le=2.0,
        alias="LTX_DISTILLED_LORA_STRENGTH",
        description="Strength passed to official two-stage --distilled-lora PATH STRENGTH",
    )
    ltx_multi_keyframe_strategy: str = Field(
        default="concat",
        alias="LTX_MULTI_KEYFRAME_STRATEGY",
        description="concat (default) | keyframe_interpolation — see docs/LTX-KF-A2V-EVAL.md",
    )
    ltx_audio_to_video_pipeline: str = Field(
        default="i2v_mux",
        alias="LTX_AUDIO_TO_VIDEO_PIPELINE",
        description="i2v_mux (silent I2V + ffmpeg mux) | a2vid_two_stage — official A2V when assets allow",
    )
    ltx_trainer_config_template: str = Field(
        default="",
        alias="LTX_TRAINER_CONFIG_TEMPLATE",
        description="YAML file with {data_dir} and {output_dir} placeholders for ltx-trainer",
    )
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
