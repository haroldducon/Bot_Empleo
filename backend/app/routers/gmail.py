from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import gmail_service
from app.config import settings
from app.crypto import decrypt, encrypt
from app.database import get_db
from app.deps import get_current_user
from app.models import GmailConnection, GmailOAuthState, User
from app.scrapers.base import ScraperError

router = APIRouter(prefix="/gmail", tags=["gmail"])
logger = logging.getLogger(__name__)


class GmailLabelIn(BaseModel):
    label_id: str = Field(min_length=1, max_length=255)


def _frontend_redirect(status: str) -> RedirectResponse:
    origin = (settings.allowed_origins or ["http://localhost:5173"])[0].rstrip("/")
    query = urlencode({"gmail": status})
    return RedirectResponse(f"{origin}/?{query}", status_code=303)


def _connection_for_user(db: Session, user_id: int) -> GmailConnection | None:
    return db.scalar(
        select(GmailConnection).where(GmailConnection.user_id == user_id)
    )


@router.get("/status")
def gmail_status(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    connection = _connection_for_user(db, user.id)
    return {
        "configured": gmail_service.oauth_is_configured(),
        "connected": connection is not None,
        "email": connection.google_email if connection else None,
        "label_id": connection.gmail_label_id if connection else None,
        "label_name": connection.gmail_label_name if connection else None,
        "label_configured": bool(connection and connection.gmail_label_id),
    }


@router.post("/connect")
def start_gmail_connection(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not gmail_service.oauth_is_configured():
        raise HTTPException(503, "El administrador debe configurar OAuth de Google en backend/.env")
    now = datetime.now(timezone.utc)
    db.execute(delete(GmailOAuthState).where(GmailOAuthState.expires_at < now))
    state = secrets.token_urlsafe(32)
    db.add(
        GmailOAuthState(
            state_hash=gmail_service.hash_oauth_state(state),
            user_id=user.id,
            expires_at=now + timedelta(minutes=10),
        )
    )
    db.commit()
    return {"authorization_url": gmail_service.build_authorization_url(state)}


@router.get("/oauth/callback")
def gmail_oauth_callback(
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if not state:
        return _frontend_redirect("state_error")
    row = db.get(GmailOAuthState, gmail_service.hash_oauth_state(state))
    if not row:
        return _frontend_redirect("state_error")
    user_id = row.user_id
    expired = row.expires_at <= datetime.now(timezone.utc)
    db.delete(row)
    db.commit()  # consume the state before any external token exchange
    if expired:
        return _frontend_redirect("state_error")
    if error or not code:
        return _frontend_redirect("denied")

    try:
        token_data = gmail_service.exchange_authorization_code(code)
        google_email, email_verified = gmail_service.fetch_google_email(
            token_data["access_token"]
        )
        if not google_email or not email_verified:
            return _frontend_redirect("error")

        connection = _connection_for_user(db, user_id)
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            if connection and connection.google_email.casefold() == google_email.casefold():
                refresh_token = decrypt(connection.encrypted_refresh_token)
            else:
                return _frontend_redirect("error")

        if connection:
            if connection.google_email.casefold() != google_email.casefold():
                connection.gmail_label_id = None
                connection.gmail_label_name = None
            connection.google_email = google_email
            connection.encrypted_refresh_token = encrypt(refresh_token)
        else:
            db.add(
                GmailConnection(
                    user_id=user_id,
                    google_email=google_email,
                    encrypted_refresh_token=encrypt(refresh_token),
                )
            )
        db.commit()
        return _frontend_redirect("connected")
    except Exception as exc:  # Never log OAuth credentials or raw provider responses.
        logger.warning("Gmail OAuth callback failed (%s)", type(exc).__name__)
        db.rollback()
        return _frontend_redirect("error")


@router.get("/labels")
def gmail_labels(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    connection = _connection_for_user(db, user.id)
    if not connection:
        raise HTTPException(409, "Conecta primero una cuenta Gmail")
    try:
        return gmail_service.list_gmail_labels(
            decrypt(connection.encrypted_refresh_token)
        )
    except ScraperError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, "No fue posible cargar las etiquetas de Gmail") from exc


@router.put("/label")
def select_gmail_label(
    data: GmailLabelIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    connection = _connection_for_user(db, user.id)
    if not connection:
        raise HTTPException(409, "Conecta primero una cuenta Gmail")
    try:
        labels = gmail_service.list_gmail_labels(
            decrypt(connection.encrypted_refresh_token)
        )
    except ScraperError as exc:
        raise HTTPException(400, str(exc)) from exc
    selected = next((label for label in labels if label["id"] == data.label_id), None)
    if not selected:
        raise HTTPException(400, "La etiqueta no pertenece a la cuenta Gmail conectada")
    connection.gmail_label_id = selected["id"]
    connection.gmail_label_name = selected["name"]
    db.commit()
    return {
        "connected": True,
        "email": connection.google_email,
        "label_id": connection.gmail_label_id,
        "label_name": connection.gmail_label_name,
        "label_configured": True,
    }


@router.delete("/connection", status_code=204)
def disconnect_gmail(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    connection = _connection_for_user(db, user.id)
    if connection:
        try:
            gmail_service.revoke_google_token(
                decrypt(connection.encrypted_refresh_token)
            )
        except Exception:  # noqa: BLE001
            pass
        db.delete(connection)
        db.commit()
    db.execute(delete(GmailOAuthState).where(GmailOAuthState.user_id == user.id))
    db.commit()
    return None
