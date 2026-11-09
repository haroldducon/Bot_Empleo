import re
import unicodedata


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def fingerprint(title: str, company: str, location: str = "") -> str | None:
    """Huella de una oferta: dos publicaciones con la misma huella son la misma vacante.

    Si no hay título o empresa, devuelve None (no se puede asegurar que sea repetida).
    """
    t, c, l = _norm(title), _norm(company), _norm(location)
    if not t or not c:
        return None
    return f"{t}|{c}|{l}"