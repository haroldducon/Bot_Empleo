import sys
import time

from sqlalchemy import select

from app.database import SessionLocal
from app.matching import score_job
from app.models import Job, User, UserJob
from app.scrapers import computrabajo


def main(email: str):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if not user or not user.profile:
            sys.exit("No existe ese usuario o no tiene perfil")
        p = user.profile
        if not p.desired_titles:
            sys.exit("Agrega al menos un cargo deseado en el perfil")

        found = {}
        for title in p.desired_titles:
            print(f"Buscando '{title}' en {p.city or 'toda Colombia'}...")
            for j in computrabajo.search(title, p.city):
                found[j.url] = j
            time.sleep(2)  # pausa entre consultas
        print(f"Ofertas encontradas: {len(found)}\n")

        results = []
        for j in found.values():
            job = db.scalar(select(Job).where(Job.url == j.url))
            if not job:
                job = Job(
                    source=j.source,
                    url=j.url,
                    title=j.title[:300],
                    company=j.company[:200],
                    location=j.location[:200],
                    text=j.text,
                )
                db.add(job)
                db.flush()
            score, matched = score_job(p, j.title, j.text)
            uj = db.scalar(
                select(UserJob).where(UserJob.user_id == user.id, UserJob.job_id == job.id)
            )
            if uj:
                uj.score, uj.matched_terms = score, matched
            else:
                db.add(UserJob(user_id=user.id, job_id=job.id, score=score, matched_terms=matched))
            results.append((score, j, matched))
        db.commit()

        for score, j, matched in sorted(results, key=lambda r: r[0], reverse=True)[:15]:
            print(f"{score:3d}%  {j.title}")
            print(f"      {j.company} | {j.location}")
            print(f"      {', '.join(matched) or 'sin coincidencias'}")
            print(f"      {j.url}\n")


if __name__ == "__main__":
    main(sys.argv[1])
