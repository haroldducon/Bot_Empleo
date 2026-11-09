import re
import unicodedata

from app.models import Profile

# Palabras de rol demasiado comunes: sola no basta para decir que la oferta encaja.
GENERIC = {
    "analista", "asistente", "auxiliar", "profesional", "junior", "senior",
    "jr", "sr", "especialista", "de", "del", "la", "el", "en", "y", "para", "con", "a",
}
SYNONYMS = {
    "datos": {"data"},
    "data": {"datos"},
    "analista": {"analyst"},
    "analyst": {"analista"},
}
MODALITIES = {
    "remoto": ("remot", "remoto"),
    "hibrido": ("hibrid", "híbrido"),
    "presencial": ("presencial", "presencial"),
}


def norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9+#. ]+", " ", t)


def words(text: str) -> list[str]:
    return [t.strip(".") for t in norm(text).split() if t.strip(".")]


def has_word(title_words: set[str], w: str) -> bool:
    return w in title_words or any(s in title_words for s in SYNONYMS.get(w, ()))


def has_phrase(body: str, phrase: str) -> bool:
    p = " ".join(words(phrase))
    return bool(p) and f" {p} " in f" {body} "


def _crit(key, label, points, max_points, status, detail, fix=None, where=None):
    return {
        "key": key,
        "label": label,
        "points": points,
        "max_points": max_points,
        "status": status,  # ok | partial | missing
        "detail": detail,
        "fix": fix,
        "where": where,  # profile | offer | None
    }


def explain_job(profile: Profile, title: str, text: str) -> dict:
    title_words = set(words(title))
    body = " ".join(words(f"{title} {text}"))
    criteria: list[dict] = []
    matched: list[str] = []

    # 1. Cargo (40 puntos)
    wanted_list = [w for w in profile.desired_titles if words(w)]
    if not wanted_list:
        criteria.append(_crit(
            "cargo", "Cargo", 0, 40, "missing",
            "No has indicado qué cargos buscas.",
            "Agrega al menos un cargo en tu perfil.", "profile",
        ))
    else:
        best = (-1, "", [], False)
        for wanted in wanted_list:
            ws = words(wanted)
            distinct = [w for w in ws if w not in GENERIC]
            if distinct:
                missing_w = [w for w in distinct if not has_word(title_words, w)]
                hit = (len(distinct) - len(missing_w)) / len(distinct)
                pts = 40 if hit == 1 else (15 if hit >= 0.5 else 0)
                generic_only = False
            else:
                missing_w = []
                pts = 15 if any(has_word(title_words, w) for w in ws) else 0
                generic_only = True
            if pts > best[0]:
                best = (pts, wanted, missing_w, generic_only)
        pts, wanted, missing_w, generic_only = best

        if pts == 40:
            criteria.append(_crit(
                "cargo", "Cargo", 40, 40, "ok",
                f"El título de la oferta coincide con tu cargo «{wanted}».",
            ))
            matched.append(f"cargo: {wanted}")
        elif pts == 15 and generic_only:
            criteria.append(_crit(
                "cargo", "Cargo", 15, 40, "partial",
                f"Solo coincide la palabra general de tu cargo «{wanted}».",
                "Escribe un cargo más específico en tu perfil (por ejemplo, «Analista de datos») para comparar mejor.",
                "profile",
            ))
            matched.append(f"cargo parecido: {wanted}")
        elif pts == 15:
            criteria.append(_crit(
                "cargo", "Cargo", 15, 40, "partial",
                f"Coincide en parte con tu cargo «{wanted}».",
                f"Para coincidencia total, el título debería incluir: {', '.join(missing_w)}.",
                "offer",
            ))
            matched.append(f"cargo parecido: {wanted}")
        else:
            criteria.append(_crit(
                "cargo", "Cargo", 0, 40, "missing",
                "El título de la oferta no se parece a ninguno de tus cargos.",
                f"Si te interesa este tipo de puesto, agrega «{title[:80]}» a tus cargos.",
                "profile",
            ))

    # 2. Habilidades (40 puntos). Con 3 habilidades encontradas ya es puntaje completo.
    skills = [s for s in profile.skills if s.strip()]
    if not skills:
        criteria.append(_crit(
            "habilidades", "Habilidades", 0, 40, "missing",
            "No has agregado habilidades a tu perfil.",
            "Agrega tus herramientas y conocimientos en tu perfil.", "profile",
        ))
    else:
        found = [s for s in skills if has_phrase(body, s)]
        absent = [s for s in skills if s not in found]
        need = min(len(skills), 3)
        pts = round(40 * min(len(found), 3) / need)
        matched += found
        if pts == 40:
            criteria.append(_crit(
                "habilidades", "Habilidades", 40, 40, "ok",
                f"La oferta menciona {len(found)} de tus habilidades: {', '.join(found)}.",
            ))
        else:
            detail = (
                f"La oferta menciona {len(found)} de tus {len(skills)} habilidades: {', '.join(found)}."
                if found
                else "La oferta no menciona ninguna de tus habilidades."
            )
            criteria.append(_crit(
                "habilidades", "Habilidades", pts, 40,
                "partial" if found else "missing",
                detail,
                f"Para el puntaje completo, la oferta debería mencionar {need - len(found)} habilidad(es) más de tu lista (no aparecen: {', '.join(absent[:5])}).",
                "offer",
            ))

    # 3. Ciudad (10 puntos)
    city_raw = profile.city.strip()
    city = " ".join(words(city_raw))
    if not city:
        criteria.append(_crit(
            "ciudad", "Ciudad", 0, 10, "missing",
            "No indicaste tu ciudad.",
            "Agrega tu ciudad en el perfil.", "profile",
        ))
    elif f" {city} " in f" {body} ":
        criteria.append(_crit(
            "ciudad", "Ciudad", 10, 10, "ok",
            f"La oferta es en {city_raw}.",
        ))
        matched.append(f"ciudad: {city_raw}")
    else:
        criteria.append(_crit(
            "ciudad", "Ciudad", 0, 10, "missing",
            f"La oferta no menciona {city_raw}.",
            "Revisa en la oferta dónde queda el trabajo.", "offer",
        ))

    # 4. Modalidad (10 puntos)
    if profile.modality not in MODALITIES:
        criteria.append(_crit(
            "modalidad", "Modalidad", 10, 10, "ok",
            "Aceptas cualquier modalidad.",
        ))
    else:
        stem, label = MODALITIES[profile.modality]
        if stem in body:
            criteria.append(_crit(
                "modalidad", "Modalidad", 10, 10, "ok",
                f"La oferta es {label}, como prefieres.",
            ))
            matched.append(label)
        else:
            criteria.append(_crit(
                "modalidad", "Modalidad", 0, 10, "missing",
                f"La oferta no indica que sea {label}.",
                f"Revisa la modalidad en la oferta, o cambia tu preferencia a «Cualquiera» en el perfil.",
                "offer",
            ))

    score = min(sum(c["points"] for c in criteria), 100)
    return {"score": score, "criteria": criteria, "matched": matched}


def score_job(profile: Profile, title: str, text: str) -> tuple[int, list[str]]:
    r = explain_job(profile, title, text)
    return r["score"], r["matched"]