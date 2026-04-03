"""POST /jobs, GET /jobs/{id}/status."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import verify_api_key
from job_state import load_job_status, merge_progress, save_job_status
from shared.types import CreateJobResponse, VideoJobRequest, VideoJobStatus
from worker.celery_app import app as celery_app

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/{job_id}/cancel", dependencies=[Depends(verify_api_key)], status_code=status.HTTP_200_OK)
def cancel_job(job_id: str) -> dict:
    """Best-effort revoke Celery task (task_id matches job_id for generate_video)."""
    celery_app.control.revoke(job_id, terminate=True, signal="SIGTERM")
    st = load_job_status(job_id)
    if st:
        merge_progress(
            job_id,
            {
                "status": "failed",
                "message": "בוטל",
                "error": "cancelled",
            },
        )
    return {"ok": True, "job_id": job_id}


@router.post("", dependencies=[Depends(verify_api_key)], status_code=status.HTTP_201_CREATED)
def create_job(body: VideoJobRequest) -> CreateJobResponse:
    initial = VideoJobStatus(
        job_id=body.job_id,
        status="queued",
        progress=0,
        message="בתור",
    )
    save_job_status(initial)
    celery_app.send_task(
        "worker.tasks.generate_video",
        args=[body.model_dump()],
        queue="video-jobs",
        task_id=body.job_id,
    )
    return CreateJobResponse(job_id=body.job_id)


@router.get("/{job_id}/status", dependencies=[Depends(verify_api_key)])
def get_status(job_id: str) -> VideoJobStatus:
    st = load_job_status(job_id)
    if not st:
        raise HTTPException(status_code=404, detail="Job not found")
    return st
