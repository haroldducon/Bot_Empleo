"""Fuente beta de ofertas públicas de Magneto Empleo Colombia.

Usa las rutas públicas cargo/ciudad de Magneto en Chromium headless, sin login,
perfil persistente ni cookies guardadas. Cada lote comparte un navegador temporal,
consulta los cargos secuencialmente y no reintenta errores/bloqueos.
"""

from __future__ import annotations

import os
import logging
import re
import threading
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.publication_dates import parse_publication_datetime
from app.scrapers.base import JobData, ScraperError

logger = logging.getLogger(__name__)

BASE = "https://www.magneto365.com"
OFFER_PATH_PREFIX = "/co/empleos/"
SEARCH_PATH_PREFIX = "/co/trabajos/buscar/"
RESULT_LINK_SELECTOR = 'a[href*="/co/empleos/"]'
QUERY_DELAY_SECONDS = 2
NAVIGATION_TIMEOUT_MS = 30000
RESULT_TIMEOUT_MS = 12000
MAX_RESULTS_PER_QUERY = 20
MAX_OFFER_AGE_DAYS = 5
MAX_SUMMARY_LENGTH = 1200
BADGES = {"requerido con urgencia", "urgente", "nuevo", "destacado"}
MAGNETO_HOSTS = {"www.magneto365.com", "magneto365.com"}
PUBLISH_DATE_PATTERN = re.compile(
    r'"id"\s*:\s*(?P<id>\d+)\s*,\s*"title"\s*:\s*"(?:\\.|[^"\\])*".{0,5000}?"publishDate"\s*:\s*"(?P<date>[^"\\]+)"',
    re.S,
)
_SEARCH_LOCK = threading.Lock()


def _fold(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower().strip()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _fold(value)).strip("-")


def city_segment(city: str) -> str:
    """Convierte el texto del perfil al segmento de ciudad usado por Magneto."""
    if not city or not city.strip():
        raise ValueError("Completa la ciudad del perfil para buscar en Magneto.")
    folded = _fold(city)
    if "bogota" in folded:
        # Ruta comprobada en Magneto: loc-bogota-d.c.-co
        return "bogota-d.c.-co"

    # El formulario del perfil suele guardar "Ciudad, Departamento, Colombia".
    # La búsqueda de Magneto necesita el nombre de la ciudad, no el departamento.
    city_name = re.split(r"[,;/]", city, maxsplit=1)[0].strip()
    city_name = re.sub(r"\bcolombia\b", "", city_name, flags=re.IGNORECASE).strip()
    slug = slugify(city_name)
    if not slug:
        raise ValueError("No se pudo convertir la ciudad del perfil a una ruta de búsqueda.")
    return f"{slug}-co"


def build_url(query: str, city: str) -> str:
    title_slug = slugify(query)
    if not title_slug:
        raise ValueError("El cargo de búsqueda no puede estar vacío.")
    return f"{BASE}{SEARCH_PATH_PREFIX}loc-{city_segment(city)}/{title_slug}"


def _clean_title(value: str) -> str:
    title = " ".join(value.split())
    return re.sub(r"\s+\d{7,}(?:-\d+)?$", "", title).strip()


def _clean_job_url(href: str, page_url: str) -> str | None:
    parts = urlsplit(urljoin(page_url, href))
    if parts.hostname not in MAGNETO_HOSTS or not parts.path.startswith(OFFER_PATH_PREFIX):
        return None
    return urlunsplit(("https", "www.magneto365.com", parts.path.rstrip("/"), "", ""))


def _published_dates_by_id(html: str) -> dict[str, str]:
    """Lee publishDate del estado público embebido en el listado Magneto."""
    # Next/RSC serializa comillas escapadas dentro de la respuesta HTML.
    normalized = html.replace(r'\"', '"')
    return {
        match.group("id"): match.group("date")
        for match in PUBLISH_DATE_PATTERN.finditer(normalized)
    }


def _job_id_from_url(url: str) -> str | None:
    match = re.search(r"-(\d+)$", urlsplit(url).path)
    return match.group(1) if match else None


def _is_recent(published_at: str | None, *, now: datetime | None = None) -> bool:
    """Acepta fechas con zona horaria entre ahora y cinco días atrás, inclusive."""
    if not published_at:
        return False
    try:
        value = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if value.tzinfo is None:
            return False
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        age = current.astimezone(timezone.utc) - value.astimezone(timezone.utc)
        return timedelta(0) <= age <= timedelta(days=MAX_OFFER_AGE_DAYS)
    except (TypeError, ValueError, OverflowError):
        return False


