"""POST /training/lora — enqueue LoRA training (optional LTX-2 trainer)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from api.deps import verify_api_key
from config import get_settings
from worker.celery_app import app as celery_app

router = APIRouter(prefix="/training", tags=["training"])


@router.post(
    "/lora",
    dependencies=[Depends(verify_api_key)],
    status_code=status.HTTP_202_ACCEPTED,
)
async def train_lora(
    lora_zip: UploadFile = File(...),
    site_id: str | None = Form(default=None),
    callback_url: str | None = Form(default=None),
    lora_kind: str = Form(default="style"),
    trigger_word: str | None = Form(default=None),
) -> dict:
    if not lora_zip.filename or not lora_zip.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Expected a .zip file")

    settings = get_settings()
    work = Path(settings.temp_dir) / "training_uploads"
    work.mkdir(parents=True, exist_ok=True)
    tid = uuid.uuid4().hex
    dest = work / f"{tid}.zip"
    content = await lora_zip.read()
    if len(content) > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Zip too large (max 500MB)")
    dest.write_bytes(content)

    celery_app.send_task(
        "worker.training_tasks.train_ltx_lora",
        args=[str(dest), tid],
        kwargs={
            "site_id": site_id,
            "callback_url": callback_url,
            "lora_kind": (lora_kind or "style").strip() or "style",
            "trigger_word": trigger_word,
        },
        queue="video-jobs",
        task_id=f"train-lora-{tid}",
    )
    return {"status": "queued", "task_id": f"train-lora-{tid}", "upload_path": str(dest)}
