"""Parsing and local-calendar filtering for job publication dates."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import re
import unicodedata

from app.weekly import APP_TIMEZONE

_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}
_NUMBERS = {"un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5}
_RELATIVE = re.compile(
    r"\b(?:hace\s+)?(?P<count>\d+|un|uno|una|dos|tres|cuatro|cinco)\s*"
    r"(?P<unit>min(?:uto)?s?|h(?:ora)?s?|d(?:ia)?s?|semanas?|mes(?:es)?|weeks?|days?|hours?|minutes?)\b"
    r"(?:\s+ago)?",
    re.IGNORECASE,
)
_SPANISH_DATE = re.compile(
    r"\b(?P<day>\d{1,2})\s+(?:de\s+)?(?P<month>enero|febrero|marzo|abril|mayo|junio|"
    r"julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"
    r"(?:\s+de\s+(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)


def _local_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(APP_TIMEZONE)
    if now.tzinfo is None:
        return now.replace(tzinfo=APP_TIMEZONE)
    return now.astimezone(APP_TIMEZONE)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=APP_TIMEZONE)
    return value.astimezone(timezone.utc)


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def parse_publication_datetime(value: object, *, now: datetime | None = None) -> datetime | None:
    """Parse common API dates and Spanish relative labels to an aware UTC datetime.

    Date-only or relative labels without a clock are anchored to midnight in
    America/Bogota. Unknown/ambiguous text remains None instead of using scrape time.
    """
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, date):
        return _as_utc(datetime.combine(value, time.min))
    if value is None:
        return None

    text = " ".join(str(value).strip().split())
    if not text:
        return None

    # ISO timestamps, including date-only values, are common in APIs and embedded data.
    candidates = [text]
    embedded_iso = re.search(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?", text)
    if embedded_iso and embedded_iso.group(0) != text:
        candidates.append(embedded_iso.group(0))
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            return _as_utc(parsed)
        except ValueError:
            pass

    folded = _fold(text)
    local_now = _local_now(now)
    if re.search(r"\b(hoy|today)\b", folded):
        return _as_utc(datetime.combine(local_now.date(), time.min, APP_TIMEZONE))
    if re.search(r"\b(ayer|yesterday)\b", folded):
        yesterday = local_now.date() - timedelta(days=1)
        return _as_utc(datetime.combine(yesterday, time.min, APP_TIMEZONE))

    relative = _RELATIVE.search(folded)
    if relative:
        raw_count = relative.group("count")
        count = int(raw_count) if raw_count.isdigit() else _NUMBERS[raw_count]
        unit = relative.group("unit")
        if unit.startswith(("min",)):
            delta = timedelta(minutes=count)
        elif unit.startswith(("h", "hour")):
            delta = timedelta(hours=count)
        elif unit.startswith(("d", "day")):
            delta = timedelta(days=count)
        elif unit.startswith(("semana", "week")):
            delta = timedelta(weeks=count)
        else:
            delta = timedelta(days=30 * count)
        return _as_utc(local_now - delta)

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            parsed_date = datetime.strptime(text, fmt).date()
            return _as_utc(datetime.combine(parsed_date, time.min, APP_TIMEZONE))
        except ValueError:
            continue

    month_match = _SPANISH_DATE.search(folded)
    if month_match:
        year = int(month_match.group("year") or local_now.year)
        try:
            parsed_date = date(year, int(month_match.group("day")), _MONTHS[month_match.group("month")])
            return _as_utc(datetime.combine(parsed_date, time.min, APP_TIMEZONE))
        except ValueError:
            return None
    return None


def publication_window(date_range: str, *, now: datetime | None = None) -> tuple[datetime, datetime] | None:
    """Return an inclusive local-calendar date window as UTC half-open bounds."""
    if date_range == "all":
        return None
    if date_range not in {"today", "yesterday", "7d", "30d"}:
        raise ValueError("Filtro de fecha no válido")

    local_today = _local_now(now).date()
    if date_range == "today":
        start_date, end_date = local_today, local_today + timedelta(days=1)
    elif date_range == "yesterday":
        start_date, end_date = local_today - timedelta(days=1), local_today
    else:
        count = 7 if date_range == "7d" else 30
        start_date, end_date = local_today - timedelta(days=count - 1), local_today + timedelta(days=1)

    start = datetime.combine(start_date, time.min, APP_TIMEZONE)
    end = datetime.combine(end_date, time.min, APP_TIMEZONE)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)
