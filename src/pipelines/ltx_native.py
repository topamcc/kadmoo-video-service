"""Run LTX-2 image-to-video per scene via subprocess (isolated GPU Python env)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from config import get_settings
from pipelines.identity import build_visual_prompt
from pipelines.lora_cache import download_optional
from shared.errors import VideoJobError
from shared.types import SceneConfig, VideoJobRequest

from pipelines.scene_crossfade import concat_with_optional_crossfade


def _repo_root() -> Path:
    # src/pipelines/ltx_native.py -> repo root is parents[2]
    return Path(__file__).resolve().parents[2]


def _script_path() -> Path:
    return _repo_root() / "scripts" / "ltx_i2v_scene.py"


def _valid_frame_count(n: int) -> int:
    """LTX docs: num_frames = 8n + 1."""
    n = max(9, min(257, n))
    return ((n - 1) // 8) * 8 + 1


def _dims(req: VideoJobRequest) -> tuple[int, int]:
    short = {"720p": 720, "1080p": 1080, "4k": 2160}[req.resolution]
    if req.aspect_ratio == "9:16":
        w, h = short, int(short * 16 / 9)
    elif req.aspect_ratio == "4:5":
        w, h = short, int(short * 5 / 4)
    elif req.aspect_ratio == "1:1":
        w, h = short, short
    elif req.aspect_ratio == "16:9":
        w, h = int(short * 16 / 9), short
    else:
        w, h = short, int(short * 16 / 9)
    # divisible by 32
    w = max(32, (w // 32) * 32)
    h = max(32, (h // 32) * 32)
    return w, h


def render_ltx_i2v_multiscene(
    req: VideoJobRequest,
    work_dir: Path,
    keyframe_paths: list[Path],
    scenes: list[SceneConfig],
    style_lora: Path | None,
    avatar_lora: Path | None,
) -> list[Path]:
    settings = get_settings()
    script = _script_path()
    if not script.is_file():
        raise VideoJobError(f"LTX script missing: {script}")

    py = settings.ltx_python_bin.strip() or sys.executable
    ckpt = settings.ltx_model_path.strip()
    if not ckpt:
        raise VideoJobError("LTX_MODEL_PATH is required for native render")

    w, h = _dims(req)
    fps = float(min(req.fps, 30))
    segments: list[Path] = []

    for i, kf in enumerate(keyframe_paths):
        sc = scenes[i] if i < len(scenes) else scenes[-1]
        dur = max(0.5, float(sc.duration_s))
        raw_frames = int(dur * fps)
        num_frames = _valid_frame_count(raw_frames)
        seg = work_dir / f"ltx_seg_{i}.mp4"
        prompt = build_visual_prompt(
            base=sc.visual_prompt_en or "cinematic commercial camera motion",
            sound_hint=sc.sound_intent_en,
            style_trigger=req.style_lora_trigger_word,
            avatar_trigger=req.avatar_lora_trigger_word,
            identity_lock=req.identity_lock,
            photo_url=req.photo_url,
        )
        cmd = [
            py,
            str(script),
            "--image",
            str(kf),
            "--prompt",
            prompt,
            "--output",
            str(seg),
            "--checkpoint",
            ckpt,
            "--model-id",
            settings.ltx_hf_model_id,
            "--width",
            str(w),
            "--height",
            str(h),
            "--num-frames",
            str(num_frames),
            "--fps",
            str(fps),
            "--seed",
            str(42 + i),
            "--pipeline-mode",
            req.pipeline_mode,
        ]
        if req.enhance_prompt:
            cmd.append("--enhance-prompt")
        # Prefer avatar LoRA for people shots, else style
        lora = avatar_lora or style_lora
        if lora and lora.is_file():
            cmd.extend(["--lora-path", str(lora), "--lora-scale", str(req.lora_strength)])
        env = os.environ.copy()
        if settings.ltx_repo_path.strip():
            env["LTX_REPO_PATH"] = settings.ltx_repo_path.strip()
        if settings.ltx_official_i2v_module.strip():
            env["LTX_OFFICIAL_I2V_MODULE"] = settings.ltx_official_i2v_module.strip()
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=3600, env=env)
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or str(e))[:4000]
            raise VideoJobError(f"LTX subprocess failed: {err}") from e
        except FileNotFoundError as e:
            raise VideoJobError(f"LTX python not found: {py}") from e
        segments.append(seg)
    return segments


def concat_segments(
    work_dir: Path,
    segments: list[Path],
    out_mp4: Path,
    *,
    crossfade: bool = False,
    fade_sec: float = 0.35,
) -> None:
    if crossfade and len(segments) > 1:
        concat_with_optional_crossfade(segments, out_mp4, fade_sec=fade_sec)
        return
    lst = work_dir / "ltx_concat.txt"
    lst.write_text("\n".join(f"file '{p.as_posix()}'" for p in segments), encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            str(out_mp4),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
