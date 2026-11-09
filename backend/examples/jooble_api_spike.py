"""Prueba aislada de la API de Jooble Colombia; no está registrada como fuente activa.

Requiere JOOBLE_API_KEY en el entorno. Hace una sola solicitud por llamada y
no automatiza ni consulta LinkedIn directamente.
"""

from __future__ import annotations

import argparse
import os
from typing import Any

import httpx

from app.scrapers.base import JobData, ScraperError

API_ROOT = "https://co.jooble.org/api"
REQUEST_TIMEOUT_SECONDS = 20
RESULTS_PER_PAGE = 10


def normalize(payload: dict[str, Any]) -> list[JobData]:
    """Convierte la respuesta del API en el contrato común del proyecto."""
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
                title=title,
                url=url,
                company=str(row.get("company") or "").strip(),
                location=str(row.get("location") or "").strip(),
                text=str(row.get("snippet") or "").strip(),
            )
        )
    return normalized


def search_jooble(
    query: str,
    city: str,
    api_key: str | None = None,
) -> list[JobData]:
    """Hace una consulta a la API REST oficial de Jooble en Colombia."""
    key = (api_key or os.getenv("JOOBLE_API_KEY", "")).strip()
    if not key:
        raise ScraperError("Configura JOOBLE_API_KEY en el entorno antes de probar la fuente.")
    if not query.strip():
        raise ValueError("El cargo o palabra clave de búsqueda no puede estar vacío.")
    if not city.strip():
        raise ValueError("Indica una ciudad o ubicación para la búsqueda.")

    # Jooble documenta la clave en la ruta; no imprimir ni registrar esta URL.
    endpoint = f"{API_ROOT}/{key}"
    body = {
        "keywords": query.strip(),
        "location": city.strip(),
        "page": "1",
        "ResultOnPage": RESULTS_PER_PAGE,
        "companysearch": False,
    }
    try:
        response = httpx.post(
            endpoint,
            json=body,
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise ScraperError(
            f"No se pudo conectar con Jooble ({type(exc).__name__})."
        ) from exc

    if response.status_code == 403:
        raise ScraperError("Jooble rechazó la clave de API o el acceso para este país.")
    if response.status_code == 429:
        raise ScraperError("Jooble informó que se alcanzó un límite de solicitudes.")
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prueba una búsqueda de ofertas en la API oficial de Jooble Colombia."
    )
    parser.add_argument("cargo", help="Cargo o palabra clave, por ejemplo: analista de datos")
    parser.add_argument("ciudad", help="Ciudad o ubicación, por ejemplo: Bogotá")
    args = parser.parse_args()

    try:
        jobs = search_jooble(args.cargo, args.ciudad)
    except (ScraperError, ValueError) as exc:
        parser.error(str(exc))

    print(f"Jooble devolvió {len(jobs)} ofertas para la búsqueda.")
    for job in jobs:
        print(f"- {job.title} | {job.company or 'Empresa no indicada'} | {job.location}")
        print(f"  {job.url}")


if __name__ == "__main__":
    main()
