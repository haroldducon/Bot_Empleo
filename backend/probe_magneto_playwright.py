#!/usr/bin/env python3
"""Prueba puntual de búsqueda en la interfaz pública de Magneto.

Instalación:
    pip install playwright
    playwright install chromium

Búsqueda por URL cargo/ubicación:
    python backend/probe_magneto_playwright.py --search-url "https://www.magneto365.com/co/trabajos/buscar/loc-bogota-d.c.-co/analista"

Búsqueda desde el formulario:
    python backend/probe_magneto_playwright.py --keyword "Analista" --city "Bogota"

Usa un contexto temporal, sin login ni perfil persistente. No acepta todas las
cookies ni reintenta errores. Espera enlaces de vacantes, no networkidle.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

HOME_URL = "https://www.magneto365.com/co"
INPUTS = 'input[class*="magneto-ui-input--container_input"]'
CITY_OPTIONS = 'p[class*="searchBar_mega-menu-search-bar__input-option__title"]'
SEARCH_BUTTON = 'span:has-text("Buscar en")'
RESULT_LINKS = 'a[href*="/co/empleos/"]'
MAGNETO_HOST_SUFFIX = "magneto365.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prueba una búsqueda pública en Magneto Empleo.")
    parser.add_argument("--keyword", default=os.getenv("MAGNETO_KEYWORD", "Analista"))
    parser.add_argument("--city", default=os.getenv("MAGNETO_CITY", "Bogota"))
    parser.add_argument("--city-match", default=os.getenv("MAGNETO_CITY_MATCH", "Bogotá"))
    parser.add_argument("--search-url", default=os.getenv("MAGNETO_SEARCH_URL"),
                        help="Ruta pública directa cargo/ubicación, sin parámetros ?.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=15000, help="Espera de elementos, en ms.")
    parser.add_argument("--headed", action="store_true", help="Mostrar Chromium; por defecto es headless.")
    parser.add_argument("--chromium-path", default=os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE"))
    return parser.parse_args()


def clean_title(value: str) -> str:
    return re.sub(r"\s+\d{7,}(?:-\d+)?$", "", " ".join(value.split())).strip()


def clean_offer_url(href: str, base_url: str) -> str | None:
    parts = urlsplit(urljoin(base_url, href))
    host = (parts.hostname or "").lower()
    if not (host == MAGNETO_HOST_SUFFIX or host.endswith("." + MAGNETO_HOST_SUFFIX)):
        return None
    if not parts.path.startswith("/co/empleos/"):
        return None
    return urlunsplit(("https", "www.magneto365.com", parts.path.rstrip("/"), "", ""))


def validate_search_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme != "https" or parts.hostname != "www.magneto365.com":
        raise ValueError("La URL debe pertenecer a https://www.magneto365.com.")
    if not parts.path.startswith("/co/trabajos/buscar/"):
        raise ValueError("La URL debe ser una ruta pública de búsqueda /co/trabajos/buscar/.")
    if parts.query or parts.fragment:
        raise ValueError("La ruta de búsqueda debe venir sin query string ni fragmento.")
    return value


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        print("El límite debe ser mayor que cero.", file=sys.stderr)
        return 2
    try:
        direct_url = validate_search_url(args.search_url) if args.search_url else None
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    blocked_page_queries: list[str] = []
    document_statuses: list[tuple[str, int, bool]] = []

    def guard_page_query(route) -> None:
        parts = urlsplit(route.request.url)
        host = (parts.hostname or "").lower()
        is_magneto = host == MAGNETO_HOST_SUFFIX or host.endswith("." + MAGNETO_HOST_SUFFIX)
        if is_magneto and parts.query and route.request.is_navigation_request():
            blocked_page_queries.append(parts.path)
            route.abort()
            return
        route.continue_()

    def record_document_response(response) -> None:
        parts = urlsplit(response.url)
        host = (parts.hostname or "").lower()
        if (host == MAGNETO_HOST_SUFFIX or host.endswith("." + MAGNETO_HOST_SUFFIX)):
            if response.request.resource_type == "document":
                document_statuses.append((parts.path, response.status, bool(parts.query)))

    with sync_playwright() as playwright:
        launch = {"headless": not args.headed}
        if args.chromium_path:
            launch["executable_path"] = args.chromium_path
        browser = playwright.chromium.launch(**launch)
        context = browser.new_context(viewport={"width": 1366, "height": 800}, locale="es-CO")
        page = context.new_page()
        page.route("**/*", guard_page_query)
        page.on("response", record_document_response)

        try:
            if direct_url:
                start_response = page.goto(direct_url, wait_until="domcontentloaded", timeout=30000)
            else:
                start_response = page.goto(HOME_URL, wait_until="domcontentloaded", timeout=30000)
            if start_response and start_response.status >= 400:
                print(f"Magneto respondió HTTP {start_response.status} al abrir la página.")
                return 1

            if not direct_url:
                # Rechaza cookies opcionales si está disponible; nunca acepta todas automáticamente.
                for label in ("Rechazar opcionales", "Rechazar todas", "Solo necesarias"):
                    try:
                        page.get_by_role("button", name=label, exact=False).first.click(timeout=700)
                        break
                    except PlaywrightTimeoutError:
                        pass

                inputs = page.locator(INPUTS)
                if inputs.count() < 2:
                    print("No se encontraron los campos de cargo y ciudad; el formulario pudo cambiar.")
                    return 1
                inputs.nth(1).wait_for(state="visible", timeout=args.timeout)
                inputs.nth(0).fill(args.keyword.strip())
                city_input = inputs.nth(1)
                city_input.click()
                city_input.fill("")
                city_input.press_sequentially(args.city.strip(), delay=100)
                option = page.locator(CITY_OPTIONS).filter(has_text=args.city_match).first
                try:
                    option.wait_for(state="visible", timeout=args.timeout)
                except PlaywrightTimeoutError:
                    if blocked_page_queries:
                        print("Magneto intentó navegar a una URL con query; se bloqueó sin leer resultados.")
                        return 3
                    print("No apareció la opción de ciudad; no se continuó con una búsqueda incompleta.")
                    return 1
                option.click()
                button = page.locator(SEARCH_BUTTON).first
                button.wait_for(state="visible", timeout=args.timeout)
                button.click()

            results = page.locator(RESULT_LINKS)
            try:
                results.first.wait_for(state="visible", timeout=args.timeout)
            except PlaywrightTimeoutError:
                current = urlsplit(page.url)
                if current.query or blocked_page_queries:
                    print("La página de resultados usa query string; se detuvo antes de extraer ofertas.")
                    return 3
                if document_statuses and document_statuses[-1][1] >= 400:
                    print(f"Magneto respondió HTTP {document_statuses[-1][1]} al cargar resultados; no se reintentó.")
                else:
                    print("No aparecieron enlaces de ofertas dentro del tiempo de espera.")
                print(f"URL final: {current.scheme}://{current.netloc}{current.path}")
                return 1

            current = urlsplit(page.url)
            if current.query:
                print("La URL final contiene parámetros; no se leerán las ofertas.")
                return 3
            if document_statuses and document_statuses[-1][1] >= 400:
                print(f"Magneto respondió HTTP {document_statuses[-1][1]} en resultados; no se reintentó.")
                return 1

            print(f"URL de resultados: {current.scheme}://{current.netloc}{current.path}")
            print(f"Ofertas encontradas: {results.count()}")
            seen: set[str] = set()
            shown = 0
            for index in range(results.count()):
                link = results.nth(index)
                offer_url = clean_offer_url(link.get_attribute("href") or "", page.url)
                if not offer_url or offer_url in seen:
                    continue
                seen.add(offer_url)
                title = clean_title(link.get_attribute("title") or link.inner_text(timeout=2000))
                if title:
                    print(f"- {title}\n  {offer_url}")
                    shown += 1
                if shown >= args.limit:
                    break
            return 0
        except PlaywrightTimeoutError as exc:
            print(f"Tiempo de espera agotado: {exc}", file=sys.stderr)
            print("No se intentó iniciar sesión ni sortear bloqueos.", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"No se pudo completar la prueba: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
