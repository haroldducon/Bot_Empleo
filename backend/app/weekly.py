"""Funciones para delimitar semanas laborales iniciadas en lunes, hora de Colombia."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

APP_TIMEZONE_NAME = "America/Bogota"
APP_TIMEZONE = ZoneInfo(APP_TIMEZONE_NAME)


def current_week_start_local(now: datetime | None = None) -> datetime:
    """Devuelve el lunes a las 00:00 en la zona horaria de la aplicación."""
    if now is None:
        local_now = datetime.now(APP_TIMEZONE)
    elif now.tzinfo is None:
        local_now = now.replace(tzinfo=APP_TIMEZONE)
    else:
        local_now = now.astimezone(APP_TIMEZONE)

    return local_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=local_now.weekday()
    )


def current_week_start_utc(now: datetime | None = None) -> datetime:
    """Devuelve el límite semanal equivalente en UTC para consultar PostgreSQL."""
    return current_week_start_local(now).astimezone(timezone.utc)


def current_week_info(now: datetime | None = None) -> dict[str, str]:
    """Información serializable sobre la semana actual y el próximo reinicio."""
    start = current_week_start_local(now)
    return {
        "start_date": start.date().isoformat(),
        "next_reset": (start + timedelta(days=7)).isoformat(),
        "timezone": APP_TIMEZONE_NAME,
    }
