from dataclasses import dataclass
from typing import Callable

from app.scrapers import jooble
from app.scrapers import base  # noqa: F401
from app.scrapers import computrabajo, elempleo, magneto
from app.scrapers.base import JobData


def _gmail_oauth_is_configured() -> bool:
    from app.gmail_service import oauth_is_configured

    return oauth_is_configured()


def _gmail_search_for_user(user_id: int, titles: list[str], city: str) -> list[JobData]:
    from app.gmail_service import search_linkedin_for_user

    return search_linkedin_for_user(user_id, titles, city)


@dataclass
class Source:
    key: str
    label: str
    search: Callable[[str, str], list[JobData]] | None = None
    batch_search: Callable[[list[str], str], list[JobData]] | None = None
    user_batch_search: Callable[[int, list[str], str], list[JobData]] | None = None
    configured: Callable[[], bool] | None = None
    setup_hint: str | None = None
    notice: str | None = None

    @property
    def available(self) -> bool:
        has_search = (
            self.search is not None
            or self.batch_search is not None
            or self.user_batch_search is not None
        )
        return has_search and (self.configured is None or self.configured())


# Para agregar una fuente nueva: crear su archivo en app/scrapers y sumar una línea aquí.
SOURCES: dict[str, Source] = {
    s.key: s
    for s in [
        Source("computrabajo", "Computrabajo", computrabajo.search),
        Source("elempleo", "El Empleo", elempleo.search),
        Source(
            key="jooble",
            label="Jooble Colombia",
            search=jooble.search,
            batch_search=jooble.search_many,
            configured=jooble.is_configured,
            setup_hint="Agrega JOOBLE_API_KEY al archivo backend/.env y reinicia el backend.",
        ),
        Source(
            key="magneto",
            label="Magneto Empleo (beta personal)",
            search=magneto.search,
            batch_search=magneto.batch_search,
            notice=(
                "Busca rutas públicas por cargo y ciudad con Chromium temporal, sin iniciar sesión. "
                "Solo incluye ofertas con fecha verificable de máximo 5 días; "
                "el puntaje usa título/ubicación. "
                "Verifica requisitos y postúlate en el anuncio original."
            ),
        ),
        Source(
            key="alertas",
            label="LinkedIn (alertas de Gmail)",
            user_batch_search=_gmail_search_for_user,
            configured=_gmail_oauth_is_configured,
            setup_hint="Configura las credenciales OAuth de Google en backend/.env.",
            notice=(
                "Solo consulta la etiqueta de Gmail que selecciones y descarta mensajes "
                "que no vengan de linkedin.com o no incluyan enlaces de empleos."
            ),
        ),
    ]
}
