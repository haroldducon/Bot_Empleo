import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _content(reset_url: str) -> tuple[str, str]:
    text = (
        "Recibimos una solicitud para cambiar la contraseña de tu cuenta de Nexo Laboral.\n\n"
        f"Abre este enlace para elegir una nueva contraseña (válido por {settings.password_reset_minutes} minutos):\n"
        f"{reset_url}\n\n"
        "Si no solicitaste este cambio, ignora este mensaje. Tu contraseña seguirá igual.\n"
    )
    html = (
        "<p>Recibimos una solicitud para cambiar la contraseña de tu cuenta de Nexo Laboral.</p>"
        f"<p><a href=\"{reset_url}\">Crear una nueva contraseña</a></p>"
        f"<p>Este enlace vence en {settings.password_reset_minutes} minutos y solo puede usarse una vez.</p>"
        "<p>Si no solicitaste este cambio, ignora este mensaje. Tu contraseña seguirá igual.</p>"
    )
    return text, html


def send_password_reset_email(recipient: str, reset_url: str) -> None:
    if not settings.reset_email_enabled:
        logger.error("Recuperación de contraseña no enviada: faltan variables de email/FRONTEND_URL")
        return

    sender = settings.resend_from_email or settings.smtp_from_email
    text, html = _content(reset_url)
    subject = "Restablece tu contraseña de Nexo Laboral"

    # Resend's HTTPS API works on port 443, including on Render Free instances.
    if settings.resend_api_key:
        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": sender,
                    "to": [recipient],
                    "subject": subject,
                    "text": text,
                    "html": html,
                },
                timeout=20,
            )
            if not response.is_success:
                # Do not log the response body: provider payloads can contain recipient data.
                logger.error("Resend rechazó el correo de recuperación (HTTP %s)", response.status_code)
        except httpx.HTTPError:
            logger.exception("No se pudo contactar la API HTTPS de Resend")
        return

    # SMTP fallback for hosting providers that allow outbound SMTP.
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
    except Exception:
        logger.exception("No se pudo enviar el correo de recuperación por SMTP")
