#!/usr/bin/env bash
# Start Redis (if needed), API + Celery worker in background (RunPod without Docker).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/*.sh 2>/dev/null || true

ENV_FILE="$ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing .env — run: ./scripts/runpod-bootstrap.sh"
  exit 1
fi

PORT=4100
if [[ -f "$ENV_FILE" ]]; then
  _port_line="$(grep -E '^PORT=' "$ENV_FILE" | tail -1 || true)"
  if [[ -n "$_port_line" ]]; then
    PORT="${_port_line#PORT=}"
    PORT="${PORT//$'\r'/}"
    PORT="${PORT// /}"
  fi
fi
export PORT

# Minimal validation (placeholders from .env.example)
if grep -qE '^API_KEY=(vs_change_me|)$' "$ENV_FILE" 2>/dev/null; then
  echo "ERROR: Set API_KEY in .env (must match VIDEO_SERVICE_API_KEY on Vercel)."
  exit 1
fi
if grep -qE '^WEBHOOK_HMAC_SECRET=(whsec_change_me|)$' "$ENV_FILE" 2>/dev/null; then
  echo "ERROR: Set WEBHOOK_HMAC_SECRET in .env (must match VIDEO_SERVICE_WEBHOOK_SECRET on Vercel)."
  exit 1
fi
if grep -q 'YOUR_PROJECT\.supabase\.co' "$ENV_FILE" 2>/dev/null; then
  echo "ERROR: Replace SUPABASE_URL placeholder in .env with your real project URL."
  exit 1
fi

API_PID_FILE="/tmp/kadmoo-runpod-api.pid"
WORKER_PID_FILE="/tmp/kadmoo-runpod-worker.pid"
API_LOG="/tmp/kadmoo-video-api.log"
WORKER_LOG="/tmp/kadmoo-video-worker.log"

if redis-cli ping 2>/dev/null | grep -q PONG; then
  echo "==> Redis already running"
else
  echo "==> Starting Redis..."
  redis-server --daemonize yes
  sleep 1
  redis-cli ping
fi

stop_one() {
  local f="$1"
  if [[ -f "$f" ]]; then
    local pid
    pid="$(cat "$f")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "==> Stopping old process pid=$pid ($f)"
      kill "$pid" 2>/dev/null || true
      sleep 1
    fi
    rm -f "$f"
  fi
}

stop_one "$API_PID_FILE"
stop_one "$WORKER_PID_FILE"

echo "==> Starting video API (uvicorn)..."
nohup "$ROOT/scripts/run-native-api.sh" >>"$API_LOG" 2>&1 &
echo $! >"$API_PID_FILE"

echo "==> Starting Celery worker..."
nohup "$ROOT/scripts/run-native-worker.sh" >>"$WORKER_LOG" 2>&1 &
echo $! >"$WORKER_PID_FILE"

sleep 2
if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null; then
  echo "==> OK: http://127.0.0.1:${PORT}/health"
  curl -s "http://127.0.0.1:${PORT}/health" | head -c 200
  echo ""
else
  echo "WARN: /health not ready yet — check $API_LOG"
  tail -20 "$API_LOG" || true
fi

echo ""
echo "PIDs: API=$(cat "$API_PID_FILE") worker=$(cat "$WORKER_PID_FILE")"
echo "Logs: $API_LOG | $WORKER_LOG"
echo "Stop:  $ROOT/scripts/runpod-stop.sh"
echo "Status: $ROOT/scripts/runpod-status.sh"
