import re
import unicodedata

import httpx
from bs4 import BeautifulSoup

from app.publication_dates import parse_publication_datetime
from app.scrapers.base import JobData, ScraperError

BASE = "https://www.elempleo.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BotEmpleosFamiliar/0.1)",
    "Accept-Language": "es-CO,es;q=0.9",
}

# Enlace de una oferta individual: /co/ofertas-trabajo/<nombre>-<número>
OFFER_RE = re.compile(r"/co/ofertas-trabajo/[^/?#]+-\d{6,}")

# Textos de la página que no son datos de la oferta
BADGES = {
    "urgente",
    "nuevo",
    "destacado",
    "ver oferta",
    "postularme",
    "postular",
    "guardar",
    "registrar hoja de vida",
}

# Botones de compartir: sus enlaces contienen la dirección de la oferta, pero no son ofertas
SHARE_TITLES = {
    "whatsapp",
    "facebook",
    "x",
    "x antes twitter",
    "twitter",
    "linkedin",
    "correo",
    "copiar enlace",
    "enlace copiado",
    "compartir",
}

# Nombres de íconos que aparecen como texto suelto dentro de la tarjeta
ICONS = {"cop", "usd", "industry", "country", "city", "contract", "salary", "experience", "modality"}

MODALITY_WORDS = {"hibrido", "híbrido", "presencial", "remoto", "teletrabajo"}

# Cada dato viene seguido de su etiqueta
LABELS = {
    "salario": "salario",
    "tipo de contrato": "contrato",
    "ubicación": "ubicacion",
    "ubicacion": "ubicacion",
    "modalidad laboral": "modalidad",
    "experiencia mínima": "experiencia",
    "experiencia minima": "experiencia",
}

DATE_RE = re.compile(r"^(hoy|ayer|hace\s+\d+.*)$", re.IGNORECASE)


def slugify(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def candidate_urls(query: str, city: str = "") -> list[str]:
    q, c = slugify(query), slugify(city)
    urls = []
    if c:
        urls.append(f"{BASE}/co/ofertas-empleo/{c}/{q}")
    urls.append(f"{BASE}/co/ofertas-empleo/{q}")
    return urls


def _card_for(link):
    """Sube desde el enlace hasta el contenedor que agrupa solo esa oferta."""
    node = link
    for _ in range(6):
        parent = node.parent
        if parent is None:
            break
        hrefs = {
            a["href"].split("?")[0]
            for a in parent.select("a[href]")
            if OFFER_RE.search(a["href"])
        }
        if len(hrefs) > 1:
            break
        node = parent
    return node


def extract_fields(lines: list[str], title: str) -> tuple[str, dict[str, str]]:
    """Devuelve (empresa, datos) a partir de las líneas de texto de la tarjeta."""
    fields: dict[str, str] = {}
    first_label = len(lines)
    for i, line in enumerate(lines):
        key = LABELS.get(line.lower())
        if not key:
            continue
        first_label = min(first_label, i)
        j = i - 1
        while j >= 0 and lines[j].lower() in ICONS:
            j -= 1
        if j >= 0 and lines[j].lower() not in LABELS:
            fields[key] = lines[j]

    title_slug = slugify(title)
    company = ""
    for line in lines[:first_label]:
        low = line.lower()
        if low in ICONS or low in MODALITY_WORDS:
            continue
        if DATE_RE.match(line) or line.startswith("$") or line.startswith("-"):
            continue
        line_slug = slugify(line)
        if not line_slug or line_slug in title_slug:
            continue  # fragmento del título repetido en la tarjeta
        company = line
        break
    return company, fields


def parse(html: str) -> list[JobData]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: dict[str, JobData] = {}
    for a in soup.select("a[href]"):
        href = a["href"]
        if not OFFER_RE.search(href):
            continue
        url = (href if href.startswith("http") else BASE + href).split("?")[0].split("#")[0]
        if not url.startswith(BASE):
            continue  # enlaces de compartir hacia otros sitios (wa.me, facebook, etc.)
        title = a.get_text(" ", strip=True)
        if not title or len(title) < 4:
            continue  # enlaces de imagen o botones; el enlace con título aparece aparte
        if title.lower() in SHARE_TITLES:
            continue
        if url in jobs:
            continue

        card = _card_for(a)
        lines = [
            s.strip()
            for s in card.stripped_strings
            if s.strip() and s.strip() != title and s.strip().lower() not in BADGES
        ]
        if any(l.lower() in {"copiar enlace", "enlace copiado"} for l in lines):
            continue  # es el cuadro de compartir, no una oferta

        company, fields = extract_fields(lines, title)
        published_at = next(
            (parsed for line in lines if (parsed := parse_publication_datetime(line))),
            None,
        )
        location = ", ".join(
            x for x in (fields.get("ubicacion"), fields.get("modalidad"), fields.get("salario")) if x
        )
        clean = [l for l in lines if l.lower() not in ICONS and l.lower() not in LABELS]

        jobs[url] = JobData(
            source="elempleo",
            title=title,
            url=url,
            company=company,
            location=location,
            text=" ".join(clean),
            published_at=published_at,
        )
    return list(jobs.values())


def search(query: str, city: str = "") -> list[JobData]:
    for url in candidate_urls(query, city):
        try:
            res = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        except httpx.HTTPError as e:
            raise ScraperError(f"No se pudo conectar con El Empleo ({e.__class__.__name__})")

        if res.status_code in (403, 429):
            raise ScraperError(f"El Empleo bloqueó la consulta (código {res.status_code})")
        if res.status_code == 404:
            continue  # prueba la siguiente dirección
        if res.status_code != 200:
            raise ScraperError(f"El Empleo respondió con código {res.status_code}")

        jobs = parse(res.text)
        if jobs:
            return jobs
        with open("debug_elempleo.html", "w", encoding="utf-8") as f:
            f.write(res.text)
    return []
