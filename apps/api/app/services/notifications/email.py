import smtplib
import time
from email.message import EmailMessage

from app.config import get_settings
from app.services.notifications.base import SendResult


class EmailNotifier:
    channel = "email"

    def send(self, destination: dict, subject: str, body: str) -> SendResult:
        settings = get_settings()
        to = destination.get("to") or []
        cc = destination.get("cc") or []
        if not isinstance(to, list) or not to:
            return SendResult(ok=False, status="failed", error="No recipients in destination.to")
        if not isinstance(cc, list):
            cc = []

        if not settings.smtp_enabled:
            return SendResult(
                ok=True,
                status="suppressed",
                error="SMTP disabled; delivery logged but not sent",
                duration_ms=0,
            )

        message = EmailMessage()
        message["From"] = settings.smtp_from
        message["To"] = ", ".join(to)
        if cc:
            message["Cc"] = ", ".join(cc)
        message["Subject"] = subject
        message.set_content(body)

        recipients = list(to) + list(cc)
        start = time.perf_counter()
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
                if settings.smtp_starttls:
                    client.starttls()
                if settings.smtp_user and settings.smtp_password:
                    client.login(settings.smtp_user, settings.smtp_password)
                client.send_message(message, to_addrs=recipients)
        except (smtplib.SMTPException, OSError) as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return SendResult(ok=False, status="failed", error=str(exc)[:480], duration_ms=duration_ms)

        duration_ms = int((time.perf_counter() - start) * 1000)
        return SendResult(ok=True, status="delivered", duration_ms=duration_ms)