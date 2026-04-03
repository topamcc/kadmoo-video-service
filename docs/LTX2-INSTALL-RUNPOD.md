# LTX-2 on RunPod (GPU) — install & wire kadmoo-video-service

Official repo: [Lightricks/LTX-2](https://github.com/Lightricks/LTX-2)

## Hardware (Lightricks docs)

- **Minimum:** NVIDIA GPU with **32GB+ VRAM**, 32GB RAM, 100GB+ disk, CUDA 11.8+
- **Recommended:** A100 80GB / H100, 64GB+ RAM, 200GB+ SSD, CUDA 12.1+

## 1. Clone LTX-2 (outside or beside this repo)

```bash
cd /opt
git clone https://github.com/Lightricks/LTX-2.git
cd LTX-2
# Per upstream README: Python 3.10+, CUDA 12.7+, PyTorch ~2.7
uv sync --frozen
source .venv/bin/activate   # or: export PATH="/opt/LTX-2/.venv/bin:$PATH"
```

## 2. Download checkpoints (Hugging Face)

Login if the repo is gated:

```bash
pip install huggingface_hub
huggingface-cli login
```

Distilled (faster):

```bash
huggingface-cli download Lightricks/LTX-2.3 \
  --include "ltx-2.3-22b-distilled.safetensors" \
  --local-dir /opt/ltx-models/
```

FP8 dev (less VRAM):

```bash
huggingface-cli download Lightricks/LTX-2.3-fp8 \
  --include "ltx-2.3-22b-dev-fp8.safetensors" \
  --local-dir /opt/ltx-models/
```

Optional spatial upscaler (if you use `LTX_UPSCALER_PATH` with a real `.safetensors` file).

## 3. kadmoo-video-service `.env`

```env
LTX_STUB_MODE=false
LTX_MODEL_PATH=/opt/ltx-models/ltx-2.3-22b-distilled.safetensors
LTX_UPSCALER_PATH=/opt/ltx-models/your_spatial_upscaler.safetensors
LTX_PYTHON_BIN=/opt/LTX-2/.venv/bin/python
LTX_HF_MODEL_ID=Lightricks/LTX-2.3
FP8_QUANTIZATION=true
```

- **`LTX_PYTHON_BIN`**: Python that has **torch + diffusers** (or the LTX-2 `uv` venv). Used to run `scripts/ltx_i2v_scene.py`.
- If unset, falls back to `sys.executable` of the API/worker (usually **without** GPU torch — keep stub or set explicitly).

## 4. Optional: `requirements-ltx.txt` on the worker venv

If you run worker with the same venv as LTX:

```bash
pip install -r requirements-ltx.txt
```

## 5. Smoke test (on the pod)

```bash
export LTX_PYTHON_BIN=/opt/LTX-2/.venv/bin/python
$LTX_PYTHON_BIN /kadmoo-video-service/scripts/ltx_i2v_scene.py \
  --image /path/to/frame.jpg \
  --prompt "slow camera push in, cinematic light" \
  --output /tmp/out.mp4 \
  --checkpoint /opt/ltx-models/ltx-2.3-22b-distilled.safetensors \
  --width 512 --height 704 --num-frames 25 --fps 24
```

## 6. Run worker + API

Same as [RUNPOD-NATIVE.md](./RUNPOD-NATIVE.md); restart Celery after changing `.env`.

## Full asset checklist

See **[LTX2-ASSET-CHECKLIST.md](./LTX2-ASSET-CHECKLIST.md)** (distilled LoRA for two-stage, spatial upscaler, Gemma encoder, HF paths).

## Optional: official `ltx-pipelines` module (instead of Diffusers-only)

If `LTX_REPO_PATH` points to a clone of [Lightricks/LTX-2](https://github.com/Lightricks/LTX-2) and `LTX_OFFICIAL_I2V_MODULE` is set (example value depends on your LTX commit, e.g. a `ltx_pipelines....` module), the worker will try `python -m <module>` from that repo before falling back to `scripts/ltx_i2v_scene.py`.

```env
LTX_REPO_PATH=/opt/LTX-2
LTX_OFFICIAL_I2V_MODULE=
```

Leave `LTX_OFFICIAL_I2V_MODULE` empty to use only the Diffusers subprocess path.

## Troubleshooting

- **OOM:** use FP8 checkpoint, reduce `--num-frames`, lower resolution, set `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
- **Import errors:** align `LTX_PYTHON_BIN` with the environment where `diffusers` / LTX packages are installed.
- **Stub still runs:** `LTX_STUB_MODE=true` or empty `LTX_MODEL_PATH` forces FFmpeg slideshow.
