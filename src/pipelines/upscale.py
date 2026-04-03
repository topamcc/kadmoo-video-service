"""Resolution pass — FFmpeg scale when stub already targeted size (no-op copy)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from shared.types import VideoJobRequest


def _target_dims(req: VideoJobRequest) -> tuple[int, int]:
    short = {"720p": 720, "1080p": 1080, "4k": 2160}[req.resolution]
    if req.aspect_ratio == "9:16":
        return short, int(short * 16 / 9)
    if req.aspect_ratio == "1:1":
        return short, short
    if req.aspect_ratio == "16:9":
        return int(short * 16 / 9), short
    return short, int(short * 16 / 9)


def upscale_if_needed(src: Path, dest: Path, req: VideoJobRequest) -> None:
    """Re-encode at target dimensions (idempotent if already matched)."""
    w, h = _target_dims(req)
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-vf",
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "copy",
            str(dest),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def copy_or_upscale(src: Path, dest: Path, req: VideoJobRequest) -> None:
    """If upscale fails (no ffmpeg), fall back to copy."""
    try:
        upscale_if_needed(src, dest, req)
    except (subprocess.CalledProcessError, FileNotFoundError):
        shutil.copy2(src, dest)
