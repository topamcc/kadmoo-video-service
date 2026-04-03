"""LTX-2 integration + stub mode (FFmpeg slideshow + audio)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import httpx

from config import get_settings
from pipelines.identity import describe_identity_prompt
from shared.errors import VideoJobError
from shared.types import SceneConfig, VideoJobRequest


def _download_file(url: str, dest: Path) -> None:
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        r = client.get(url)
        if not r.is_success:
            raise VideoJobError(f"Failed to download asset: {url}")
        dest.write_bytes(r.content)


def _dims_for_aspect(ar: str, resolution: str) -> tuple[int, int]:
    short = {"720p": 720, "1080p": 1080, "4k": 2160}[resolution]
    if ar == "9:16":
        return short, int(short * 16 / 9)
    if ar == "1:1":
        return short, short
    if ar == "16:9":
        return int(short * 16 / 9), short
    return short, int(short * 16 / 9)


def render_stub_slideshow(
    req: VideoJobRequest,
    work_dir: Path,
    audio_mp3: Path,
    out_video: Path,
) -> None:
    """
    Dev / no-GPU path: Ken Burns-style still sequence from keyframes + ElevenLabs audio.
    """
    if not req.keyframe_urls:
        raise VideoJobError("keyframe_urls is required")
    scenes = list(req.scenes or [])
    n_kf = len(req.keyframe_urls)
    if len(scenes) < n_kf:
        per = 5.0
        while len(scenes) < n_kf:
            scenes.append(
                SceneConfig(
                    visual_prompt_en="",
                    sound_intent_en="ambience",
                    duration_s=per,
                    keyframe_index=len(scenes),
                )
            )

    w, h = _dims_for_aspect(req.aspect_ratio, req.resolution)
    images_dir = work_dir / "frames"
    images_dir.mkdir(parents=True, exist_ok=True)

    concat_list = work_dir / "concat.txt"
    lines: list[str] = []

    for i, url in enumerate(req.keyframe_urls):
        ext = ".png" if ".png" in url.lower() else ".jpg"
        img_path = images_dir / f"kf{i}{ext}"
        _download_file(url, img_path)
        dur = scenes[i].duration_s if i < len(scenes) else 5.0
        dur = max(0.5, float(dur))
        # Single-frame video segment
        seg = work_dir / f"seg{i}.mp4"
        vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(img_path),
                "-t",
                str(dur),
                "-vf",
                vf,
                "-r",
                str(min(req.fps, 30)),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(seg),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        lines.append(f"file '{seg.as_posix()}'")

    concat_list.write_text("\n".join(lines), encoding="utf-8")
    silent = work_dir / "slideshow.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(silent),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    # Mux narration
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(silent),
            "-i",
            str(audio_mp3),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(out_video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def run_ltx_pipeline(
    req: VideoJobRequest,
    work_dir: Path,
    audio_mp3: Path,
    out_video: Path,
) -> None:
    """
    Entry: real LTX-2 when ltx_stub_mode=false and model paths are set; else stub slideshow.
    """
    settings = get_settings()
    _ = describe_identity_prompt(req.photo_url, req.identity_lock)

    if settings.ltx_stub_mode or not settings.ltx_model_path:
        render_stub_slideshow(req, work_dir, audio_mp3, out_video)
        return

    raise VideoJobError(
        "LTX-2 native path is not wired in this build. Set LTX_STUB_MODE=true "
        "or integrate ltx-pipelines against LTX_MODEL_PATH.",
    )
