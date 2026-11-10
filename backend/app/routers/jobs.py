from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Literal
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.ai_providers import AIError, analyze_with_compatible_provider, analyze_with_gemini
from app.config import settings
from app.crypto import decrypt
from app.database import get_db
from app.deps import get_current_user
from app import gmail_service
from app.job_text import fetch_offer_text
from app.matching import explain_job
from app.models import AICredential, GmailConnection, Job, User, UserJob
from app.scrapers import SOURCES
from app.scrapers.base import ScraperError
from app.search_service import RUNS, new_state, run_search
from app.weekly import (
    APP_TIMEZONE_NAME,
    current_week_info,
    current_week_start_local,
    current_week_start_utc,
)

router = APIRouter(tags=["jobs"])


class SourceOut(BaseModel):
    key: str
    label: str
    available: bool
    setup_hint: str | None = None
    notice: str | None = None


class RunIn(BaseModel):
    sources: list[str]


class AnalyzeIn(BaseModel):
    provider: Literal["gemini", "groq", "openrouter"] = "gemini"


class WeekInfo(BaseModel):
    start_date: str
    next_reset: str
    timezone: str


class AnalyticsDay(BaseModel):
    date: str
    label: str
    full_label: str
    count: int


class WeeklyAnalytics(BaseModel):
    start_date: str
    next_reset: str
    timezone: str
    total: int
    peak_day: str | None
    peak_count: int
    days: list[AnalyticsDay]


class CriterionOut(BaseModel):
    key: str
    label: str
    points: int
    max_points: int
    status: str
    detail: str
    fix: str | None = None
    where: str | None = None


class JobOut(BaseModel):
    id: int
    title: str
    company: str
    location: str
    url: str
    source: str
    source_label: str
    score: int
    matched_terms: list[str]
    criteria: list[CriterionOut]
    classification: str
    review_reasons: list[str]
    evidence_coverage: int
    salary_status: str
    created_at: datetime
    published_at: datetime | None
    ai: dict | None = None


