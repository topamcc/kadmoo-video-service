#!/usr/bin/env bash
# One-shot setup on RunPod (or any Ubuntu root shell): packages, clone/pull, pip, .env template, Redis URL for native.
set -euo pipefail

WORKSPACE_PARENT="${KADMOO_WORKSPACE_PARENT:-/workspace}"
REPO_DIR_NAME="${KADMOO_REPO_DIR:-kadmoo-video-service}"
REPO_URL="${KADMOO_VIDEO_SERVICE_GIT_URL:-https://github.com/topamcc/kadmoo-video-service.git}"
TARGET="${WORKSPACE_PARENT}/${REPO_DIR_NAME}"

echo "==> [kadmoo] apt packages (redis, ffmpeg, python, git, nano)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq redis-server ffmpeg curl python3-pip git nano ca-certificates

mkdir -p "$WORKSPACE_PARENT"
if [[ ! -d "$TARGET/.git" ]]; then
  echo "==> [kadmoo] cloning $REPO_URL -> $TARGET"
  git clone "$REPO_URL" "$TARGET"
else
  echo "==> [kadmoo] git pull in $TARGET"
  git -C "$TARGET" pull --ff-only origin main || git -C "$TARGET" pull --ff-only
fi

cd "$TARGET"
chmod +x scripts/*.sh 2>/dev/null || true

echo "==> [kadmoo] pip install..."
pip3 install -q -r requirements.txt

if [[ ! -f .env ]]; then
  echo "==> [kadmoo] creating .env from .env.example"
  cp .env.example .env
fi

# Native RunPod: Redis on localhost (example file points at docker hostname "redis")
if grep -q '^REDIS_URL=redis://redis:6379/0' .env 2>/dev/null; then
  sed -i 's|^REDIS_URL=redis://redis:6379/0|REDIS_URL=redis://127.0.0.1:6379/0|' .env
  echo "==> [kadmoo] set REDIS_URL=redis://127.0.0.1:6379/0 for native mode"
fi

echo ""
echo "=== Bootstrap done ==="
echo "Project: $TARGET"
echo "Next:"
echo "  1) Edit secrets:  nano $TARGET/.env"
echo "     (API_KEY, WEBHOOK_HMAC_SECRET, SUPABASE_*, ELEVENLABS_*, ...)"
echo "  2) Start services:  cd $TARGET && ./scripts/runpod-start.sh"
echo "Full guide: docs/RUNPOD-ONE-PAGE-HE.md"
echo ""
