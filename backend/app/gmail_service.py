from __future__ import annotations

import base64
import hashlib
import re
from email.utils import parseaddr
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.publication_dates import parse_publication_datetime
from app.scrapers.base import JobData, ScraperError

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
OPENID_SCOPES = "openid email"
JOB_SUBJECT_TERMS = (
    "job", "jobs", "empleo", "empleos", "oportunidad", "vacante", "trabajo", "trabajos"
)
GENERIC_LINK_TEXT = {
    "apply", "apply now", "view job", "see job", "ver empleo", "ver oferta",
    "solicitar", "postularme", "más información", "mas informacion", "view",
}


def oauth_is_configured() -> bool:
    return bool(
        settings.google_oauth_client_id
        and settings.google_oauth_client_secret
        and settings.google_oauth_redirect_uri
    )


def build_authorization_url(state: str) -> str:
    if not oauth_is_configured():
        raise ValueError("Faltan las credenciales OAuth de Google en backend/.env")
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": f"{OPENID_SCOPES} {GMAIL_READONLY_SCOPE}",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_authorization_code(code: str) -> dict:
    response = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("access_token"):
        raise ValueError("Google no devolvió un token de acceso")
    return data


def refresh_access_token(refresh_token: str) -> str:
    try:
        response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=20,
        )
        response.raise_for_status()
        access_token = response.json().get("access_token")
        if not access_token:
            raise ScraperError("Google no devolvió un token de acceso válido.")
        return access_token
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (400, 401):
            raise ScraperError(
                "La autorización de Gmail venció o fue revocada. Desconecta y vuelve a conectar la cuenta."
            ) from exc
        raise ScraperError("No se pudo renovar el acceso a Gmail.") from exc
    except httpx.HTTPError as exc:
        raise ScraperError("No se pudo contactar a Google para renovar el acceso a Gmail.") from exc


def fetch_google_email(access_token: str) -> tuple[str, bool]:
    response = httpx.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return str(data.get("email", "")), bool(data.get("email_verified"))


def list_gmail_labels(refresh_token: str) -> list[dict[str, str]]:
    access_token = refresh_access_token(refresh_token)
    try:
        response = httpx.get(
            f"{GMAIL_API}/labels",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ScraperError("No se pudieron consultar las etiquetas de Gmail.") from exc
    return [
        {"id": item["id"], "name": item["name"]}
        for item in response.json().get("labels", [])
        if item.get("type") == "user" and item.get("id") and item.get("name")
    ]


def _decode_body(payload: dict) -> tuple[str, str]:
    html_parts: list[str] = []
    text_parts: list[str] = []

    def walk(part: dict) -> None:
        body = part.get("body") or {}
        data = body.get("data")
        if data:
            try:
                decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
                    "utf-8", errors="replace"
                )
            except (ValueError, UnicodeError):
                decoded = ""
            mime = part.get("mimeType", "")
            if mime == "text/html":
                html_parts.append(decoded)
            elif mime == "text/plain":
                text_parts.append(decoded)
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    return "\n".join(html_parts), "\n".join(text_parts)


def _canonical_job_url(raw_url: str) -> str | None:
    url = raw_url.strip().replace("&amp;", "&")
    for _ in range(3):
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host in {"linkedin.com", "www.linkedin.com"} and parsed.path.startswith("/safety/go"):
            nested = parse_qs(parsed.query).get("url", [""])[0]
            if nested:
                url = nested
                continue
        if host not in {"linkedin.com", "www.linkedin.com"}:
            return None
        match = re.search(r"/(?:comm/)?jobs/view/(\d+)", parsed.path)
        if not match:
            return None
        return f"https://www.linkedin.com/jobs/view/{match.group(1)}/"
    return None


