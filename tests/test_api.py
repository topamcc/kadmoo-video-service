"""API smoke tests (no Redis/Celery required for import errors)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure src on path
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")
os.environ.setdefault("WEBHOOK_HMAC_SECRET", "secret")


def test_health_route_registered():
    from main import app

    paths = [getattr(r, "path", None) for r in app.routes]
    assert "/health" in paths

