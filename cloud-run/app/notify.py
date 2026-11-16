"""Link-only email to the admin after a call (ADR-10, A6).

The email holds a link and nothing else: no invite label, contact details or conversation
content, because email isn't behind the admin sign-in. Sent over SMTP with STARTTLS, so any
provider works. Skipped when SMTP_HOST is unset, as it is in local development and tests.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config import Settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10


def message(settings: Settings) -> EmailMessage:
    email = EmailMessage()
    email["Subject"] = "A new conversation is ready to review"
    email["From"] = settings.notify_from or settings.smtp_username
    email["To"] = settings.admin_email
    email.set_content(f"A conversation has ended. Review it here:\n\n{settings.admin_url}\n")
    return email


def notify_admin(settings: Settings) -> None:
    """Never raises: a failed email mustn't fail the call's save. Logs the error type only."""
    if not settings.smtp_host:
        return
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=TIMEOUT_SECONDS) as smtp:
            smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            smtp.send_message(message(settings))
    except (OSError, smtplib.SMTPException) as error:
        logger.warning("Notification email failed: %s", type(error).__name__)
