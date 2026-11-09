"""Proveedor de empleos mediante la API REST oficial de Jooble Colombia.

La fuente se mantiene deshabilitada hasta configurar JOOBLE_API_KEY en el backend.
Cada búsqueda agrupada realiza una sola solicitud HTTP.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.publication_dates import parse_publication_datetime
from app.scrapers.base import JobData, ScraperError

API_ROOT = "https://co.jooble.org/api"
REQUEST_TIMEOUT_SECONDS = 20
RESULTS_PER_PAGE = 10


def is_configured() -> bool:
    return bool(settings.jooble_api_key.strip())


def normalize(payload: dict[str, Any]) -> list[JobData]:
    rows = payload.get("jobs", [])
    if not isinstance(rows, list):
        raise ScraperError("Jooble devolvió una respuesta de ofertas inválida.")

    normalized: list[JobData] = []
    seen_urls: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue

        title = str(row.get("title") or "").strip()
        url = str(row.get("link") or "").strip()
        if not title or not url.startswith(("https://", "http://")) or url in seen_urls:
            continue
        seen_urls.add(url)
        normalized.append(
            JobData(
                source="jooble",
                title=title[:300],
                url=url,
                company=str(row.get("company") or "").strip()[:200],
                location=str(row.get("location") or "").strip()[:200],
                text=str(row.get("snippet") or "").strip(),
                published_at=parse_publication_datetime(
                    row.get("updated") or row.get("published") or row.get("date")
                ),
            )
        )
    return normalized


def search(query: str, city: str = "") -> list[JobData]:
    """Consulta un cargo/consulta. La clave nunca se devuelve ni se registra."""
    api_key = settings.jooble_api_key.strip()
    if not api_key:
        raise ScraperError("Jooble no está configurado. Agrega JOOBLE_API_KEY al .env del backend.")
    if not query.strip():
        return []
    if not city.strip():
        raise ScraperError("Completa una ciudad en tu perfil para buscar en Jooble.")

    # Jooble documenta la clave en la ruta del endpoint; no registrar esta URL.
    endpoint = f"{API_ROOT}/{api_key}"
    request_body = {
        "keywords": query.strip(),
        "location": city.strip(),
        "page": "1",
        "ResultOnPage": RESULTS_PER_PAGE,
        "companysearch": False,
    }
    try:
        response = httpx.post(
            endpoint,
            json=request_body,
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise ScraperError(
            f"No se pudo conectar con Jooble ({type(exc).__name__})."
        ) from exc

    if response.status_code == 403:
        raise ScraperError(
            "Jooble respondió 403 (clave ausente o inválida). Verifica que la clave "
            "corresponda al dominio de Colombia (co.jooble.org) y, si persiste, "
            "confirma la habilitación con soporte de Jooble."
        )
    if response.status_code == 429:
        raise ScraperError("Jooble informó que se alcanzó el límite de solicitudes.")
    if response.status_code != 200:
        raise ScraperError(f"Jooble respondió con código HTTP {response.status_code}.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise ScraperError("Jooble devolvió una respuesta que no es JSON válido.") from exc
    if not isinstance(payload, dict):
        raise ScraperError("Jooble devolvió una respuesta con formato inesperado.")
    if payload.get("error"):
        raise ScraperError("Jooble devolvió un error en la consulta.")
    return normalize(payload)


def search_many(queries: list[str], city: str = "") -> list[JobData]:
    """Agrupa cargos en una consulta; evita una llamada API por cada etiqueta."""
    unique: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized = " ".join(query.split())
        key = normalized.casefold()
        if normalized and key not in seen:
            unique.append(normalized)
            seen.add(key)
    if not unique:
        return []
    # Jooble documenta keywords con términos separados por coma.
    return search(", ".join(unique), city)
