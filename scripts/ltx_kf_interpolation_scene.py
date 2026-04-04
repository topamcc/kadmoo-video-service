#!/usr/bin/env python3
"""
Run Lightricks KeyframeInterpolationPipeline once for multiple keyframes (worker subprocess).

Requires LTX-2 venv (ltx_pipelines on PYTHONPATH), same assets as two-stage HQ.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _frame_indices(n_keyframes: int, num_frames: int) -> list[int]:
    if n_keyframes <= 0:
        return []
    if n_keyframes == 1:
        return [0]
    last = max(0, num_frames - 1)
    return [round(i * last / (n_keyframes - 1)) for i in range(n_keyframes)]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--width", type=int, required=True)
    p.add_argument("--height", type=int, required=True)
    p.add_argument("--num-frames", type=int, required=True)
    p.add_argument("--fps", type=float, required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--enhance-prompt", action="store_true")
    p.add_argument("--keyframe", action="append", required=True, help="Repeat: path to keyframe image")
    args = p.parse_args()

    gemma = os.environ.get("LTX_GEMMA_ROOT", "").strip()
    ups = os.environ.get("LTX_UPSCALER_PATH", "").strip()
    dl = os.environ.get("LTX_DISTILLED_LORA_PATH", "").strip()
    d_strength = os.environ.get("LTX_DISTILLED_LORA_STRENGTH", "0.8").strip() or "0.8"
    img_strength = os.environ.get("LTX_IMAGE_CONDITIONING_STRENGTH", "0.85").strip() or "0.85"

    paths = [Path(x) for x in args.keyframe]
    for x in paths:
        if not x.is_file():
            print(f"Keyframe not found: {x}", file=sys.stderr)
            return 1
    if not gemma or not Path(gemma).is_dir():
        print("LTX_GEMMA_ROOT must be set to a directory", file=sys.stderr)
        return 1
    if not ups or not Path(ups).is_file():
        print("LTX_UPSCALER_PATH must point to spatial upscaler .safetensors", file=sys.stderr)
        return 1
    if not dl or not Path(dl).is_file():
        print("LTX_DISTILLED_LORA_PATH required for keyframe_interpolation", file=sys.stderr)
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
        "ltx_pipelines.keyframe_interpolation",
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
    ]
    if args.enhance_prompt:
        cmd.append("--enhance-prompt")
    if _truthy("FP8_QUANTIZATION"):
        cmd.extend(["--quantization", "fp8-cast"])

    lora_path = os.environ.get("LTX_EXTRA_LORA_PATH", "").strip()
    lora_scale = os.environ.get("LTX_EXTRA_LORA_SCALE", "").strip()
    if lora_path and Path(lora_path).is_file() and lora_scale:
        cmd.extend(["--lora", str(Path(lora_path).resolve()), lora_scale])

    frames = args.num_frames
    for path, fi in zip(paths, _frame_indices(len(paths), frames)):
        cmd.extend(["--image", str(path.resolve()), str(fi), img_strength])

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
