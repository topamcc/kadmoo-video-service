# LTX-2 asset checklist (RunPod / GPU host)

Upstream reference: [Lightricks/LTX-2](https://github.com/Lightricks/LTX-2) README — required files change with releases; verify against the commit you installed.

## Core weights (pick at least one main checkpoint)

| Asset | Typical filename | Notes |
|-------|------------------|--------|
| Distilled (fast) | `ltx-2.3-22b-distilled.safetensors` | Good default for throughput |
| Dev FP8 (VRAM) | `ltx-2.3-22b-dev-fp8.safetensors` | From `Lightricks/LTX-2.3-fp8` |

Set `LTX_MODEL_PATH` to the chosen file.

## Two-stage pipelines (recommended quality)

| Asset | Typical filename | Notes |
|-------|------------------|--------|
| Spatial upscaler x2 | `ltx-2.3-spatial-upscaler-x2-1.0.safetensors` | Set `LTX_UPSCALER_PATH`, enable `LTX_USE_SPATIAL_UPSCALER=true` |
| Distilled LoRA (384) | `ltx-2.3-22b-distilled-lora-384.safetensors` | Often required for two-stage flows per upstream README |
| Spatial upscaler x1.5 | optional | Alternative to x2 |

Optional: `LTX_DISTILLED_LORA_PATH` in kadmoo-video-service `.env` when you use `two_stage_hq` / official modules that expect it.

## Text encoder

- **Gemma 3** — download all assets from the Hugging Face repo linked in the official LTX-2 README. Missing encoder files usually cause import or load failures inside `ltx-pipelines`.
- Set **`LTX_GEMMA_ROOT`** in `.env` to the directory that contains those files (same path you pass to upstream `--gemma-root`).

## Environment sync

- `LTX_PYTHON_BIN` = Python from `uv sync` inside the cloned LTX-2 repo (has `ltx-core` / `ltx-pipelines` importable).
- `LTX_REPO_PATH` = root of the cloned `LTX-2` repo (optional if packages are installed editable; used by `scripts/ltx_official_try_import.py` to prepend `src` paths).
- `LTX_STUB_MODE=false` and non-empty `LTX_MODEL_PATH` — otherwise the worker uses FFmpeg slideshow.
- **`LTX_USE_OFFICIAL_PIPELINES=true`** — after `LTX_GEMMA_ROOT`, `LTX_UPSCALER_PATH`, and (for two-stage HQ) `LTX_DISTILLED_LORA_PATH` are set, the worker runs **`python -m ltx_pipelines.<module>`** instead of the Diffusers-only path inside `scripts/ltx_i2v_scene.py`. Mapping: `pipeline_mode=two_stage_hq` → `ti2vid_two_stages_hq`, `distilled_fast` → `distilled`. `diffusers_i2v` stays on Diffusers unless you only enable the legacy `LTX_OFFICIAL_I2V_MODULE` flow.

## Smoke order

1. `python scripts/ltx_official_try_import.py` (or `uv run python -c "import ltx_pipelines"`) on the pod.
2. `scripts/ltx_i2v_scene.py` with your checkpoint (Diffusers path).
3. If `LTX_OFFICIAL_I2V_MODULE` is set, run one frame with the same args the worker will use (see `docs/LTX2-INSTALL-RUNPOD.md`).

## Version runbook

Record in deploy notes: **LTX-2 git SHA**, **kadmoo-video-service git SHA**, and **HF file revisions** so upgrades stay aligned.
