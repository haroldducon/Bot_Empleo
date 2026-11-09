from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.avatar_images import MAX_AVATAR_BYTES, normalize_avatar
from app.database import get_db
from app.deps import get_current_user
from app.models import Education, Experience, Profile, User
from app.schemas import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


def _get_or_create(user: User, db: Session) -> Profile:
    if user.profile is None:
        user.profile = Profile(notification_email=user.email)
        db.commit()
        db.refresh(user)
    return user.profile


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_or_create(user, db)


@router.put("", response_model=ProfileOut)
def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_or_create(user, db)
    p.full_name = data.full_name
    p.headline = data.headline
    p.summary = data.summary
    p.city = data.city
    p.modality = data.modality
    p.desired_titles = [t.strip() for t in data.desired_titles if t.strip()]
    p.skills = [s.strip() for s in data.skills if s.strip()]
    p.salary_min = data.salary_min
    p.notification_email = data.notification_email or user.email
    p.notify_enabled = data.notify_enabled
    # Reemplaza las listas completas (el frontend envía el estado final del formulario)
    p.experiences = [Experience(**e.model_dump()) for e in data.experiences]
    p.education = [Education(**e.model_dump()) for e in data.education]
    db.commit()
    db.refresh(p)
    return p


@router.post("/avatar", status_code=204)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        raw = await file.read(MAX_AVATAR_BYTES + 1)
    finally:
        await file.close()
    if len(raw) > MAX_AVATAR_BYTES:
        raise HTTPException(413, "La foto no puede superar 2 MB.")
    try:
        normalized = normalize_avatar(raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    profile = _get_or_create(user, db)
    profile.avatar_data = normalized
    db.commit()
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get("/avatar", response_class=Response)
def get_avatar(user: User = Depends(get_current_user)):
    profile = user.profile
    headers = {
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    }
    if not profile or not profile.avatar_data:
        return Response(status_code=204, headers=headers)
    return Response(content=profile.avatar_data, media_type="image/webp", headers=headers)


@router.delete("/avatar", status_code=204)
def delete_avatar(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.profile and user.profile.avatar_data:
        user.profile.avatar_data = None
        db.commit()
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
