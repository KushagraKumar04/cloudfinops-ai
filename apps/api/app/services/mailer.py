import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger("app.mailer")


def send_email(to: list[str], subject: str, body: str) -> tuple[bool, str | None]:
    settings = get_settings()
    if not to:
        return False, "No recipients"
    if not settings.smtp_enabled:
        logger.info(
            "SMTP disabled. Would send to=%s subject=%s\n%s",
            to,
            subject,
            body,
        )
        return True, None

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(to)
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_starttls:
                client.starttls()
            if settings.smtp_user and settings.smtp_password:
                client.login(settings.smtp_user, settings.smtp_password)
            client.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("Email delivery failed: %s", exc)
        return False, str(exc)[:480]

    return True, None