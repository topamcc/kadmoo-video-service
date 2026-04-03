"""Redis-backed job status for GET /jobs/{id}/status."""

from __future__ import annotations

import json
from typing import Any

import redis

from config import get_settings
from shared.types import VideoJobStatus


def _redis_client() -> redis.Redis:
    s = get_settings()
    return redis.from_url(s.redis_url, decode_responses=True)


def job_key(job_id: str) -> str:
    return f"video:job:{job_id}"


def save_job_status(status: VideoJobStatus) -> None:
    r = _redis_client()
    r.set(job_key(status.job_id), status.model_dump_json(), ex=86400 * 7)


def load_job_status(job_id: str) -> VideoJobStatus | None:
    r = _redis_client()
    raw = r.get(job_key(job_id))
    if not raw:
        return None
    return VideoJobStatus.model_validate_json(raw)


def queue_depth() -> int:
    """Approximate Celery queue length (named queue video-jobs)."""
    try:
        r = _redis_client()
        return int(r.llen("video-jobs") or 0)
    except redis.RedisError:
        return -1


def redis_ok() -> bool:
    try:
        r = _redis_client()
        return bool(r.ping())
    except redis.RedisError:
        return False


def merge_progress(job_id: str, updates: dict[str, Any]) -> VideoJobStatus:
    current = load_job_status(job_id)
    if not current:
        current = VideoJobStatus(job_id=job_id, status="queued", progress=0)
    data = current.model_dump()
    data.update({k: v for k, v in updates.items() if v is not None})
    merged = VideoJobStatus.model_validate(data)
    save_job_status(merged)
    return merged
