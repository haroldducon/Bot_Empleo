from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Profile

GENERIC = {
    "analista", "asistente", "auxiliar", "profesional", "junior", "senior",
    "jr", "sr", "especialista", "de", "del", "la", "el", "en", "y", "para", "con", "a",
}
STOPWORDS = GENERIC | {
    "un", "una", "unos", "unas", "por", "que", "se", "su", "sus", "lo", "las",
    "los", "al", "es", "son", "ser", "tener", "conocimiento", "experiencia",
    "empresa", "compania", "compañia", "trabajo", "laboral", "funciones", "responsable",
    "realizar", "manejo", "manejar", "apoyo", "apoyar", "actividades", "requisitos",
    "oferta", "vacante", "busca", "buscamos", "requiere", "requerimos", "anos", "ano",
}
SYNONYMS = {
    "datos": {"data"},
    "data": {"datos"},
    "analista": {"analyst"},
    "analyst": {"analista"},
}
BROAD_EXPERIENCE_TITLES = {
    "administrador", "asesor", "coordinador", "director", "ejecutivo", "gerente",
    "gestor", "jefe", "supervisor", "consultor", "representante", "vendedor",
}
MODALITIES = {
    "remoto": ("remot", "remoto"),
    "hibrido": ("hibrid", "híbrido"),
    "presencial": ("presencial", "presencial"),
}
# Solo se infiere el nivel cuando aparece expresamente en el título del estudio/oferta.
EDUCATION_LEVELS = (
    ("doctorado", 6, re.compile(r"\bdoctor(?:ado|a|al)\b")),
    ("maestría", 5, re.compile(r"\b(?:maestr[ií]a|mag[ií]ster|m[aá]ster)\b")),
    ("especialización", 4, re.compile(r"\b(?:especializaci[oó]n|especialista)\b")),
    ("profesional", 3, re.compile(r"\bprofesional\b")),
    ("tecnólogo", 2, re.compile(r"\btecn[oó]log[oa]s?\b")),
    ("técnico", 1, re.compile(r"\bt[eé]cnic[oa]s?\b")),
)
MONEY_PATTERN = re.compile(
    r"(?:\b(?:cop|col\$)\s*|\$\s*)(\d[\d.,\s]{4,}\d|\d{6,9})"
    r"|\b(\d{1,3}(?:[.,]\d{3})+)\s*(?:cop|pesos)\b",
    re.IGNORECASE,
)


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
        "status": status,  # ok | partial | missing | unknown
        "detail": detail,
        "fix": fix,
        "where": where,  # profile | offer | None
    }


def _important_words(text: str) -> set[str]:
    return {w for w in words(text) if w not in STOPWORDS and len(w) > 2}


def _explicit_education_levels(text: str) -> list[tuple[str, int]]:
    folded = norm(text)
    found = [(name, level) for name, level, pattern in EDUCATION_LEVELS if pattern.search(folded)]
    return sorted(found, key=lambda item: item[1])


def _required_education_levels(text: str) -> list[tuple[str, int]]:
    folded = norm(text)
    context_pattern = re.compile(
        r"\b(?:formacion|academic\w*|educacion|estudios|nivel|titulo|requisit\w*|"
        r"graduad\w*|egresad\w*|requiere|requieren|exige|solicita)\b"
    )
    found = set()
    # El nivel y la palabra que lo convierte en requisito deben aparecer en la misma frase.
    for clause in re.split(r"[;.!?\n]+", folded):
        if re.search(r"\b(?:no se requiere|no requiere|no es requisito|sin requerir|no obligatori\w*)\b", clause):
            continue
        for name, level, pattern in EDUCATION_LEVELS:
            for match in pattern.finditer(clause):
                before = clause[max(0, match.start() - 60):match.start()]
                after = clause[match.end():match.end() + 35]
                if context_pattern.search(before) or re.search(r"\b(?:requerid\w*|obligatori\w*)\b", after):
                    found.add((name, level))
                    break
    return sorted(found, key=lambda item: item[1])


def _parse_salary_amounts(text: str) -> list[int]:
    amounts = []
    for match in MONEY_PATTERN.finditer(text or ""):
        raw = (match.group(1) or match.group(2) or "").strip()
        digits = re.sub(r"\D", "", raw)
        if not digits:
            continue
        try:
            amount = int(digits)
        except ValueError:
            continue
        # Evita interpretar cantidades pequeñas, años o identificadores como salario COP.
        if 100_000 <= amount <= 2_000_000_000:
            amounts.append(amount)
    return amounts


