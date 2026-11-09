import sys
from collections import defaultdict

from sqlalchemy import select

from app.database import SessionLocal
from app.dedupe import fingerprint
from app.models import Job, User, UserJob


def main(email: str, apply: bool):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if not user:
            sys.exit("No existe ese usuario")

        rows = db.execute(
            select(UserJob, Job)
            .join(Job, UserJob.job_id == Job.id)
            .where(UserJob.user_id == user.id)
        ).all()

        groups = defaultdict(list)
        for uj, j in rows:
            fp = fingerprint(j.title, j.company, j.location)
            if fp:
                groups[fp].append((uj, j))
        dup_groups = [g for g in groups.values() if len(g) > 1]

        extra = sum(len(g) - 1 for g in dup_groups)
        print(f"Ofertas guardadas: {len(rows)}")
        print(f"Vacantes repetidas: {len(dup_groups)} (sobran {extra} publicaciones)\n")

        hidden = 0
        for items in dup_groups:
            # Conserva la que tiene análisis de IA, luego la de mayor puntaje, luego la más antigua
            items.sort(
                key=lambda x: (x[0].ai_analysis is not None, x[0].score, -x[0].id),
                reverse=True,
            )
            keep, others = items[0], items[1:]

            if len(dup_groups) <= 15 or not apply:
                print(f"- {keep[1].title}  ({keep[1].company})")
                for uj, j in items:
                    mark = "conserva" if uj is keep[0] else "repetida"
                    state = " [descartada]" if uj.dismissed else ""
                    print(f"    {mark}{state}: {j.url}")

            if apply:
                if any(uj.dismissed for uj, _ in items):
                    # Si ya descartaste una, sus repeticiones también se ocultan
                    targets = [uj for uj, _ in items if not uj.dismissed]
                else:
                    targets = [uj for uj, _ in others]
                for uj in targets:
                    uj.dismissed = True
                    hidden += 1

        if apply:
            db.commit()
            print(f"\nListo: se ocultaron {hidden} publicaciones repetidas.")
        else:
            print("\nNo se cambió nada. Para ocultar las repetidas, ejecuta de nuevo con --apply")


if __name__ == "__main__":
    main(sys.argv[1], "--apply" in sys.argv)