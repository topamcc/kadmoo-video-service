"""Resolution pass — optional LTX spatial upscale, then FFmpeg target dimensions."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from config import get_settings
from shared.types import VideoJobRequest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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
    """Optional neural-ish spatial upscale, then encode to target WxH."""
    settings = get_settings()
    work_src = src
    intermediate: Path | None = None
    if settings.ltx_use_spatial_upscaler and settings.ltx_upscaler_path.strip():
        script = _repo_root() / "scripts" / "ltx_spatial_upscale.py"
        intermediate = src.parent / "spatial_upscaled.mp4"
        py = settings.ltx_python_bin.strip() or sys.executable
        if script.is_file():
            subprocess.run(
                [
                    py,
                    str(script),
                    "--input",
                    str(src),
                    "--output",
                    str(intermediate),
                    "--upscaler",
                    settings.ltx_upscaler_path,
                    "--scale",
                    "2.0",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            work_src = intermediate

    w, h = _target_dims(req)
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(work_src),
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
