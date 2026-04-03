"""Identity lock hooks for LTX-2 / LoRA (placeholder for production LTX integration)."""

from __future__ import annotations

# When LTX-2 supports face-conditioned LoRA, wire photo_url + training artifacts here.


def describe_identity_prompt(photo_url: str, enabled: bool) -> str:
    if not enabled:
        return ""
    return (
        "Preserve the identity of the person from the reference portrait; "
        "photorealistic, consistent facial features across shots."
    )
