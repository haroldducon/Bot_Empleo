import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import PasswordResetToken, Profile, User
from app.password_reset_mail import send_password_reset_email
from app.schemas import (
    PasswordResetComplete,
    PasswordResetRequest,
    Token,
    UserCreate,
    UserOut,
)
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
GENERIC_RESET_MESSAGE = (
    "Si existe una cuenta con ese correo, recibirás instrucciones para cambiar la contraseña."
)


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado")
    user = User(email=email, password_hash=hash_password(data.password))
    user.profile = Profile(notification_email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos")
    return Token(access_token=create_access_token(user.id))


@router.post("/forgot-password")
def forgot_password(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if user and settings.reset_email_enabled:
        now = datetime.now(timezone.utc)
        latest = db.scalar(
            select(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id)
            .order_by(PasswordResetToken.created_at.desc())
            .limit(1)
        )
        # Per-account cooldown limits mail abuse. The response remains identical either way.
        if not latest or (now - latest.created_at).total_seconds() >= 60:
            db.execute(
                delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
            )
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            reset_token = PasswordResetToken(
                token_hash=token_hash,
                user_id=user.id,
                expires_at=now + timedelta(minutes=settings.password_reset_minutes),
            )
            db.add(reset_token)
            db.commit()
            reset_url = (
                f"{settings.frontend_url.rstrip('/')}/#reset-password?token="
                f"{quote(raw_token, safe='')}"
            )
            background_tasks.add_task(send_password_reset_email, user.email, reset_url)

    return {"message": GENERIC_RESET_MESSAGE}


@router.post("/reset-password")
def reset_password(data: PasswordResetComplete, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(data.token.encode("utf-8")).hexdigest()
    reset_token = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if not reset_token or reset_token.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace no es válido o ya venció. Solicita uno nuevo.",
        )
    user = db.get(User, reset_token.user_id)
    if not user:
        db.delete(reset_token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace no es válido o ya venció. Solicita uno nuevo.",
        )

    user.password_hash = hash_password(data.new_password)
    db.execute(
        delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    db.commit()
    return {"message": "Contraseña actualizada. Ya puedes iniciar sesión."}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
