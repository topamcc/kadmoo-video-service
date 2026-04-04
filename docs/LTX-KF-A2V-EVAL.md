# Keyframe interpolation vs concat; A2Vid vs I2V + mux

This note captures how **kadmoo-video-service** wires optional Lightricks [LTX-2 `ltx_pipelines`](https://github.com/Lightricks/LTX-2/tree/main/packages/ltx-pipelines) paths and what to evaluate on your GPU host.

## Multi-keyframe (`image_to_video`)

| Strategy | Env | Behavior |
| -------- | --- | -------- |
| **concat** (default) | `LTX_MULTI_KEYFRAME_STRATEGY=concat` | One I2V clip per keyframe/scene, then `ffmpeg` concat (+ optional crossfade). Same prompts per scene as today. |
| **keyframe_interpolation** | `LTX_MULTI_KEYFRAME_STRATEGY=keyframe_interpolation` | Single run of `python -m ltx_pipelines.keyframe_interpolation` with all keyframes as `--image PATH FRAME_IDX STRENGTH`. Prompts are joined with `"; "`. Requires **`LTX_USE_OFFICIAL_PIPELINES=true`** and the same asset set as two-stage HQ (checkpoint, distilled LoRA, spatial upsampler, Gemma). Only used when **two or more** keyframes are present. |

**Evaluation ideas:** temporal continuity between scenes, identity drift, VRAM peak, wall time vs concat. KIP uses **guiding latents** (smoother motion) vs per-shot **replacing latents** in `TI2VidTwoStagesPipeline` (see upstream README conditioning section).

## Audio-to-video (`render_mode=audio_to_video`)

| Pipeline | Env | Behavior |
| -------- | --- | -------- |
| **i2v_mux** (default) | `LTX_AUDIO_TO_VIDEO_PIPELINE=i2v_mux` | One I2V segment from the first keyframe for narration duration, silent MP4, then mux ElevenLabs MP3. |
| **a2vid_two_stage** | `LTX_AUDIO_TO_VIDEO_PIPELINE=a2vid_two_stage` | `python -m ltx_pipelines.a2vid_two_stage` with `--audio-path` set to the generated narration MP3. Output MP4 includes conditioned audio from the pipeline (upstream returns input waveform for fidelity). Requires official assets + **`LTX_USE_OFFICIAL_PIPELINES=true`**. |

**Evaluation ideas:** lip-sync / reactive motion vs mux-only; length alignment with `num_frames` vs audio duration; failure modes when MP3 codec/path differs from upstream expectations.

## Operational checklist

1. Confirm `GET /health` shows `ltx_use_official_pipelines` and related flags after deploy.
2. Run `scripts/ltx_official_try_import.py` on the pod.
3. A/B one SMB job with concat vs KIP and compare motion continuity.

Record **LTX-2 git SHA** and **HF file revisions** next to results so upgrades stay comparable.
