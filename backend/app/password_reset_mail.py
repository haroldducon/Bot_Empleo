import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(recipient: str, reset_url: str) -> None:
    if not settings.reset_email_enabled:
        logger.error("Recuperación de contraseña no enviada: faltan variables SMTP/FRONTEND_URL")
        return

    message = EmailMessage()
    message["Subject"] = "Restablece tu contraseña de Nexo Laboral"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "Recibimos una solicitud para cambiar la contraseña de tu cuenta de Nexo Laboral.\n\n"
        f"Abre este enlace para elegir una nueva contraseña (válido por {settings.password_reset_minutes} minutos):\n"
        f"{reset_url}\n\n"
        "Si no solicitaste este cambio, ignora este mensaje. Tu contraseña seguirá igual.\n"
    )
    message.add_alternative(
        "<p>Recibimos una solicitud para cambiar la contraseña de tu cuenta de Nexo Laboral.</p>"
        f"<p><a href=\"{reset_url}\">Crear una nueva contraseña</a></p>"
        f"<p>Este enlace vence en {settings.password_reset_minutes} minutos y solo puede usarse una vez.</p>"
        "<p>Si no solicitaste este cambio, ignora este mensaje. Tu contraseña seguirá igual.</p>",
        subtype="html",
    )

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
        logger.exception("No se pudo enviar el correo de recuperación")
