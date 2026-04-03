"""LTX-2 LoRA training: unzip, optional ltx-trainer, upload weights, webhook to Next.js."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

from worker.celery_app import app

from config import get_settings
from storage.supabase_upload import upload_bytes_to_storage
from webhook.training_notify import send_lora_training_webhook


def _find_safetensors(root: Path) -> list[Path]:
    found = [p for p in root.rglob("*.safetensors") if p.is_file()]
    return sorted(found, key=lambda p: p.stat().st_size, reverse=True)


def _unzip(z: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(z, "r") as zf:
        zf.extractall(dest)


@app.task(bind=True, name="train_ltx_lora", max_retries=0)
def train_ltx_lora(
    self,
    zip_path: str,
    work_id: str,
    site_id: str | None = None,
    callback_url: str | None = None,
    lora_kind: str = "style",
    trigger_word: str | None = None,
) -> dict:
    settings = get_settings()
    z = Path(zip_path)
    if not z.is_file():
        return {"ok": False, "error": "zip missing"}

    out_dir = z.parent / f"lora_out_{work_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_dir = out_dir / "extracted"
    train_out = out_dir / "trainer_output"
    train_out.mkdir(parents=True, exist_ok=True)

    try:
        _unzip(z, extract_dir)
    except zipfile.BadZipFile as e:
        return {"ok": False, "error": f"bad zip: {e}"}

    repo = settings.ltx_repo_path.strip()
    train_py = Path(repo) / "packages" / "ltx-trainer" / "scripts" / "train.py" if repo else None

    def _upload_best(best: Path) -> dict:
        data = best.read_bytes()
        sid = (site_id or "unknown").replace("/", "")[:64]
        kind = "style" if lora_kind != "avatar" else "avatar"
        object_path = f"lora-weights/{sid}/{work_id}_{kind}.safetensors"
        public_url, spath, size = upload_bytes_to_storage(
            data,
            object_path=object_path,
            content_type="application/octet-stream",
        )
        payload = {
            "event": "lora.training.completed",
            "task_id": f"train-lora-{work_id}",
            "site_id": site_id,
            "lora_kind": kind,
            "public_url": public_url,
            "storage_path": spath,
            "file_size_bytes": size,
            "trigger_word": trigger_word,
            "ok": True,
        }
        if callback_url:
            send_lora_training_webhook(callback_url, payload)
        return {
            "ok": True,
            "public_url": public_url,
            "storage_path": spath,
            "weights_file": str(best),
        }

    # 1) Weights already inside the zip
    bundled = _find_safetensors(extract_dir)
    if bundled:
        try:
            return _upload_best(bundled[0])
        except RuntimeError as e:
            return {"ok": False, "error": str(e)}

    # 2) Run ltx-trainer when template + repo exist
    tpl = settings.ltx_trainer_config_template.strip()
    if train_py and train_py.is_file() and tpl and Path(tpl).is_file():
        cfg_path = out_dir / "train_config.yaml"
        text = Path(tpl).read_text(encoding="utf-8")
        cfg_path.write_text(
            text.format(
                data_dir=str(extract_dir.resolve()),
                output_dir=str(train_out.resolve()),
            ),
            encoding="utf-8",
        )
        try:
            subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    str(train_py),
                    "--config",
                    str(cfg_path),
                ],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                timeout=86400,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            err = str(e)
            if isinstance(e, subprocess.CalledProcessError):
                err = (e.stderr or e.stdout or err)[:4000]
            return {"ok": False, "error": f"trainer failed: {err}"}

        produced = _find_safetensors(train_out)
        if not produced:
            produced = _find_safetensors(out_dir)
        if not produced:
            return {"ok": False, "error": "trainer finished but no .safetensors found"}
        try:
            return _upload_best(produced[0])
        except RuntimeError as e:
            return {"ok": False, "error": str(e)}

    # 3) No path to weights
    dest = out_dir / "training_input.zip"
    shutil.copy2(z, dest)
    return {
        "ok": False,
        "error": "Zip had no .safetensors and trainer not configured "
        "(set LTX_REPO_PATH + LTX_TRAINER_CONFIG_TEMPLATE, or ship weights in zip).",
        "saved_zip": str(dest),
    }
