"""HMAC-signed callback after LoRA training (optional)."""

from __future__ import annotations

import json

import httpx

from config import get_settings
from webhook.dispatcher import sign_body


def send_lora_training_webhook(callback_url: str, payload: dict) -> None:
    settings = get_settings()
    secret = settings.webhook_hmac_secret.strip()
    if not secret or not callback_url.strip():
        return
    body = json.dumps(payload, default=str)
    signature = sign_body(secret, body)
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": "lora.training.completed",
        "User-Agent": "KadmooVideo/1.0",
    }
    with httpx.Client(timeout=30.0) as client:
        client.post(callback_url.strip(), content=body, headers=headers)
