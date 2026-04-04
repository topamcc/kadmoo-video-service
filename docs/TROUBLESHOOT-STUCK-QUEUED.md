# Jobs stuck `queued` / 0% — RunPod & Celery

## What it means

- **Supabase `video_jobs.status = queued`** with `progress_message` like **"בתור"** means the Next.js app successfully called `POST /jobs` on **kadmoo-video-service** and the job was **enqueued in Redis**.
- If nothing ever moves past 0%, the **Celery worker** is usually **not running** or cannot reach Redis.

A **generic RunPod PyTorch + Jupyter** pod does **not** run this stack. Paying for GPU on Jupyter does **not** start `video-api`, `redis`, or `video-worker`.

## Checklist (on the same host as `VIDEO_SERVICE_URL`)

### 1. API and `/health`

```bash
curl -s http://127.0.0.1:4100/health
```

Expect JSON with `redis: true`, `queue_depth`, `status`.

- If connection refused → FastAPI is not listening on **4100** or you are on the wrong pod.
- **RunPod:** expose **HTTP port 4100** publicly so Vercel can reach `VIDEO_SERVICE_URL`.

### 2. Redis

If `redis: false` in `/health`, fix `REDIS_URL` and ensure the `redis` container (or process) is up.

### 3. Celery worker (required)

**Docker:**

```bash
docker compose ps
docker compose logs -f video-worker --tail 100
```

Both **`video-api`** and **`video-worker`** must be running. Only API without worker → jobs sit in Redis forever.

**Native (RunPod without Docker daemon):** see [RUNPOD-NATIVE.md](./RUNPOD-NATIVE.md) and [RUNPOD-ONE-PAGE-HE.md](./RUNPOD-ONE-PAGE-HE.md) — start worker with:

`celery -A worker.celery_app worker -l info -c 1 -Q video-jobs`

### 4. After the worker is healthy

- Create a **new** job from Studio, or use **Retry** in Kadmoo Admin (if deployed) on a failed row.
- Ensure Vercel has `NEXT_PUBLIC_APP_URL` (HTTPS) and matching `VIDEO_SERVICE_WEBHOOK_SECRET` / `WEBHOOK_HMAC_SECRET` so progress webhooks apply.

## Kadmoo Admin UI

In the app (admin): **Video GPU service** page shows `/health` plus **queue_depth** and hints when the queue is backing up.
