import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.dedupe import fingerprint
from app.matching import score_job
from app.models import Job, User, UserJob
from app.scrapers import SOURCES
from app.scrapers.base import ScraperError
from app.weekly import current_week_start_utc

DELAY_SECONDS = 2

# Estado de la última búsqueda de cada usuario (en memoria, suficiente en local)
RUNS: dict[int, dict] = {}


def new_state(sources: list[str]) -> dict:
    return {
        "state": "running",
        "message": "Iniciando búsqueda...",
        "sources": {
            k: {"state": "pending", "found": 0, "error": ""} for k in sources
        },
        "new_jobs": 0,
        "duplicates": 0,
        "total": 0,
    }


def run_search(user_id: int, sources: list[str]) -> None:
    state = RUNS[user_id]
    week_start = current_week_start_utc()
    try:
        with SessionLocal() as db:
            user = db.get(User, user_id)
            p = user.profile
            found = {}

            for key in sources:
                src = SOURCES[key]
                st = state["sources"][key]
                st["state"] = "running"
                if src.batch_search or src.user_batch_search:
                    state["message"] = (
                        f"Buscando {len(p.desired_titles)} cargos en {src.label}..."
                    )
                    try:
                        if src.user_batch_search:
                            jobs = src.user_batch_search(
                                user_id, p.desired_titles, p.city
                            )
                        else:
                            jobs = src.batch_search(p.desired_titles, p.city)
                    except ScraperError as e:
                        for partial in getattr(e, "partial_jobs", []):
                            found[partial.url] = partial
                        st["found"] = sum(
                            1 for job in found.values() if job.source == key
                        )
                        st["error"] = str(e)
                        st["state"] = "error"
                        continue
                    for job in jobs:
                        found[job.url] = job
                    st["found"] = sum(1 for job in found.values() if job.source == key)
                    st["state"] = "done"
                    continue
                for title in p.desired_titles:
                    state["message"] = f"Buscando '{title}' en {src.label}..."
                    try:
                        jobs = src.search(title, p.city)
                    except ScraperError as e:
                        st["error"] = str(e)
                        break
                    for j in jobs:
                        found[j.url] = j
                    st["found"] = sum(1 for j in found.values() if j.source == key)
                    time.sleep(DELAY_SECONDS)
                st["state"] = "error" if st["error"] else "done"

            if not found and any(s["error"] for s in state["sources"].values()):
                state.update(
                    state="error",
                    message="No se pudieron obtener ofertas. Revisa el detalle de cada fuente.",
                )
                return

            state["message"] = "Guardando ofertas..."

            # Huellas de las vacantes que esta persona ya tiene (incluye las descartadas)
            known = {}
            owned = db.execute(
                select(Job)
                .join(UserJob, UserJob.job_id == Job.id)
                .where(
                    UserJob.user_id == user_id,
                    UserJob.created_at >= week_start,
                )
            ).scalars()
            for ej in owned:
                fp = fingerprint(ej.title, ej.company, ej.location)
                if fp:
                    known.setdefault(fp, ej.id)

            new = 0
            duplicates = 0
            for j in found.values():
                job = db.scalar(select(Job).where(Job.url == j.url))
                if job:
                    # Mismo enlace: solo actualiza los datos por si el scraper mejoró
                    job.title = j.title[:300]
                    job.company = j.company[:200]
                    job.location = j.location[:200]
                    job.text = j.text
                    if j.published_at is not None:
                        job.published_at = j.published_at
                else:
                    fp = fingerprint(j.title, j.company, j.location)
                    if fp and fp in known:
                        duplicates += 1  # la misma vacante ya publicada con otro enlace
                        continue
                    job = Job(
                        source=j.source,
                        url=j.url,
                        title=j.title[:300],
                        company=j.company[:200],
                        location=j.location[:200],
                        text=j.text,
                        published_at=j.published_at,
                    )
                    db.add(job)
                    db.flush()
                    if fp:
                        known[fp] = job.id

                score, matched = score_job(p, j.title, j.text)
                uj = db.scalar(
                    select(UserJob).where(
                        UserJob.user_id == user_id, UserJob.job_id == job.id
                    )
                )
                if uj:
                    if uj.created_at < week_start:
                        uj.created_at = datetime.now(timezone.utc)
                        uj.dismissed = False
                        uj.ai_analysis = None
                    uj.score, uj.matched_terms = score, matched
                else:
                    db.add(
                        UserJob(
                            user_id=user_id,
                            job_id=job.id,
                            score=score,
                            matched_terms=matched,
                        )
                    )
                    new += 1
            db.commit()

        state.update(
            state="done",
            message=(
                f"Listo: {len(found)} ofertas revisadas, {new} nuevas, "
                f"{duplicates} repetidas omitidas."
            ),
            new_jobs=new,
            duplicates=duplicates,
            total=len(found),
        )
    except Exception as e:  # noqa: BLE001
        state.update(state="error", message=f"Error inesperado: {e}")
