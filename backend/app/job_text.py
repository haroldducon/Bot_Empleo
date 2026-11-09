import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.scrapers.base import ScraperError

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BotEmpleosFamiliar/0.1)",
    "Accept-Language": "es-CO,es;q=0.9",
}
ALLOWED_HOSTS = {"www.elempleo.com", "co.computrabajo.com"}


def fetch_offer_text(url: str, limit: int = 7000) -> str:
    host = urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        raise ScraperError("Esa oferta no se puede abrir desde la plataforma.")
    try:
        res = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
    except httpx.HTTPError:
        raise ScraperError("No se pudo abrir la oferta completa.")
    if res.status_code != 200:
        raise ScraperError(f"La oferta respondió con código {res.status_code}.")

    soup = BeautifulSoup(res.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "svg", "form"]):
        tag.decompose()
    root = soup.select_one("main") or soup.body or soup
    text = re.sub(r"\s+", " ", root.get_text(" ", strip=True))
    if len(text) < 80:
        raise ScraperError("No se pudo leer el contenido de la oferta.")
    return text[:limit]