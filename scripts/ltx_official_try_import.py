#!/usr/bin/env python3
"""Smoke: verify LTX-2 packages import from LTX_REPO_PATH (RunPod)."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    repo = os.environ.get("LTX_REPO_PATH", "").strip()
    if not repo or not Path(repo).is_dir():
        print("Set LTX_REPO_PATH to cloned Lightricks/LTX-2", file=sys.stderr)
        return 1
    root = Path(repo)
    for sub in ("packages/ltx-pipelines/src", "packages/ltx-core/src"):
        p = root / sub
        if p.is_dir():
            sys.path.insert(0, str(p))
    try:
        import ltx_pipelines  # noqa: F401

        print("OK: ltx_pipelines importable")
        return 0
    except ImportError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