def _location_matches(location: str, city: str) -> bool:
    if not city.strip() or not location.strip():
        return True
    location_slug = slugify(location)
    if any(term in location_slug for term in ("remoto", "teletrabajo", "home-office")):
        return True
    city_parts = [slugify(part) for part in re.split(r"[,;/]", city) if slugify(part)]
    if "bogota" in _fold(city):
        city_parts.append("bogota")
    return any(part in location_slug for part in city_parts)


def parse(html: str, page_url: str, city: str = "") -> list[JobData]:
    """Lee únicamente tarjetas visibles del listado; no visita páginas de detalle."""
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[JobData] = []
    seen: set[str] = set()

    for card in soup.select("article"):
        link = card.select_one(RESULT_LINK_SELECTOR)
        if not link:
            continue
        url = _clean_job_url(str(link.get("href", "")), page_url)
        raw_title = " ".join((link.get("title") or link.get_text(" ", strip=True)).split())
        title = _clean_title(raw_title)
        if not url or not title or url in seen:
            continue
        seen.add(url)

        lines = [" ".join(line.split()) for line in card.stripped_strings if line.strip()]
        other_lines = [
            line for line in lines
            if line.casefold() not in {raw_title.casefold(), title.casefold()}
            and line.casefold() not in BADGES
        ]
        company_line = next((line for line in other_lines if "|" in line), "")
        company_parts = [part.strip() for part in company_line.split("|", 1)]
        company = company_parts[0] if company_parts else ""
        contract = company_parts[1] if len(company_parts) > 1 else ""
        salary = next(
            (line for line in other_lines if "$" in line or "salario a convenir" in line.casefold()),
            "",
        )
        location_candidates = [
            line for line in other_lines
            if line != company_line and line != salary and "$" not in line
        ]
        location = location_candidates[-1] if location_candidates else ""
        if not _location_matches(location, city):
            continue

        summary = " | ".join(part for part in (company, contract, salary, location) if part)
        jobs.append(JobData(
            source="magneto",
            title=title[:300],
            url=url,
            company=company[:200],
            location=location[:200],
            text=summary[:MAX_SUMMARY_LENGTH],
        ))
        if len(jobs) >= MAX_RESULTS_PER_QUERY:
            break
    return jobs


def _fallback_parse(page, city: str) -> list[JobData]:
    """Recupera título/enlace si Magneto cambia el contenedor article de sus tarjetas."""
    links = page.locator(RESULT_LINK_SELECTOR)
    jobs: list[JobData] = []
    seen: set[str] = set()
    for index in range(min(links.count(), MAX_RESULTS_PER_QUERY)):
        link = links.nth(index)
        url = _clean_job_url(link.get_attribute("href") or "", page.url)
        title = _clean_title(link.get_attribute("title") or link.inner_text(timeout=2000))
        if not url or not title or url in seen:
            continue
        seen.add(url)
        card = link.locator("xpath=ancestor::article[1]")
        text = ""
        if card.count():
            try:
                text = " ".join(card.inner_text(timeout=1500).split())[:MAX_SUMMARY_LENGTH]
            except Exception:  # noqa: BLE001 - el título/enlace siguen siendo suficientes
                text = ""
        if not _location_matches(text, city):
            continue
        jobs.append(JobData(
            source="magneto", title=title[:300], url=url,
            text=text or title,
        ))
    return jobs


def _block_query_page(route) -> None:
    # The scraper only needs text and offer links; avoid loading heavy visual assets.
    if route.request.resource_type in {"image", "font", "media"}:
        route.abort()
        return
    parts = urlsplit(route.request.url)
    host = (parts.hostname or "").lower()
    if host in MAGNETO_HOSTS and parts.query and route.request.is_navigation_request():
        route.abort()
        return
    route.continue_()


