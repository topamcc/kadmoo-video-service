# Version compatibility runbook (LTX-2 + kadmoo-video-service)

Keep these three pins aligned when upgrading:

1. **Lightricks/LTX-2** — git commit SHA on the GPU host (`LTX_REPO_PATH`).
2. **kadmoo-video-service** — git commit deployed on RunPod.
3. **Kadmoo App** — Vercel deploy that matches the JSON job contract (`CreateExternalVideoJobBody` / `VideoJobRequest`).

## Contract fields (video jobs)

| Field | Notes |
|-------|--------|
| `pipeline_mode` | `diffusers_i2v` (default), `distilled_fast`, `two_stage_hq` |
| `enhance_prompt` | Passed to Diffusers and to official `ltx_pipelines` CLIs as `--enhance-prompt` when enabled |
| `smooth_scene_transitions` | FFmpeg crossfade between scene segments |
| `render_mode` | `image_to_video` / `audio_to_video` |

## Official CLI

When **`LTX_USE_OFFICIAL_PIPELINES=true`** and assets in [LTX2-ASSET-CHECKLIST.md](./LTX2-ASSET-CHECKLIST.md) are present, `scripts/ltx_i2v_scene.py` runs **`python -m ltx_pipelines.ti2vid_two_stages_hq`** or **`ltx_pipelines.distilled`** (from `pipeline_mode`) before falling back to Diffusers.

Legacy: if `LTX_OFFICIAL_I2V_MODULE` is set, the same script still tries `uv run python -m <module>` from `LTX_REPO_PATH` after the fixed mapping fails.

Multi-keyframe and A2V options: [LTX-KF-A2V-EVAL.md](./LTX-KF-A2V-EVAL.md).

## Training

- Zip may contain ready `.safetensors` → uploaded without running `ltx-trainer`.
- Or set `LTX_TRAINER_CONFIG_TEMPLATE` to a YAML file with `{data_dir}` and `{output_dir}` placeholders plus `LTX_REPO_PATH` with `ltx-trainer`.

## Webhooks

- Video: `WEBHOOK_HMAC_SECRET` (service) = `VIDEO_SERVICE_WEBHOOK_SECRET` (Next.js).
- LoRA training completion: same secret, `POST /api/webhooks/lora-training`.
