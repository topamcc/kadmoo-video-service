"""Optional BGM via Replicate MusicGen (or silent bed)."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import httpx

from config import get_settings
from shared.types import VideoJobRequest


def _replicate_create_prediction(
    token: str,
    *,
    version: str,
    input_payload: dict,
) -> dict:
    r = httpx.post(
        "https://api.replicate.com/v1/predictions",
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
        },
        json={"version": version, "input": input_payload},
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json()


def _replicate_wait_result(token: str, pred_url: str, timeout_s: float = 300.0) -> dict:
    deadline = time.time() + timeout_s
    headers = {"Authorization": f"Token {token}"}
    with httpx.Client(timeout=30.0) as client:
        while time.time() < deadline:
            r = client.get(pred_url, headers=headers)
            r.raise_for_status()
            body = r.json()
            st = body.get("status")
            if st == "succeeded":
                return body
            if st in ("failed", "canceled"):
                raise RuntimeError(body.get("error") or st)
            time.sleep(2.0)
    raise TimeoutError("Replicate prediction timeout")


def generate_bgm_bed(duration_s: float, work_dir: Path, req: VideoJobRequest) -> Path | None:
    """
    If REPLICATE_API_TOKEN set, run meta/musicgen small model; else return None (caller skips mix).
    """
    if not req.generate_bgm:
        return None
    settings = get_settings()
    token = settings.replicate_api_token.strip()
    if not token:
        return None
    work_dir.mkdir(parents=True, exist_ok=True)
    # musicgen-small — public version id may change; user can override via env in future
    version = "671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
    pred = _replicate_create_prediction(
        token,
        version=version,
        input_payload={
            "prompt": "subtle corporate background music, no vocals, calm",
            "duration": int(min(30, max(5, duration_s))),
        },
    )
    urls = pred.get("urls") or {}
    get_url = urls.get("get") or pred.get("url")
    if not get_url:
        return None
    result = _replicate_wait_result(token, get_url)
    out_url = (result.get("output") or [None])[0] if isinstance(result.get("output"), list) else result.get(
        "output"
    )
    if not out_url or not isinstance(out_url, str):
        return None
    dest = work_dir / "bgm.wav"
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        r = client.get(out_url)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest if dest.is_file() else None


def mix_voice_and_bgm(
    voice_mp3: Path,
    bgm_wav: Path | None,
    out_path: Path,
) -> None:
    """Sidechain-compress BGM under voice using ffmpeg filters."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not bgm_wav or not bgm_wav.is_file():
        shutil.copy2(voice_mp3, out_path)
        return
    # amix with volume adjust on bgm (simple duck substitute)
    filt = (
        f"[1:a]volume=0.15,aloop=loop=-1:size=2e+09[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(voice_mp3),
            "-i",
            str(bgm_wav),
            "-filter_complex",
            filt,
            "-map",
            "[a]",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(out_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