def _batch_search_locked(queries: list[str], city: str) -> list[JobData]:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ScraperError(
            "Playwright no está instalado. Ejecuta pip install -r backend/requirements.txt."
        ) from exc

    found: dict[str, JobData] = {}
    browser = None
    context = None
    try:
        with sync_playwright() as playwright:
            launch_options = {"headless": True}
            chromium_path = os.getenv("MAGNETO_CHROMIUM_EXECUTABLE")
            if chromium_path:
                launch_options["executable_path"] = chromium_path
            browser = playwright.chromium.launch(**launch_options)
            context = browser.new_context(
                locale="es-CO",
                viewport={"width": 1024, "height": 768},
            )
            page = context.new_page()
            page.route("**/*", _block_query_page)
            failed_responses: list[tuple[str, int]] = []

            def record_failure(response) -> None:
                parts = urlsplit(response.url)
                host = (parts.hostname or "").lower()
                if host in MAGNETO_HOSTS and response.status in (403, 429, 500):
                    failed_responses.append((parts.path, response.status))

            page.on("response", record_failure)
            for query_index, query in enumerate(queries):
                if query_index:
                    time.sleep(QUERY_DELAY_SECONDS)
                url = build_url(query, city)
                failures_before = len(failed_responses)
                try:
                    response = page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=NAVIGATION_TIMEOUT_MS,
                    )
                except (PlaywrightTimeoutError, PlaywrightError) as exc:
                    logger.exception("Magneto page navigation failed for %s", urlsplit(url).path)
                    raise ScraperError(
                        f"No se pudo cargar una búsqueda de Magneto ({type(exc).__name__}); se detuvo sin reintentos.",
                        partial_jobs=list(found.values()),
                    ) from exc

                if response is None:
                    raise ScraperError(
                        "Magneto no devolvió una respuesta de página; se detuvo sin reintentos.",
                        partial_jobs=list(found.values()),
                    )
                if response.status == 404:
                    continue
                if response.status in (403, 429, 500):
                    raise ScraperError(
                        f"Magneto respondió HTTP {response.status}; se detuvo sin reintentos.",
                        partial_jobs=list(found.values()),
                    )
                if response.status >= 400:
                    raise ScraperError(
                        f"Magneto respondió HTTP {response.status}; se detuvo sin reintentos.",
                        partial_jobs=list(found.values()),
                    )

                current = urlsplit(page.url)
                if current.query:
                    raise ScraperError(
                        "Magneto redirigió a una página con query string; se detuvo sin leer resultados.",
                        partial_jobs=list(found.values()),
                    )

                result_links = page.locator(RESULT_LINK_SELECTOR)
                try:
                    result_links.first.wait_for(state="visible", timeout=RESULT_TIMEOUT_MS)
                except PlaywrightTimeoutError:
                    new_failures = failed_responses[failures_before:]
                    if new_failures:
                        path, status = new_failures[-1]
                        raise ScraperError(
                            f"Magneto respondió HTTP {status} al cargar resultados ({path}); se detuvo sin reintentos.",
                            partial_jobs=list(found.values()),
                        )
                    # Puede no haber ofertas para este cargo; se continúa con el siguiente.
                    continue

                page_html = page.content()
                publish_dates = _published_dates_by_id(page_html)
                if not publish_dates:
                    raise ScraperError(
                        "Magneto no expuso fechas de publicación verificables; no se importaron ofertas para respetar el límite de 5 días.",
                        partial_jobs=list(found.values()),
                    )

                page_jobs = parse(page_html, page.url, city)
                if not page_jobs:
                    page_jobs = _fallback_parse(page, city)
                for job in page_jobs:
                    job_id = _job_id_from_url(job.url)
                    raw_published_at = publish_dates.get(job_id) if job_id else None
                    if not job_id or not _is_recent(raw_published_at):
                        continue
                    job.published_at = parse_publication_datetime(raw_published_at)
                    found.setdefault(job.url, job)

            return list(found.values())
    except ScraperError:
        raise
    except Exception as exc:  # noqa: BLE001 - incluye errores al arrancar Chromium
        logger.exception("Magneto scraper failed unexpectedly")
        raise ScraperError(
            f"No se pudo ejecutar la búsqueda de Magneto ({type(exc).__name__}); revisa la instalación de Chromium.",
            partial_jobs=list(found.values()),
        ) from exc
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:  # noqa: BLE001
                pass
        if browser is not None:
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass


def batch_search(queries: list[str], city: str) -> list[JobData]:
    """Busca cargos en secuencia con un navegador efímero compartido por el lote."""
    clean_queries = list(dict.fromkeys(query.strip() for query in queries if query and query.strip()))
    if not clean_queries:
        return []
    if not city or not city.strip():
        raise ScraperError("Completa la ciudad del perfil para consultar Magneto.")
    if not _SEARCH_LOCK.acquire(blocking=False):
        raise ScraperError("Magneto ya está procesando otra búsqueda; inténtalo más tarde.")
    try:
        return _batch_search_locked(clean_queries, city)
    finally:
        _SEARCH_LOCK.release()


def search(query: str, city: str = "") -> list[JobData]:
    """Compatibilidad con el contrato de búsqueda individual."""
    return batch_search([query], city)
