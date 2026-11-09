import re
import unicodedata

import httpx
from bs4 import BeautifulSoup

from app.publication_dates import parse_publication_datetime
from app.scrapers.base import JobData, ScraperError

BASE = "https://co.computrabajo.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BotEmpleosFamiliar/0.1)",
    "Accept-Language": "es-CO,es;q=0.9",
}

# Etiquetas de la página que no son datos de la oferta
BADGES = {
    "postulado",
    "vista",
    "empleo destacado",
    "se precisa urgente",
    "urgente",
    "nuevo",
    "destacado",
}


def slugify(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def build_url(query: str, city: str = "") -> str:
    path = f"/trabajo-de-{slugify(query)}"
    if city:
        path += f"-en-{slugify(city)}"
    return BASE + path


def parse(html: str) -> list[JobData]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[JobData] = []
    for art in soup.select("article"):
        link = art.select_one("h2 a[href]") or art.select_one("a[href]")
        if not link:
            continue
        title = link.get_text(" ", strip=True)
        if not title:
            continue
        href = link["href"]
        url = href if href.startswith("http") else BASE + href
        url = url.split("#")[0]
        lines = [
            s
            for s in art.stripped_strings
            if s != title and s.strip().lower() not in BADGES
        ]
        published_at = next(
            (parsed for line in lines if (parsed := parse_publication_datetime(line))),
            None,
        )
        jobs.append(
            JobData(
                source="computrabajo",
                title=title,
                url=url,
                company=lines[0] if lines else "",
                location=lines[1] if len(lines) > 1 else "",
                text=" ".join(lines),
                published_at=published_at,
            )
        )
    return jobs


def search(query: str, city: str = "") -> list[JobData]:
    url = build_url(query, city)
    try:
        res = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
    except httpx.HTTPError as e:
        raise ScraperError(f"No se pudo conectar con Computrabajo ({e.__class__.__name__})")

    if res.status_code in (403, 429):
        raise ScraperError(f"Computrabajo bloqueó la consulta (código {res.status_code})")
    if res.status_code == 404:
        return []  # no hay página para esa combinación de cargo y ciudad
    if res.status_code != 200:
        raise ScraperError(f"Computrabajo respondió con código {res.status_code}")

    jobs = parse(res.text)
    if not jobs:
        with open("debug_computrabajo.html", "w", encoding="utf-8") as f:
            f.write(res.text)
    return jobs
