"""Identity / LoRA prompt helpers for LTX-2."""

from __future__ import annotations


def describe_identity_prompt(photo_url: str, enabled: bool) -> str:
    if not enabled:
        return ""
    return (
        "Preserve the identity of the person from the reference portrait; "
        "photorealistic, consistent facial features across shots."
    )


def build_visual_prompt(
    *,
    base: str,
    sound_hint: str = "",
    style_trigger: str = "",
    avatar_trigger: str = "",
    identity_lock: bool = True,
    photo_url: str = "",
) -> str:
    """Combine scene prompt with optional trigger words and identity hint."""
    parts: list[str] = []
    if style_trigger.strip():
        parts.append(style_trigger.strip())
    if avatar_trigger.strip():
        parts.append(avatar_trigger.strip())
    parts.append(base.strip() or "cinematic motion, professional lighting")
    if sound_hint.strip():
        parts.append(f"Audio mood: {sound_hint.strip()}")
    if identity_lock and photo_url.strip():
        parts.append(describe_identity_prompt(photo_url, True))
    return ". ".join(p for p in parts if p)
