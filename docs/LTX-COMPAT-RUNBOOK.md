# Version compatibility runbook (LTX-2 + kadmoo-video-service)

Keep these three pins aligned when upgrading:

1. **Lightricks/LTX-2** — git commit SHA on the GPU host (`LTX_REPO_PATH`).
2. **kadmoo-video-service** — git commit deployed on RunPod.
3. **Kadmoo App** — Vercel deploy that matches the JSON job contract (`CreateExternalVideoJobBody` / `VideoJobRequest`).

## Contract fields (video jobs)

| Field | Notes |
|-------|--------|
| `pipeline_mode` | `diffusers_i2v` (default), `distilled_fast`, `two_stage_hq` |
| `enhance_prompt` | Passed into Diffusers path when supported |
| `smooth_scene_transitions` | FFmpeg crossfade between scene segments |
| `render_mode` | `image_to_video` / `audio_to_video` |

## Official CLI

If `LTX_OFFICIAL_I2V_MODULE` is set, `scripts/ltx_i2v_scene.py` tries `uv run python -m <module>` from `LTX_REPO_PATH` before Diffusers. CLI flags differ by upstream version — adjust `scripts/ltx_i2v_scene.py` attempts if your LTX commit changes.

## Training

- Zip may contain ready `.safetensors` → uploaded without running `ltx-trainer`.
- Or set `LTX_TRAINER_CONFIG_TEMPLATE` to a YAML file with `{data_dir}` and `{output_dir}` placeholders plus `LTX_REPO_PATH` with `ltx-trainer`.

## Webhooks

- Video: `WEBHOOK_HMAC_SECRET` (service) = `VIDEO_SERVICE_WEBHOOK_SECRET` (Next.js).
- LoRA training completion: same secret, `POST /api/webhooks/lora-training`.