@router.get("/search/sources", response_model=list[SourceOut])
def list_sources(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    connection = db.scalar(
        select(GmailConnection).where(GmailConnection.user_id == user.id)
    )
    sources = []
    for source in SOURCES.values():
        available = source.available
        setup_hint = source.setup_hint
        if source.key == "alertas":
            if not gmail_service.oauth_is_configured():
                available = False
                setup_hint = "Faltan GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET y GOOGLE_OAUTH_REDIRECT_URI en backend/.env."
            elif not connection:
                available = False
                setup_hint = "Conecta un buzón Gmail dedicado y selecciona la etiqueta que contiene las alertas de empleo de LinkedIn."
            elif not connection.gmail_label_id:
                available = False
                setup_hint = "Crea una etiqueta Gmail para las alertas de LinkedIn y selecciónala aquí."
            else:
                available = True
                setup_hint = None
        sources.append(
            SourceOut(
                key=source.key,
                label=source.label,
                available=available,
                setup_hint=setup_hint if not available else None,
                notice=source.notice,
            )
        )
    return sources


@router.post("/search/run", status_code=202)
def start_search(
    data: RunIn,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = user.profile
    if not p or not p.desired_titles:
        raise HTTPException(400, "Agrega al menos un cargo que te interese en tu perfil")
    connection = db.scalar(
        select(GmailConnection).where(GmailConnection.user_id == user.id)
    )
    keys = []
    for key in data.sources:
        if key not in SOURCES or not SOURCES[key].available:
            continue
        if key == "alertas" and not (
            gmail_service.oauth_is_configured()
            and connection
            and connection.gmail_label_id
        ):
            continue
        keys.append(key)
    if not keys:
        raise HTTPException(400, "Elige al menos una fuente disponible")
    current = RUNS.get(user.id)
    if current and current["state"] == "running":
        raise HTTPException(409, "Ya hay una búsqueda en curso")
    RUNS[user.id] = new_state(keys)
    background.add_task(run_search, user.id, keys)
    return RUNS[user.id]


@router.get("/search/status")
def search_status(user: User = Depends(get_current_user)):
    return RUNS.get(user.id, {"state": "idle"})


@router.get("/search/week", response_model=WeekInfo)
def search_week(user: User = Depends(get_current_user)):
    """Indica el período visible; el cambio ocurre automáticamente al llegar el lunes."""
    return current_week_info()


@router.get("/analytics/weekly", response_model=WeeklyAnalytics)
def weekly_analytics(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Cuenta ofertas únicas asociadas al usuario en cada día de la semana actual."""
    week_start = current_week_start_local()
    next_reset = week_start + timedelta(days=7)
    day_bucket = cast(func.timezone(APP_TIMEZONE_NAME, UserJob.created_at), Date)
    rows = db.execute(
        select(day_bucket, func.count(UserJob.id))
        .where(
            UserJob.user_id == user.id,
            UserJob.created_at >= week_start.astimezone(timezone.utc),
            UserJob.created_at < next_reset.astimezone(timezone.utc),
        )
        .group_by(day_bucket)
    ).all()
    count_by_date = {day.isoformat(): int(count) for day, count in rows}

    weekday_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    short_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    days = []
    for offset, (full_label, label) in enumerate(zip(weekday_names, short_names)):
        day_date = (week_start + timedelta(days=offset)).date()
        date_key = day_date.isoformat()
        days.append(
            AnalyticsDay(
                date=date_key,
                label=label,
                full_label=full_label,
                count=count_by_date.get(date_key, 0),
            )
        )

    total = sum(day.count for day in days)
    peak = max(days, key=lambda day: day.count) if total else None
    return WeeklyAnalytics(
        start_date=week_start.date().isoformat(),
        next_reset=next_reset.isoformat(),
        timezone=APP_TIMEZONE_NAME,
        total=total,
        peak_day=peak.full_label if peak else None,
        peak_count=peak.count if peak else 0,
        days=days,
    )


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
    min_score: int = Query(30, ge=0, le=100),
    limit: int = Query(100, ge=1, le=300),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = user.profile
    if not profile:
        return []

    query = (
        select(UserJob, Job)
        .join(Job, UserJob.job_id == Job.id)
        .where(
            UserJob.user_id == user.id,
            UserJob.dismissed.is_(False),
            UserJob.created_at >= current_week_start_utc(),
        )
    )
    rows = db.execute(query.order_by(UserJob.created_at.desc())).all()

    # El puntaje se recalcula con el perfil actual, así siempre está al día
    items = []
    for uj, j in rows:
        r = explain_job(profile, j.title, j.text, j.location)
        if r["classification"] == "excluded":
            continue
        if r["classification"] == "match" and r["score"] < min_score:
            continue
        if r["classification"] in {"match", "review"}:
            items.append((r["score"], uj.created_at, uj, j, r))
    items.sort(key=lambda item: (item[0], item[1]), reverse=True)

    return [
        JobOut(
            id=uj.id,
            title=j.title,
            company=j.company,
            location=j.location,
            url=j.url,
            source=j.source,
            source_label=SOURCES[j.source].label if j.source in SOURCES else j.source,
            score=score,
            matched_terms=r["matched"],
            criteria=r["criteria"],
            classification=r["classification"],
            review_reasons=r["review_reasons"],
            evidence_coverage=r["evidence_coverage"],
            salary_status=r["salary_status"],
            created_at=uj.created_at,
            published_at=j.published_at,
            ai=uj.ai_analysis,
        )
        for score, _, uj, j, r in items[:limit]
    ]


@router.post("/jobs/{user_job_id}/dismiss", status_code=204)
def dismiss_job(
    user_job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uj = db.get(UserJob, user_job_id)
    if not uj or uj.user_id != user.id:
        raise HTTPException(404, "Oferta no encontrada")
    uj.dismissed = True
    db.commit()


@router.post("/jobs/{user_job_id}/analyze")
def analyze_job(
    user_job_id: int,
    data: AnalyzeIn = Body(default=AnalyzeIn()),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uj = db.get(UserJob, user_job_id)
    if not uj or uj.user_id != user.id:
        raise HTTPException(404, "Oferta no encontrada")
    if not user.profile:
        raise HTTPException(400, "Completa tu perfil antes de analizar ofertas")

    cred = db.scalar(
        select(AICredential).where(
            AICredential.user_id == user.id,
            AICredential.provider == data.provider,
            AICredential.is_active.is_(True),
        )
    )
    if not cred:
        provider_name = {"gemini": "Gemini", "groq": "Groq", "openrouter": "OpenRouter"}[data.provider]
        raise HTTPException(400, f"Guarda tu clave de {provider_name} en la pestaña Claves de IA")

    job = db.get(Job, uj.job_id)
    try:
        offer_text = fetch_offer_text(job.url)
    except ScraperError as e:
        raise HTTPException(502, str(e))

    try:
        api_key = decrypt(cred.encrypted_key)
        if data.provider == "gemini":
            result = analyze_with_gemini(api_key, settings.gemini_model, user.profile, job, offer_text)
            result.update(provider="gemini", model=settings.gemini_model)
        else:
            result = analyze_with_compatible_provider(data.provider, api_key, user.profile, job, offer_text)
    except AIError as e:
        raise HTTPException(e.status, str(e))

    result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    uj.ai_analysis = result
    db.commit()
    return result
