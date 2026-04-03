# kadmoo-video-service

GPU video factory for **Kadmoo Studio**: FastAPI control plane + Celery worker + Redis queue.  
Integrates with the Next.js app via **X-API-Key** and **HMAC webhooks** (same pattern as `kadmoo-crawler-service`).

## Features (v0.1)

- `POST /jobs` — enqueue async video generation
- `GET /jobs/{id}/status` — poll Redis-backed status
- `GET /health` — Redis, queue depth, optional `nvidia-smi`
- **ElevenLabs v3** Hebrew TTS + optional IVC from `voice_sample_url`
- **LTX_STUB_MODE** (default `true`): FFmpeg slideshow from Nano Banana keyframes + narration (no GPU required)
- Upload final MP4 to **Supabase** `studio-assets` bucket

## Quick start (Docker)

1. Copy `.env.example` → `.env` and fill keys.
2. `docker compose up --build`
3. API: `http://localhost:4100/docs`

Run worker + API:

```bash
docker compose up video-api video-worker redis
```

## Local Python

```bash
cd src
export PYTHONPATH=.
pip install -r ../requirements.txt
# Terminal 1
redis-server
# Terminal 2
celery -A worker.celery_app worker -l info -c 1 -Q video-jobs
# Terminal 3
uvicorn main:app --reload --host 0.0.0.0 --port 4100 --app-dir .
```

## Production LTX-2

Set `LTX_STUB_MODE=false` and install/configure **ltx-pipelines** against `LTX_MODEL_PATH` / `LTX_UPSCALER_PATH`, then implement the native branch in `pipelines/video_render.py`.

## Next.js env (Repo A)

- `VIDEO_SERVICE_URL` — public base URL of this service
- `VIDEO_SERVICE_API_KEY` — same as `API_KEY` here
- `USE_EXTERNAL_VIDEO=true`
- `VIDEO_SERVICE_WEBHOOK_SECRET` — same as `WEBHOOK_HMAC_SECRET` here
- `NEXT_PUBLIC_APP_URL` — public HTTPS URL of the app (required for `/api/webhooks/video`)

## Deploy on RunPod / GPU VPS

Step-by-step (Hebrew checklist): **[docs/DEPLOY-RUNPOD.md](./docs/DEPLOY-RUNPOD.md)**
