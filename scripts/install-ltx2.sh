#!/usr/bin/env bash
# Install LTX-2 repo + download a default checkpoint (RunPod / Ubuntu).
set -euo pipefail
LTX_ROOT="${LTX_ROOT:-/opt/LTX-2}"
MODEL_DIR="${LTX_MODEL_DIR:-/opt/ltx-models}"

echo "==> Cloning LTX-2 to $LTX_ROOT"
mkdir -p "$(dirname "$LTX_ROOT")"
if [[ ! -d "$LTX_ROOT/.git" ]]; then
  git clone https://github.com/Lightricks/LTX-2.git "$LTX_ROOT"
else
  git -C "$LTX_ROOT" pull || true
fi

echo "==> uv sync (installs LTX monorepo venv)"
if command -v uv >/dev/null 2>&1; then
  (cd "$LTX_ROOT" && uv sync --frozen)
else
  echo "Install uv: https://docs.astral.sh/uv/" >&2
  exit 1
fi

mkdir -p "$MODEL_DIR"
echo "==> Download distilled checkpoint to $MODEL_DIR (requires: huggingface-cli login if gated)"
pip install -q huggingface_hub
huggingface-cli download Lightricks/LTX-2.3 \
  --include "ltx-2.3-22b-distilled.safetensors" \
  --local-dir "$MODEL_DIR" || {
    echo "HF download failed — run: huggingface-cli login" >&2
    exit 1
  }

echo "Done. Set in kadmoo-video-service .env:"
echo "  LTX_STUB_MODE=false"
echo "  LTX_MODEL_PATH=$MODEL_DIR/ltx-2.3-22b-distilled.safetensors"
echo "  LTX_PYTHON_BIN=$LTX_ROOT/.venv/bin/python"
