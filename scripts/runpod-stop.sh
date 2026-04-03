#!/usr/bin/env bash
set -euo pipefail

API_PID_FILE="/tmp/kadmoo-runpod-api.pid"
WORKER_PID_FILE="/tmp/kadmoo-runpod-worker.pid"

for f in "$API_PID_FILE" "$WORKER_PID_FILE"; do
  if [[ -f "$f" ]]; then
    pid="$(cat "$f")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "Stopping pid $pid ($f)"
      kill "$pid" 2>/dev/null || true
    fi
    rm -f "$f"
  fi
done

echo "Stopped API + worker (best-effort). Redis left running."
