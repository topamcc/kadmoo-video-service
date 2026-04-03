"""LTX-2 integration + stub mode (FFmpeg slideshow + audio)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import httpx

from config import get_settings
from pipelines.identity import describe_identity_prompt
from pipelines.lora_cache import download_optional
from pipelines.ltx_native import concat_segments, render_ltx_i2v_multiscene
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


def _probe_audio_duration(audio_mp3: Path) -> float:
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
                str(audio_mp3),
            ],
            text=True,
        )
        return float(json.loads(out).get("format", {}).get("duration") or 5.0)
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        KeyError,
        ValueError,
        json.JSONDecodeError,
    ):
        return 5.0


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


def _mux_video_audio(silent_video: Path, audio_mp3: Path, out_video: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(silent_video),
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


def _prepare_keyframes(req: VideoJobRequest, work_dir: Path) -> tuple[list[Path], list[SceneConfig]]:
    images_dir = work_dir / "kf_dl"
    images_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
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
    for i, url in enumerate(req.keyframe_urls):
        ext = ".png" if ".png" in url.lower() else ".jpg"
        p = images_dir / f"kf{i}{ext}"
        _download_file(url, p)
        paths.append(p)
    return paths, scenes


def run_ltx_pipeline(
    req: VideoJobRequest,
    work_dir: Path,
    audio_mp3: Path,
    out_video: Path,
) -> None:
    """
    Stub slideshow when LTX_STUB_MODE or no LTX_MODEL_PATH; else native I2V subprocess per scene.
    """
    settings = get_settings()
    _ = describe_identity_prompt(req.photo_url, req.identity_lock)

    if settings.ltx_stub_mode or not settings.ltx_model_path.strip():
        render_stub_slideshow(req, work_dir, audio_mp3, out_video)
        return

    key_paths, scenes = _prepare_keyframes(req, work_dir)
    style_lora = download_optional(req.style_lora_url, work_dir / "loras" / "style.safetensors")
    avatar_lora = download_optional(req.avatar_lora_url, work_dir / "loras" / "avatar.safetensors")

    if req.render_mode == "audio_to_video":
        # Single clip driven by narration length (first keyframe)
        dur = _probe_audio_duration(audio_mp3)
        scenes_a2v = [
            SceneConfig(
                visual_prompt_en=scenes[0].visual_prompt_en if scenes else "natural speaking, subtle head motion",
                sound_intent_en=scenes[0].sound_intent_en if scenes else "dialogue",
                duration_s=max(1.0, dur),
                keyframe_index=0,
            )
        ]
        segs = render_ltx_i2v_multiscene(
            req,
            work_dir,
            [key_paths[0]],
            scenes_a2v,
            style_lora,
            avatar_lora,
        )
        silent = work_dir / "ltx_silent.mp4"
        concat_segments(
            work_dir,
            segs,
            silent,
            crossfade=req.smooth_scene_transitions,
        )
        _mux_video_audio(silent, audio_mp3, out_video)
        return

    segs = render_ltx_i2v_multiscene(req, work_dir, key_paths, scenes, style_lora, avatar_lora)
    silent = work_dir / "ltx_silent.mp4"
    concat_segments(
        work_dir,
        segs,
        silent,
        crossfade=req.smooth_scene_transitions,
    )
    _mux_video_audio(silent, audio_mp3, out_video)