def _experience_match(profile: Profile, title: str, text: str) -> tuple[int, str, str, bool]:
    experiences = list(profile.experiences or [])
    profile_terms: set[str] = set()
    experience_parts: list[tuple[set[str], set[str]]] = []
    for experience in experiences:
        position = getattr(experience, "position", "") or ""
        position_terms = _important_words(position)
        description_terms = _important_words(getattr(experience, "description", "") or "")
        profile_terms |= position_terms | description_terms
        experience_parts.append((position_terms, description_terms))
    if not profile_terms:
        return 0, "unknown", "No hay experiencia laboral suficiente registrada para compararla.", False

    offer_text = f"{title} {text}"
    offer_terms = _important_words(offer_text)
    if not offer_terms:
        return 0, "unknown", "La fuente no entregó texto suficiente para comparar la experiencia.", False

    shared = profile_terms & offer_terms
    strong_hits: set[str] = set()
    for position_terms, description_terms in experience_parts:
        position_hits = position_terms & offer_terms
        if len(position_terms) >= 2:
            if len(position_hits) >= 2 and len(position_hits) / len(position_terms) >= 0.6:
                strong_hits |= position_hits
        elif len(position_terms) == 1:
            term = next(iter(position_terms))
            if term in position_hits and term not in BROAD_EXPERIENCE_TITLES:
                strong_hits.add(term)

        description_hits = description_terms & offer_terms
        denominator = max(1, min(len(description_terms), 12))
        if len(description_hits) >= 3 and len(description_hits) / denominator >= 0.25:
            strong_hits |= description_hits

    if strong_hits:
        details = sorted(strong_hits)
        return 20, "ok", f"La experiencia registrada comparte términos relevantes con la oferta: {', '.join(details[:5])}.", True
    if shared:
        details = sorted(shared)
        return 10, "partial", f"Hay una relación posible por estos términos, pero conviene revisar las funciones: {', '.join(details[:5])}.", False
    return 0, "missing", "No se encontró una relación textual clara entre la experiencia registrada y la oferta.", False


