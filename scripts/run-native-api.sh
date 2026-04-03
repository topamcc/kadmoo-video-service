#!/usr/bin/env bash
# FastAPI (uvicorn) for hosts without Docker (e.g. RunPod PyTorch pod).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src"
set -a
# shellcheck disable=SC1091
[ -f .env ] && . ./.env
set +a
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-4100}" --app-dir "$ROOT/src"
