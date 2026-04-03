"""Optional crossfade between silent scene segments (FFmpeg xfade) — smooth_scene_transitions."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


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


def concat_with_optional_crossfade(
    segments: list[Path],
    out_mp4: Path,
    *,
    fade_sec: float = 0.35,
) -> None:
    """Chain FFmpeg xfade across segment videos. Falls back to concat demuxer on failure."""
    if not segments:
        raise ValueError("no segments")
    if len(segments) == 1:
        shutil.copy2(segments[0], out_mp4)
        return

    fade_sec = max(0.05, min(1.5, float(fade_sec)))
    durations = [_probe_duration(p) for p in segments]
    if any(d <= 0 for d in durations):
        _concat_demuxer(segments, out_mp4)
        return

    inputs: list[str] = []
    for p in segments:
        inputs.extend(["-i", str(p)])

    acc = durations[0]
    parts: list[str] = []
    cur = "[0:v]"
    for i in range(1, len(segments)):
        off = max(0.0, acc - fade_sec)
        out_l = f"[xf{i}]"
        parts.append(f"{cur}[{i}:v]xfade=transition=fade:duration={fade_sec}:offset={off}{out_l}")
        cur = out_l
        acc = acc + durations[i] - fade_sec

    fc = ";".join(parts)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        fc,
        "-map",
        cur,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-an",
        str(out_mp4),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        _concat_demuxer(segments, out_mp4)


def _concat_demuxer(segments: list[Path], out_mp4: Path) -> None:
    work = out_mp4.parent
    lst = work / "ltx_concat_fallback.txt"
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