def explain_job(profile: Profile, title: str, text: str, location: str = "") -> dict:
    title_words = set(words(title))
    combined_text = f"{title} {text} {location}".strip()
    body = " ".join(words(combined_text))
    criteria: list[dict] = []
    matched: list[str] = []

    # 1. Cargo: 25 puntos.
    wanted_list = [w for w in (profile.desired_titles or []) if words(w)]
    if not wanted_list:
        criteria.append(_crit("cargo", "Cargo", 0, 25, "unknown", "No has indicado qué cargos buscas.", "Agrega al menos un cargo en tu perfil.", "profile"))
    else:
        best = (-1, "", [], False)
        for wanted in wanted_list:
            ws = words(wanted)
            distinct = [w for w in ws if w not in GENERIC]
            if distinct:
                missing_w = [w for w in distinct if not has_word(title_words, w)]
                hit = (len(distinct) - len(missing_w)) / len(distinct)
                pts = 25 if hit == 1 else (10 if hit >= 0.5 else 0)
                generic_only = False
            else:
                missing_w = []
                pts = 10 if any(has_word(title_words, w) for w in ws) else 0
                generic_only = True
            if pts > best[0]:
                best = (pts, wanted, missing_w, generic_only)
        pts, wanted, missing_w, generic_only = best
        if pts == 25:
            criteria.append(_crit("cargo", "Cargo", 25, 25, "ok", f"El título coincide con tu cargo «{wanted}»."))
            matched.append(f"cargo: {wanted}")
        elif pts == 10:
            detail = f"Solo coincide una palabra general de «{wanted}»." if generic_only else f"Coincide parcialmente con «{wanted}»."
            criteria.append(_crit("cargo", "Cargo", 10, 25, "partial", detail, "Revisa si este cargo corresponde a tu objetivo."))
            matched.append(f"cargo parecido: {wanted}")
        else:
            criteria.append(_crit("cargo", "Cargo", 0, 25, "missing", "El título no coincide claramente con los cargos de tu perfil.", "Agrega el cargo si te interesa este tipo de puesto.", "profile"))

    # 2. Habilidades: 20 puntos.
    skills = [s for s in (profile.skills or []) if s.strip()]
    if not skills:
        criteria.append(_crit("habilidades", "Habilidades", 0, 20, "unknown", "No has agregado habilidades al perfil.", "Agrega herramientas y conocimientos en tu perfil.", "profile"))
    else:
        found = [s for s in skills if has_phrase(body, s)]
        need = min(len(skills), 3)
        pts = round(20 * min(len(found), 3) / need)
        matched.extend(found)
        if pts == 20:
            criteria.append(_crit("habilidades", "Habilidades", 20, 20, "ok", f"La oferta menciona {len(found)} de tus habilidades: {', '.join(found)}."))
        elif found:
            criteria.append(_crit("habilidades", "Habilidades", pts, 20, "partial", f"La oferta menciona {len(found)} de tus {len(skills)} habilidades: {', '.join(found)}.", "Revisa las habilidades faltantes en el detalle."))
        else:
            criteria.append(_crit("habilidades", "Habilidades", 0, 20, "missing", "La oferta no menciona las habilidades registradas en tu perfil."))

    # 3. Experiencia laboral relacionada: 20 puntos.
    points, status, detail, strongly_related = _experience_match(profile, title, text)
    criteria.append(_crit("experiencia", "Experiencia relacionada", points, 20, status, detail, "Agrega funciones y logros concretos en tu perfil o revisa el detalle de la oferta." if status in {"partial", "missing", "unknown"} else None, "profile" if status == "unknown" else "offer" if status in {"partial", "missing"} else None))
    if status == "ok":
        matched.append("experiencia relacionada")

    # 4. Nivel de estudios: reconoce solo el nivel escrito en el título del perfil.
    education_rows = list(profile.education or [])
    profile_levels = []
    for education in education_rows:
        profile_levels.extend(_explicit_education_levels(getattr(education, "degree", "") or ""))
    offer_levels = _required_education_levels(combined_text)
    if not education_rows or not profile_levels or not offer_levels:
        if not education_rows:
            detail = "No has registrado estudios en tu perfil."
            fix = "Agrega el título tal como aparece en tu formación; no se inferirá el nivel por el nombre de la carrera."
            where = "profile"
        elif not profile_levels and offer_levels:
            detail = "La oferta menciona nivel educativo, pero el título de tu perfil no indica explícitamente si es técnico, tecnólogo o profesional."
            fix = "Verifica el nivel en el título del estudio de tu perfil."
            where = "profile"
        else:
            detail = "La oferta no indica explícitamente un nivel educativo requerido."
            fix = None
            where = None
        criteria.append(_crit("estudios", "Nivel de estudios", 0, 15, "unknown", detail, fix, where))
    else:
        required_name, required_level = offer_levels[0]
        profile_name, profile_level = max(profile_levels, key=lambda item: item[1])
        if profile_level >= required_level:
            criteria.append(_crit("estudios", "Nivel de estudios", 15, 15, "ok", f"La oferta menciona «{required_name}» y tu perfil registra «{profile_name}» o un nivel superior."))
            matched.append(f"estudios: {profile_name}")
        else:
            criteria.append(_crit("estudios", "Nivel de estudios", 0, 15, "missing", f"La oferta menciona «{required_name}»; tu nivel explícito registrado es «{profile_name}». Verifica si aceptan equivalencias o experiencia relacionada.", "Confirma los requisitos en el anuncio original.", "offer"))

    # 5. Salario: 10 puntos; sin cifra publicada queda como desconocido, no como incumplimiento.
    expected = getattr(profile, "salary_min", None)
    salaries = _parse_salary_amounts(combined_text)
    salary_status = "target_missing"
    salary_detail = ""
    salary_points = 0
    if not expected:
        salary_detail = "No indicaste salario mínimo esperado en tu perfil."
    elif not salaries:
        salary_status = "unknown"
        salary_detail = "Salario no informado por la oferta; no se penaliza la coincidencia por falta de este dato."
    else:
        low, high = min(salaries), max(salaries)
        if high < expected:
            salary_status = "missing"
            salary_detail = f"El máximo publicado ({high:,} COP) está por debajo de tu mínimo ({expected:,} COP).".replace(",", ".")
        elif low >= expected:
            salary_status = "ok"
            salary_points = 10
            salary_detail = f"El salario publicado es compatible con tu mínimo de {expected:,} COP.".replace(",", ".")
        else:
            salary_status = "partial"
            salary_points = 5
            salary_detail = f"El rango publicado ({low:,}–{high:,} COP) se cruza con tu mínimo ({expected:,} COP); verifica el valor ofrecido.".replace(",", ".")
    criteria.append(_crit("salario", "Salario", salary_points, 10, salary_status, salary_detail, "Confirma el rango directamente en el anuncio." if salary_status in {"partial", "missing", "unknown"} and expected else None, "offer" if salary_status in {"partial", "missing", "unknown"} and expected else None))

    # 6. Ubicación: 5 puntos.
    city_raw = (profile.city or "").strip()
    city = " ".join(words(city_raw))
    location_text = " ".join(words(f"{location} {text}"))
    if not city:
        criteria.append(_crit("ciudad", "Ciudad", 0, 5, "unknown", "No indicaste tu ciudad.", "Agrega tu ciudad en el perfil.", "profile"))
    elif city in location_text:
        criteria.append(_crit("ciudad", "Ciudad", 5, 5, "ok", f"La oferta coincide con tu ciudad ({city_raw})."))
        matched.append(f"ciudad: {city_raw}")
    elif any(term in location_text for term in ("remoto", "teletrabajo", "home office")):
        criteria.append(_crit("ciudad", "Ciudad", 5, 5, "ok", "La oferta indica trabajo remoto."))
        matched.append("ubicación remota")
    elif location or text:
        criteria.append(_crit("ciudad", "Ciudad", 0, 5, "missing", f"La oferta no indica que esté en {city_raw} ni que sea remota."))
    else:
        criteria.append(_crit("ciudad", "Ciudad", 0, 5, "unknown", "La fuente no entregó ubicación verificable."))

    # 7. Modalidad: 5 puntos.
    modality = (profile.modality or "cualquiera").strip().lower()
    if modality not in MODALITIES:
        criteria.append(_crit("modalidad", "Modalidad", 5, 5, "ok", "Aceptas cualquier modalidad."))
    else:
        stem, label = MODALITIES[modality]
        if stem in body:
            criteria.append(_crit("modalidad", "Modalidad", 5, 5, "ok", f"La oferta indica modalidad {label}, como prefieres."))
            matched.append(label)
        elif text:
            criteria.append(_crit("modalidad", "Modalidad", 0, 5, "missing", f"La oferta no indica que sea {label}.", "Revisa la modalidad en el anuncio original."))
        else:
            criteria.append(_crit("modalidad", "Modalidad", 0, 5, "unknown", "La fuente no informó la modalidad."))

    known = [criterion for criterion in criteria if criterion["status"] != "unknown"]
    known_max = sum(criterion["max_points"] for criterion in known)
    points = sum(criterion["points"] for criterion in known)
    score = round(100 * points / known_max) if known_max else 0
    evidence_coverage = round(known_max)

    salary_incompatible = salary_status == "missing"
    education_mismatch = any(c["key"] == "estudios" and c["status"] == "missing" for c in criteria)
    education_uncertain = any(c["key"] == "estudios" and c["status"] == "unknown" and offer_levels for c in criteria)
    salary_compatible_or_unknown = salary_status in {"ok", "partial", "unknown"}
    review_reasons: list[str] = []
    if salary_incompatible:
        review_reasons.append("El salario publicado queda por debajo de tu mínimo; revisa si aceptarías una excepción.")
    if education_mismatch:
        review_reasons.append("El nivel de estudios podría no cumplir; confirma equivalencias y experiencia aceptada.")
    if education_uncertain:
        review_reasons.append("El nivel educativo de tu perfil no se puede clasificar con confianza a partir del título registrado.")
    if salary_status == "partial":
        review_reasons.append("El rango salarial se cruza parcialmente con tu expectativa.")
    if score < 30 and strongly_related and salary_compatible_or_unknown:
        review_reasons.append("Aunque el puntaje general es menor de 30%, tu experiencia parece claramente relacionada y el salario es compatible o no está informado.")
    elif score >= 30 and evidence_coverage < 50:
        review_reasons.append("La fuente aportó pocos datos para dar una coincidencia segura.")
    elif score >= 30 and status == "partial":
        review_reasons.append("La relación con tu experiencia es posible, pero necesita revisión manual.")

    review = bool(review_reasons)
    if score < 30 and not (strongly_related and salary_compatible_or_unknown):
        classification = "excluded"
    elif review:
        classification = "review"
    elif score >= 30:
        classification = "match"
    else:
        classification = "excluded"

    return {
        "score": score,
        "criteria": criteria,
        "matched": matched,
        "classification": classification,
        "review_reasons": review_reasons,
        "evidence_coverage": evidence_coverage,
        "salary_status": salary_status,
    }


def score_job(profile: Profile, title: str, text: str, location: str = "") -> tuple[int, list[str]]:
    result = explain_job(profile, title, text, location)
    return result["score"], result["matched"]
