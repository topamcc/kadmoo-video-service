#!/usr/bin/env bash
# Celery worker for hosts without Docker (e.g. RunPod PyTorch pod).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"
set -a
# shellcheck disable=SC1091
[ -f .env ] && . ./.env
set +a
exec celery -A worker.celery_app worker -l info -c 1 -Q video-jobs
