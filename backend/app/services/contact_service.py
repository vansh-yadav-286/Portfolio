from app.core.config import settings
from app.schemas.contact import ContactMessageCreate
from app.services.email_service import EmailSendError, send_contact_email
from app.utils.helpers import api_error


def send_message(payload: ContactMessageCreate) -> None:
    if not settings.smtp_configured:
        raise api_error("The contact form is not configured on this server", status_code=503)
    try:
        send_contact_email(payload.name, payload.email, payload.subject, payload.message)
    except EmailSendError as exc:
        raise api_error(str(exc), status_code=502)
