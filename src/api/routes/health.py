"""GET /health — Redis, optional GPU, queue depth."""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Literal

from fastapi import APIRouter

from config import get_settings
from job_state import queue_depth, redis_ok

router = APIRouter(tags=["health"])


def _nvidia_gpu_mem() -> tuple[float, float] | None:
    """Returns (used_gb, total_gb) or None if unavailable."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=5,
        )
        line = out.strip().splitlines()[0]
        parts = re.split(r",\s*", line)
        if len(parts) >= 2:
            used_mb = float(parts[0])
            total_mb = float(parts[1])
            return used_mb / 1024, total_mb / 1024
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError):
        pass
    return None


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    r_ok = redis_ok()
    q = queue_depth()
    gpu = _nvidia_gpu_mem()

    status: Literal["ok", "degraded", "unhealthy"] = "ok"
    if not r_ok:
        status = "unhealthy"
    elif q < 0:
        status = "degraded"

    body: dict = {
        "status": status,
        "redis": r_ok,
        "queue_depth": max(0, q) if q >= 0 else 0,
        "uptime_probe": True,
        "ltx_stub_mode": settings.ltx_stub_mode,
        "ltx_model_configured": bool(settings.ltx_model_path.strip()),
        "ltx_repo_configured": bool(settings.ltx_repo_path.strip()),
        "ltx_python_bin_set": bool(settings.ltx_python_bin.strip()),
    }
    if gpu:
        body["gpu_memory_used_gb"] = round(gpu[0], 2)
        body["gpu_memory_total_gb"] = round(gpu[1], 2)
    else:
        body["gpu_memory_used_gb"] = 0.0
        body["gpu_memory_total_gb"] = 0.0

    return body
