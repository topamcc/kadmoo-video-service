#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-4100}"
echo "=== Redis ==="
redis-cli ping 2>/dev/null || echo "redis-cli failed"

echo ""
echo "=== Local /health ==="
curl -sS "http://127.0.0.1:${PORT}/health" || echo "(unreachable)"

echo ""
echo "=== PIDs ==="
for f in /tmp/kadmoo-runpod-api.pid /tmp/kadmoo-runpod-worker.pid; do
  if [[ -f "$f" ]]; then
    pid="$(cat "$f")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "$f -> $pid (running)"
    else
      echo "$f -> $pid (dead)"
    fi
  else
    echo "$f (missing)"
  fi
done

echo ""
echo "=== Last log lines ==="
echo "--- api ---"
tail -5 /tmp/kadmoo-video-api.log 2>/dev/null || echo "(no log)"
echo "--- worker ---"
tail -5 /tmp/kadmoo-video-worker.log 2>/dev/null || echo "(no log)"
