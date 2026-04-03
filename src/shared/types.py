"""Pydantic models: API contract (mirror TypeScript external-video/types)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SceneConfig(BaseModel):
    visual_prompt_en: str
    sound_intent_en: str = "subtle ambience"
    duration_s: float = 5.0
    keyframe_index: int | None = None


RenderMode = Literal["image_to_video", "audio_to_video"]

# diffusers_i2v = scripts/ltx_i2v_scene.py; official_* tries LTX_OFFICIAL_I2V_MODULE from LTX_REPO_PATH first
PipelineMode = Literal["diffusers_i2v", "distilled_fast", "two_stage_hq"]


class VideoJobRequest(BaseModel):
    job_id: str
    site_id: str
    created_by: str = Field(description="Supabase auth user id for studio_assets row")
    callback_url: str
    voice_sample_url: str | None = None
    voice_id: str | None = None
    script_he: str
    photo_url: str
    keyframe_urls: list[str]
    logo_url: str | None = None
    scenes: list[SceneConfig] = Field(default_factory=list)
    resolution: Literal["720p", "1080p", "4k"] = "1080p"
    fps: int = 50
    aspect_ratio: Literal["9:16", "1:1", "16:9", "4:5"] = "9:16"
    generate_bgm: bool = True
    identity_lock: bool = True
    template_id: str = "smb-vo-external"
    site_name: str = ""
    full_narration_for_asset: str = ""
    # LoRA weights (HTTP URL to .safetensors). Flux LoRAs are not LTX-compatible — use LTX-trained weights.
    style_lora_url: str | None = None
    avatar_lora_url: str | None = None
    style_lora_trigger_word: str = ""
    avatar_lora_trigger_word: str = ""
    lora_strength: float = Field(default=1.0, ge=0.0, le=2.0)
    render_mode: RenderMode = "image_to_video"
    pipeline_mode: PipelineMode = "diffusers_i2v"
    enhance_prompt: bool = False
    smooth_scene_transitions: bool = False


class VideoJobStatus(BaseModel):
    job_id: str
    status: Literal[
        "queued",
        "cloning_voice",
        "generating_speech",
        "rendering_base",
        "upscaling",
        "postprocessing",
        "uploading",
        "completed",
        "failed",
    ]
    progress: int = 0
    message: str | None = None
    video_url: str | None = None
    storage_path: str | None = None
    file_size_bytes: int | None = None
    duration_seconds: float | None = None
    error: str | None = None
    voice_id: str | None = None


class WebhookPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event: Literal["video.progress", "video.completed", "video.failed"]
    job_id: str = Field(alias="jobId")
    timestamp: str
    data: VideoJobStatus


class CreateJobResponse(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"
