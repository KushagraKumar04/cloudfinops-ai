import time

import httpx

from app.config import get_settings
from app.services.notifications.base import SendResult


class WebhookNotifier:
    channel = "webhook"

    def send(self, destination: dict, subject: str, body: str) -> SendResult:
        settings = get_settings()
        url = destination.get("url")
        if not url or not isinstance(url, str):
            return SendResult(ok=False, status="failed", error="Missing destination.url")

        headers = destination.get("headers") or {}
        if not isinstance(headers, dict):
            headers = {}
        headers = {str(k): str(v) for k, v in headers.items()}
        headers.setdefault("Content-Type", "application/json")

        payload = {
            "subject": subject,
            "body": body,
            "source": "cloudfinops-ai",
        }

        attempt = 0
        last_error: str | None = None
        start = time.perf_counter()
        max_attempts = max(1, settings.webhook_max_retries + 1)
        while attempt < max_attempts:
            attempt += 1
            try:
                with httpx.Client(timeout=settings.webhook_timeout_seconds) as client:
                    response = client.post(url, headers=headers, json=payload)
                if 200 <= response.status_code < 300:
                    duration_ms = int((time.perf_counter() - start) * 1000)
                    return SendResult(ok=True, status="delivered", duration_ms=duration_ms)
                last_error = f"HTTP {response.status_code}"
            except httpx.HTTPError as exc:
                last_error = str(exc)[:480]

        duration_ms = int((time.perf_counter() - start) * 1000)
        return SendResult(ok=False, status="failed", error=last_error, duration_ms=duration_ms)