def _extract_jobs(html: str, plain: str, subject: str) -> list[JobData]:
    if not html:
        lines = [line.strip() for line in plain.splitlines()]
        jobs: dict[str, JobData] = {}
        for index, line in enumerate(lines):
            for match in re.findall(r"https?://[^\s<>\"']+", line):
                url = _canonical_job_url(match.rstrip(".,);]"))
                if not url or url in jobs:
                    continue
                preceding = [
                    item for item in lines[max(0, index - 3) : index]
                    if item and not item.casefold().startswith(("http://", "https://"))
                    and item.casefold() not in GENERIC_LINK_TEXT
                    and len(item) <= 220
                ]
                title = preceding[-1] if preceding else subject.strip() or "Oferta en LinkedIn"
                published_at = next(
                    (
                        parsed
                        for item in reversed(lines[max(0, index - 4) : index])
                        if (parsed := parse_publication_datetime(item))
                    ),
                    None,
                )
                jobs[url] = JobData(
                    source="alertas",
                    title=title,
                    url=url,
                    text=f"{subject}\n{line}"[:5000],
                    published_at=published_at,
                )
        return list(jobs.values())

    if html:
        soup = BeautifulSoup(html, "html.parser")
    jobs: dict[str, JobData] = {}
    for anchor in soup.select("a[href]"):
        url = _canonical_job_url(anchor.get("href", ""))
        if not url or url in jobs:
            continue
        title = " ".join((anchor.get("aria-label") or anchor.get_text(" ", strip=True)).split())
        if not title or title.casefold() in GENERIC_LINK_TEXT or len(title) > 220:
            continue

        container = anchor
        card_text = ""
        for _ in range(5):
            candidate = container.get_text(" | ", strip=True)
            if 25 <= len(candidate) <= 900:
                card_text = candidate
                break
            if container.parent is None:
                break
            container = container.parent
        if not card_text:
            card_text = title

        segments = [
            re.sub(r"\s+", " ", part).strip(" |\t\r\n")
            for part in re.split(r"\s*[|•·]\s*", card_text)
        ]
        segments = [part for part in segments if part]
        published_at = next(
            (parsed for part in segments if (parsed := parse_publication_datetime(part))),
            None,
        )
        title_index = next((i for i, part in enumerate(segments) if part.casefold() == title.casefold()), -1)
        candidates = segments[title_index + 1 :] if title_index >= 0 else []
        candidates = [
            part for part in candidates
            if part.casefold() not in GENERIC_LINK_TEXT
            and not re.search(r"\b(?:hace|ago|days? ago|días?)\b", part, re.I)
            and len(part) <= 160
        ]
        company = candidates[0] if candidates else ""
        location = candidates[1] if len(candidates) > 1 else ""
        jobs[url] = JobData(
            source="alertas",
            title=title,
            url=url,
            company=company,
            location=location,
            text=f"{subject}\n{card_text}"[:5000],
            published_at=published_at,
        )
    return list(jobs.values())


def fetch_linkedin_alerts(refresh_token: str, label_id: str) -> list[JobData]:
    """Read only recent messages carrying the user's explicitly selected Gmail label."""
    access_token = refresh_access_token(refresh_token)
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = httpx.get(
            f"{GMAIL_API}/messages",
            headers=headers,
            params={
                "labelIds": label_id,
                "q": "from:linkedin.com newer_than:7d",
                "maxResults": 50,
            },
            timeout=20,
        )
        response.raise_for_status()
        message_refs = response.json().get("messages", [])
        found: dict[str, JobData] = {}
        for ref in message_refs:
            message_response = httpx.get(
                f"{GMAIL_API}/messages/{ref['id']}",
                headers=headers,
                params={"format": "full"},
                timeout=20,
            )
            message_response.raise_for_status()
            message = message_response.json()
            payload = message.get("payload", {})
            headers_by_name = {
                item.get("name", "").lower(): item.get("value", "")
                for item in payload.get("headers", [])
            }
            sender = parseaddr(headers_by_name.get("from", ""))[1].lower()
            subject = headers_by_name.get("subject", "")
            if not sender.endswith("@linkedin.com"):
                continue
            if not any(term in subject.casefold() for term in JOB_SUBJECT_TERMS):
                continue
            html, plain = _decode_body(payload)
            for job in _extract_jobs(html, plain, subject):
                found[job.url] = job
        return list(found.values())
    except ScraperError:
        raise
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403):
            raise ScraperError(
                "Google rechazó la lectura de Gmail. Revisa que la etiqueta seleccionada exista y que la cuenta haya autorizado el acceso."
            ) from exc
        raise ScraperError("Google no pudo devolver las alertas de LinkedIn.") from exc
    except httpx.HTTPError as exc:
        raise ScraperError("No se pudo contactar a Gmail para leer las alertas.") from exc


def revoke_google_token(refresh_token: str) -> None:
    try:
        httpx.post(
            GOOGLE_REVOKE_URL,
            data={"token": refresh_token},
            timeout=15,
        )
    except httpx.HTTPError:
        # La desconexión local debe poder completarse aunque el endpoint de revocación no responda.
        pass


def hash_oauth_state(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def search_linkedin_for_user(user_id: int, _desired_titles: list[str], _city: str) -> list[JobData]:
    from sqlalchemy import select

    from app.crypto import decrypt
    from app.database import SessionLocal
    from app.models import GmailConnection

    with SessionLocal() as db:
        connection = db.scalar(
            select(GmailConnection).where(GmailConnection.user_id == user_id)
        )
        if not connection:
            raise ScraperError("Conecta una cuenta Gmail para buscar alertas de LinkedIn.")
        if not connection.gmail_label_id:
            raise ScraperError("Selecciona primero una etiqueta de Gmail para LinkedIn.")
        refresh_token = decrypt(connection.encrypted_refresh_token)
        label_id = connection.gmail_label_id

    labels = list_gmail_labels(refresh_token)
    if not any(label["id"] == label_id for label in labels):
        raise ScraperError(
            "La etiqueta de Gmail seleccionada ya no existe. Elige otra en la configuración de alertas."
        )
    return fetch_linkedin_alerts(refresh_token, label_id)
