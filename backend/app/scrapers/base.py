from dataclasses import dataclass
from datetime import datetime


class ScraperError(Exception):
    """Error al consultar una fuente, con ofertas parciales opcionales."""

    def __init__(self, message: str, partial_jobs=None):
        super().__init__(message)
        self.partial_jobs = list(partial_jobs or [])


@dataclass
class JobData:
    source: str
    title: str
    url: str
    company: str = ""
    location: str = ""
    text: str = ""
    published_at: datetime | None = None
