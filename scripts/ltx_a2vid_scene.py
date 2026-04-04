#!/usr/bin/env python3
"""
Run Lightricks A2VidPipelineTwoStage (audio + image conditioning) as a worker subprocess.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--image", required=True)
    p.add_argument("--audio", required=True, help="Path to narration audio (e.g. MP3 from ElevenLabs)")
    p.add_argument("--prompt", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--width", type=int, required=True)
    p.add_argument("--height", type=int, required=True)
    p.add_argument("--num-frames", type=int, required=True)
    p.add_argument("--fps", type=float, required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--enhance-prompt", action="store_true")
    args = p.parse_args()

    img = Path(args.image)
    aud = Path(args.audio)
    if not img.is_file():
        print(f"Image not found: {img}", file=sys.stderr)
        return 1
    if not aud.is_file():
        print(f"Audio not found: {aud}", file=sys.stderr)
        return 1

    gemma = os.environ.get("LTX_GEMMA_ROOT", "").strip()
    ups = os.environ.get("LTX_UPSCALER_PATH", "").strip()
    dl = os.environ.get("LTX_DISTILLED_LORA_PATH", "").strip()
    d_strength = os.environ.get("LTX_DISTILLED_LORA_STRENGTH", "0.8").strip() or "0.8"
    img_strength = os.environ.get("LTX_IMAGE_CONDITIONING_STRENGTH", "0.85").strip() or "0.85"

    if not gemma or not Path(gemma).is_dir():
        print("LTX_GEMMA_ROOT must be set to a directory", file=sys.stderr)
        return 1
    if not ups or not Path(ups).is_file():
        print("LTX_UPSCALER_PATH must point to spatial upscaler .safetensors", file=sys.stderr)
        return 1
    if not dl or not Path(dl).is_file():
        print("LTX_DISTILLED_LORA_PATH required for a2vid_two_stage", file=sys.stderr)
        return 1
    ck = Path(args.checkpoint)
    if not ck.is_file():
        print(f"Checkpoint not found: {ck}", file=sys.stderr)
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd: list[str] = [
        sys.executable,
        "-m",
        "ltx_pipelines.a2vid_two_stage",
        "--checkpoint-path",
        str(ck.resolve()),
        "--distilled-lora",
        str(Path(dl).resolve()),
        d_strength,
        "--spatial-upsampler-path",
        str(Path(ups).resolve()),
        "--gemma-root",
        str(Path(gemma).resolve()),
        "--prompt",
        args.prompt,
        "--output-path",
        str(out_path.resolve()),
        "--width",
        str(args.width),
        "--height",
        str(args.height),
        "--num-frames",
        str(args.num_frames),
        "--frame-rate",
        str(args.fps),
        "--seed",
        str(args.seed),
        "--audio-path",
        str(aud.resolve()),
        "--image",
        str(img.resolve()),
        "0",
        img_strength,
    ]
    if args.enhance_prompt:
        cmd.append("--enhance-prompt")
    if _truthy("FP8_QUANTIZATION"):
        cmd.extend(["--quantization", "fp8-cast"])

    lora_path = os.environ.get("LTX_EXTRA_LORA_PATH", "").strip()
    lora_scale = os.environ.get("LTX_EXTRA_LORA_SCALE", "").strip()
    if lora_path and Path(lora_path).is_file() and lora_scale:
        cmd.extend(["--lora", str(Path(lora_path).resolve()), lora_scale])

    repo = os.environ.get("LTX_REPO_PATH", "").strip()
    cwd = Path(repo) if repo and Path(repo).is_dir() else None
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=7200)
    except FileNotFoundError:
        print("python executable missing", file=sys.stderr)
        return 2
    if r.returncode != 0:
        print((r.stderr or r.stdout or "unknown error")[:8000], file=sys.stderr)
        return r.returncode
    if not out_path.is_file() or out_path.stat().st_size < 1000:
        print("Output missing or too small", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
