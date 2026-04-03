"""ElevenLabs v3 TTS + optional IVC from voice sample URL."""

from __future__ import annotations

from pathlib import Path

import httpx

from config import get_settings
from shared.errors import VideoJobError

ELEVEN_BASE = "https://api.elevenlabs.io/v1"


def _headers() -> dict[str, str]:
    s = get_settings()
    if not s.elevenlabs_api_key:
        raise VideoJobError("ELEVENLABS_API_KEY is not configured")
    return {
        "xi-api-key": s.elevenlabs_api_key,
    }


def download_bytes(url: str) -> bytes:
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        r = client.get(url)
        if not r.is_success:
            raise VideoJobError(f"Failed to download {url}: {r.status_code}")
        return r.content


def clone_voice_from_sample(*, name: str, sample_url: str) -> str:
    """Instant voice clone from audio URL; returns voice_id."""
    audio = download_bytes(sample_url)
    headers = _headers()
    files = {
        "files": ("sample.mp3", audio, "application/octet-stream"),
    }
    data = {"name": name[:80]}
    with httpx.Client(timeout=180.0) as client:
        r = client.post(
            f"{ELEVEN_BASE}/voices/add",
            headers=headers,
            data=data,
            files=files,
        )
        if not r.is_success:
            raise VideoJobError(f"ElevenLabs voice clone failed: {r.status_code} {r.text}")
        body = r.json()
        vid = body.get("voice_id")
        if not vid:
            raise VideoJobError("ElevenLabs clone: missing voice_id in response")
        return str(vid)


def synthesize_speech_hebrew(*, voice_id: str, text: str, out_path: Path) -> None:
    """Text-to-speech with eleven_v3 model (Hebrew + emotional tags in text)."""
    headers = _headers()
    headers["Content-Type"] = "application/json"
    payload = {
        "text": text,
        "model_id": "eleven_v3",
    }
    params = {"output_format": "mp3_44100_128"}
    url = f"{ELEVEN_BASE}/text-to-speech/{voice_id}"
    with httpx.Client(timeout=300.0) as client:
        r = client.post(url, headers=headers, json=payload, params=params)
        if not r.is_success:
            raise VideoJobError(f"ElevenLabs TTS failed: {r.status_code} {r.text}")
        out_path.write_bytes(r.content)


def resolve_voice_id(
    *,
    existing_voice_id: str | None,
    voice_sample_url: str | None,
    job_id: str,
) -> str:
    if existing_voice_id:
        return existing_voice_id
    s = get_settings()
    if voice_sample_url:
        try:
            return clone_voice_from_sample(
                name=f"kadmoo-{job_id[:8]}",
                sample_url=voice_sample_url,
            )
        except VideoJobError:
            if s.elevenlabs_default_voice_id:
                return s.elevenlabs_default_voice_id
            raise
    if s.elevenlabs_default_voice_id:
        return s.elevenlabs_default_voice_id
    raise VideoJobError(
        "No voice: provide voice_id, voice_sample_url, or set ELEVENLABS_DEFAULT_VOICE_ID",
    )


def mp3_to_wav_if_needed(mp3_path: Path, wav_path: Path) -> None:
    """Optional: convert MP3 to WAV via ffmpeg for engines that need PCM."""
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(mp3_path),
            str(wav_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
