"""Upload final MP4 to Supabase Storage (service role)."""

from __future__ import annotations

from pathlib import Path

import httpx

from config import get_settings


def upload_video_file(
    local_path: Path,
    *,
    object_path: str,
) -> tuple[str, str, int]:
    """
    Returns (public_url, storage_path, file_size_bytes).
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for upload")

    data = local_path.read_bytes()
    size = len(data)
    bucket = settings.supabase_storage_bucket
    base = settings.supabase_url.rstrip("/")
    url = f"{base}/storage/v1/object/{bucket}/{object_path}"

    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "video/mp4",
        "apikey": settings.supabase_service_role_key,
        "x-upsert": "false",
    }

    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, content=data, headers=headers)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Supabase upload failed: {r.status_code} {r.text}")

    public = f"{base}/storage/v1/object/public/{bucket}/{object_path}"
    return public, object_path, size
