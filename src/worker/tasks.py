"""Celery task: full video pipeline + webhooks."""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from worker.celery_app import app

from config import get_settings
from job_state import save_job_status
from pipelines.bgm import generate_bgm_bed, mix_voice_and_bgm
from pipelines.postprocess import postprocess
from pipelines.tts import resolve_voice_id, synthesize_speech_hebrew
from pipelines.upscale import upscale_if_needed
from pipelines.video_render import run_ltx_pipeline
from shared.errors import VideoJobError
from shared.types import VideoJobRequest, VideoJobStatus, WebhookPayload
from storage.supabase_upload import upload_video_file
from webhook.dispatcher import send_webhook_sync


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit(req: VideoJobRequest, event: str, st: VideoJobStatus) -> None:
    save_job_status(st)
    if not req.callback_url:
        return
    secret = get_settings().webhook_hmac_secret
    if not secret:
        return
    payload = WebhookPayload(
        event=event,  # type: ignore[arg-type]
        job_id=req.job_id,
        timestamp=_utc_ts(),
        data=st,
    )
    send_webhook_sync(req.callback_url, payload)


def _probe_duration(path: Path) -> float:
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            text=True,
        )
        return float(json.loads(out).get("format", {}).get("duration") or 0)
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        KeyError,
        ValueError,
        json.JSONDecodeError,
    ):
        return 0.0


@app.task(bind=True, name="generate_video", max_retries=1, default_retry_delay=60)
def generate_video(self, payload_dict: dict) -> None:
    req = VideoJobRequest.model_validate(payload_dict)
    settings = get_settings()
    work = Path(settings.temp_dir) / req.job_id
    work.mkdir(parents=True, exist_ok=True)
    speech_mp3 = work / "speech.mp3"
    raw_video = work / "raw_render.mp4"
    scaled_video = work / "scaled.mp4"
    final_video = work / "final.mp4"

    voice_id: str | None = req.voice_id

    try:
        st = VideoJobStatus(
            job_id=req.job_id,
            status="cloning_voice",
            progress=10,
            message="משכפל קול…",
        )
        _emit(req, "video.progress", st)

        voice_id = resolve_voice_id(
            existing_voice_id=req.voice_id,
            voice_sample_url=req.voice_sample_url,
            job_id=req.job_id,
        )

        st = VideoJobStatus(
            job_id=req.job_id,
            status="generating_speech",
            progress=25,
            message="יוצר דיבור (ElevenLabs v3)…",
            voice_id=voice_id,
        )
        _emit(req, "video.progress", st)
        synthesize_speech_hebrew(voice_id=voice_id, text=req.script_he, out_path=speech_mp3)

        speech_for_render = speech_mp3
        dur_speech = _probe_duration(speech_mp3)
        if req.generate_bgm:
            st_bgm = VideoJobStatus(
                job_id=req.job_id,
                status="generating_speech",
                progress=30,
                message="מוסיף מוזיקת רקע (אופציונלי)…",
                voice_id=voice_id,
            )
            _emit(req, "video.progress", st_bgm)
            try:
                bgm = generate_bgm_bed(max(5.0, dur_speech or 10.0), work, req)
                mix_path = work / "speech_with_bgm.mp3"
                mix_voice_and_bgm(speech_mp3, bgm, mix_path)
                speech_for_render = mix_path
            except Exception:
                speech_for_render = speech_mp3

        st = VideoJobStatus(
            job_id=req.job_id,
            status="rendering_base",
            progress=45,
            message="מרנדר וידאו (LTX / מצב פיתוח)…",
            voice_id=voice_id,
        )
        _emit(req, "video.progress", st)
        run_ltx_pipeline(req, work, speech_for_render, raw_video)

        st = VideoJobStatus(
            job_id=req.job_id,
            status="upscaling",
            progress=60,
            message="המרת רזולוציה…",
            voice_id=voice_id,
        )
        _emit(req, "video.progress", st)
        upscale_if_needed(raw_video, scaled_video, req)

        st = VideoJobStatus(
            job_id=req.job_id,
            status="postprocessing",
            progress=80,
            message="עיבוד סופי…",
            voice_id=voice_id,
        )
        _emit(req, "video.progress", st)
        postprocess(scaled_video, final_video, req)

        st = VideoJobStatus(
            job_id=req.job_id,
            status="uploading",
            progress=90,
            message="מעלה ל-Supabase…",
            voice_id=voice_id,
        )
        _emit(req, "video.progress", st)

        object_path = f"videos/kadmoo-video/{req.job_id}/{uuid.uuid4().hex}.mp4"
        pub_url, spath, size = upload_video_file(final_video, object_path=object_path)
        duration = _probe_duration(final_video)

        st = VideoJobStatus(
            job_id=req.job_id,
            status="completed",
            progress=100,
            message="הושלם",
            video_url=pub_url,
            storage_path=spath,
            file_size_bytes=size,
            duration_seconds=duration,
            voice_id=voice_id,
        )
        save_job_status(st)
        _emit(req, "video.completed", st)

    except VideoJobError as e:
        st = VideoJobStatus(
            job_id=req.job_id,
            status="failed",
            progress=0,
            error=str(e),
            voice_id=voice_id,
        )
        save_job_status(st)
        _emit(req, "video.failed", st)
    except Exception as e:
        st = VideoJobStatus(
            job_id=req.job_id,
            status="failed",
            progress=0,
            error=str(e),
            voice_id=voice_id,
        )
        save_job_status(st)
        _emit(req, "video.failed", st)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
