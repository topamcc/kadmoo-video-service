"""Download LoRA / weight URLs into a job work directory."""

from __future__ import annotations

from pathlib import Path

import httpx

from shared.errors import VideoJobError


def download_optional(url: str | None, dest: Path) -> Path | None:
    if not url or not str(url).strip():
        return None
    u = str(url).strip()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=300.0, follow_redirects=True) as client:
        r = client.get(u)
        if not r.is_success:
            raise VideoJobError(f"Failed to download LoRA weights: {u} ({r.status_code})")
    dest.write_bytes(r.content)
    return dest
