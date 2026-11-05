import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """The message could not be delivered. Safe to show the visitor a generic
    'try again' - never the underlying SMTP error, which can leak server details.
    """


def send_contact_email(name: str, email: str, subject: str, message: str) -> None:
    """Forwards a contact-form submission to CONTACT_EMAIL_TO by SMTP.
    There is no database, so this is the only record of the submission -
    if this fails, the message is genuinely gone, not just unsaved.
    """
    msg = EmailMessage()
    msg["Subject"] = f"[Portfolio contact] {subject}"
    msg["From"] = settings.contact_email_from
    msg["To"] = settings.contact_email_to
    # Replying to this message goes straight to the visitor, not CONTACT_EMAIL_FROM.
    msg["Reply-To"] = email
    msg.set_content(f"From: {name} <{email}>\n\n{message}")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError):
        logger.exception("Failed to send contact-form email")
        raise EmailSendError("Could not send your message right now. Please try again later.")
