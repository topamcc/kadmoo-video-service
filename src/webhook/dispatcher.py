"""HMAC-signed outbound webhooks to Repo A (same pattern as kadmoo-crawler-service)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import httpx

from config import get_settings
from shared.types import WebhookPayload


def sign_body(secret: str, body: str) -> str:
    return hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()


def send_webhook_sync(callback_url: str, payload: WebhookPayload) -> None:
    settings = get_settings()
    secret = settings.webhook_hmac_secret
    if not secret:
        return
    # WebhookPayload uses jobId camelCase in JSON
    dumped = payload.model_dump(mode="json", by_alias=True)
    body = json.dumps(dumped, default=str)
    signature = sign_body(secret, body)
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": payload.event,
        "X-Webhook-Job-Id": payload.job_id,
        "User-Agent": "KadmooVideo/1.0",
    }
    max_retries = 3
    backoff = 1.0
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.post(callback_url, content=body, headers=headers)
            if r.is_success:
                return
            if r.status_code < 500 and r.status_code != 429:
                return
        except httpx.HTTPError:
            pass
        time.sleep(backoff)
        backoff *= 2
