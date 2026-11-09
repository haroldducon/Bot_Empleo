from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto import decrypt, encrypt
from app.database import get_db
from app.deps import get_current_user
from app.models import AICredential, User
from app.schemas import AIKeyIn, AIKeyOut, Provider

router = APIRouter(prefix="/ai-keys", tags=["ai-keys"])


def _out(c: AICredential) -> AIKeyOut:
    key = decrypt(c.encrypted_key)
    return AIKeyOut(provider=c.provider, hint=f"…{key[-4:]}", is_active=c.is_active)


@router.get("", response_model=list[AIKeyOut])
def list_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AICredential).where(AICredential.user_id == user.id))
    return [_out(c) for c in rows]


@router.put("/{provider}", response_model=AIKeyOut)
def save_key(
    provider: Provider,
    data: AIKeyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cred = db.scalar(
        select(AICredential).where(
            AICredential.user_id == user.id, AICredential.provider == provider
        )
    )
    encrypted = encrypt(data.api_key.strip())
    if cred:
        cred.encrypted_key = encrypted
    else:
        cred = AICredential(user_id=user.id, provider=provider, encrypted_key=encrypted)
        db.add(cred)
    db.commit()
    db.refresh(cred)
    return _out(cred)


@router.delete("/{provider}", status_code=204)
def delete_key(
    provider: Provider,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cred = db.scalar(
        select(AICredential).where(
            AICredential.user_id == user.id, AICredential.provider == provider
        )
    )
    if not cred:
        raise HTTPException(404, "No hay clave guardada para ese proveedor")
    db.delete(cred)
    db.commit()