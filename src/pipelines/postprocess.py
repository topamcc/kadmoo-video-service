"""Final mux / optional BGM (placeholder — copy when generate_bgm is False)."""

from __future__ import annotations

import shutil
from pathlib import Path

from shared.types import VideoJobRequest


def postprocess(src: Path, dest: Path, req: VideoJobRequest) -> None:
    """
    When generate_bgm is True, future: mix stock bed under narration.
    Stub: copy stream to dest.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if req.generate_bgm:
        # Reserved: FFmpeg sidechain duck or stock asset path from env
        shutil.copy2(src, dest)
        return
    shutil.copy2(src, dest)
