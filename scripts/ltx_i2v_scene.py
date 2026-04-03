#!/usr/bin/env python3
"""
One-scene image-to-video helper for kadmoo-video-service (subprocess from worker).

1) Optional: try `uv run python -m <LTX_OFFICIAL_I2V_MODULE>` from LTX_REPO_PATH (upstream CLI varies by version).
2) Else: Hugging Face Diffusers LTX pipeline when available; otherwise exits with code 2.

Usage:
  python scripts/ltx_i2v_scene.py --image in.jpg --prompt "..." --output out.mp4 \\
    --checkpoint /path/to/model.safetensors --width 512 --height 704 --num-frames 25 --fps 24
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _try_official_uv_module(repo: str, module: str, args: argparse.Namespace) -> int:
    """
    Attempt upstream ltx_pipelines CLI. Return 0 on success, 3 if skipped/failed so caller may fall back.
    """
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base = [
        "uv",
        "run",
        "python",
        "-m",
        module,
    ]
    ck = str(Path(args.checkpoint)) if args.checkpoint and Path(args.checkpoint).is_file() else ""
    # Several upstream CLIs use these names; try a small set (first success wins).
    templates: list[list[str]] = [
        [
            "--prompt",
            args.prompt,
            "--output-path",
            str(out_path),
            "--image-path",
            str(Path(args.image)),
        ],
        [
            "--prompt",
            args.prompt,
            "--output-path",
            str(out_path),
            "--image",
            str(Path(args.image)),
        ],
        [
            "--prompt",
            args.prompt,
            "--output_path",
            str(out_path),
            "--image_path",
            str(Path(args.image)),
        ],
    ]
    attempts: list[list[str]] = []
    for tail in templates:
        cmd = list(base)
        cmd.extend(tail)
        if ck:
            cmd.extend(["--checkpoint-path", ck, "--checkpoint", ck])
        attempts.append(cmd)
    cwd = Path(repo)
    if not cwd.is_dir():
        return 3
    for cmd in attempts:
        try:
            r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=7200)
        except FileNotFoundError:
            return 3
        except subprocess.TimeoutExpired:
            return 3
        if r.returncode == 0 and out_path.is_file() and out_path.stat().st_size > 1000:
            return 0
    return 3


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--image", required=True, help="Keyframe image path")
    p.add_argument("--prompt", required=True)
    p.add_argument("--output", required=True, help="Output mp4 path")
    p.add_argument("--checkpoint", default="", help="Local .safetensors checkpoint (optional if --model-id)")
    p.add_argument(
        "--model-id",
        default="Lightricks/LTX-2.3",
        help="HF model id when not using local checkpoint only",
    )
    p.add_argument("--width", type=int, default=512)
    p.add_argument("--height", type=int, default=704)
    p.add_argument("--num-frames", type=int, default=25)
    p.add_argument("--fps", type=float, default=24.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--lora-path", default="", help="Optional local LoRA .safetensors")
    p.add_argument("--lora-scale", type=float, default=1.0)
    p.add_argument(
        "--pipeline-mode",
        default="diffusers_i2v",
        choices=("diffusers_i2v", "distilled_fast", "two_stage_hq"),
        help="distilled_fast/two_stage_hq may trigger official module when env is set",
    )
    p.add_argument("--enhance-prompt", action="store_true", help="Pass through to pipeline if supported")
    args = p.parse_args()

    repo = os.environ.get("LTX_REPO_PATH", "").strip()
    official_mod = os.environ.get("LTX_OFFICIAL_I2V_MODULE", "").strip()
    if (
        official_mod
        and repo
        and args.pipeline_mode in ("distilled_fast", "two_stage_hq")
    ):
        rc = _try_official_uv_module(repo, official_mod, args)
        if rc == 0:
            return 0

    img_path = Path(args.image)
    if not img_path.is_file():
        print(f"Image not found: {img_path}", file=sys.stderr)
        return 1

    try:
        import torch
    except ImportError:
        print("torch not installed", file=sys.stderr)
        return 2

    try:
        from diffusers import DiffusionPipeline
    except ImportError:
        print("diffusers not installed", file=sys.stderr)
        return 2

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32

    # Try common LTX class names across diffusers versions
    pipe = None
    for cls_name in ("LTX2Pipeline", "LTXPipeline", "LtxPipeline"):
        cls = getattr(__import__("diffusers", fromlist=[cls_name]), cls_name, None)
        if cls is None:
            continue
        try:
            if args.checkpoint and Path(args.checkpoint).is_file():
                pipe = cls.from_single_file(
                    args.checkpoint,
                    torch_dtype=dtype,
                )
            else:
                pipe = cls.from_pretrained(
                    args.model_id,
                    torch_dtype=dtype,
                    trust_remote_code=True,
                )
            break
        except Exception as e:  # noqa: BLE001
            print(f"{cls_name} load failed: {e}", file=sys.stderr)
            pipe = None

    if pipe is None:
        try:
            pipe = DiffusionPipeline.from_pretrained(
                args.model_id,
                torch_dtype=dtype,
                trust_remote_code=True,
            )
        except Exception as e:  # noqa: BLE001
            print(f"DiffusionPipeline.from_pretrained failed: {e}", file=sys.stderr)
            return 2

    if args.lora_path and Path(args.lora_path).is_file():
        try:
            pipe.load_lora_weights(args.lora_path, adapter_name="kadmoo")
            if hasattr(pipe, "set_adapters"):
                pipe.set_adapters(["kadmoo"], adapter_weights=[args.lora_scale])
        except Exception as e:  # noqa: BLE001
            print(f"LoRA load failed (continuing without): {e}", file=sys.stderr)

    pipe = pipe.to(device)

    from PIL import Image

    image = Image.open(img_path).convert("RGB")
    image = image.resize((args.width, args.height), Image.Resampling.LANCZOS)

    gen_kwargs = {
        "prompt": args.prompt,
        "image": image,
        "num_frames": args.num_frames,
        "generator": torch.Generator(device=device).manual_seed(args.seed),
    }
    if args.enhance_prompt:
        gen_kwargs["enhance_prompt"] = True

    try:
        result = pipe(**gen_kwargs)
    except TypeError:
        # Older signatures: drop fps / enhance_prompt
        gen_kwargs.pop("fps", None)
        gen_kwargs.pop("enhance_prompt", None)
        result = pipe(**gen_kwargs)

    frames = getattr(result, "frames", None) or result[0]
    if not frames:
        print("No frames in pipeline output", file=sys.stderr)
        return 2

    # result.frames may be list of PIL or list of tensors
    first = frames[0] if isinstance(frames, list) else frames
    if hasattr(first, "save"):
        pil_list = list(frames) if isinstance(frames, list) else [frames]
    else:
        print("Unexpected frame format; export not implemented", file=sys.stderr)
        return 2

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = out_path.parent / f"_ltx_frames_{out_path.stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for i, im in enumerate(pil_list):
        im.save(tmp_dir / f"f{i:05d}.png")

    import subprocess

    pattern = str(tmp_dir / "f%05d.png")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(args.fps),
            "-i",
            pattern,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out_path),
        ],
        check=True,
    )
    for f in sorted(tmp_dir.glob("*.png")):
        f.unlink(missing_ok=True)
    tmp_dir.rmdir()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
