"""Validate and normalize small user profile avatars before database storage."""
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_AVATAR_BYTES = 2 * 1024 * 1024
MAX_AVATAR_PIXELS = 16_000_000
MAX_AVATAR_DIMENSION = 512
_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def normalize_avatar(data: bytes) -> bytes:
    """Return a metadata-free WebP avatar or raise ValueError for invalid input."""
    if not data:
        raise ValueError("El archivo está vacío.")
    if len(data) > MAX_AVATAR_BYTES:
        raise ValueError("La foto no puede superar 2 MB.")

    try:
        with Image.open(BytesIO(data)) as original:
            if original.format not in _ALLOWED_FORMATS:
                raise ValueError("Usa una imagen JPG, PNG o WebP.")
            width, height = original.size
            if width <= 0 or height <= 0 or width * height > MAX_AVATAR_PIXELS:
                raise ValueError("La imagen supera el límite de dimensiones permitido.")
            original.verify()

        with Image.open(BytesIO(data)) as original:
            image = ImageOps.exif_transpose(original)
            image.thumbnail(
                (MAX_AVATAR_DIMENSION, MAX_AVATAR_DIMENSION),
                Image.Resampling.LANCZOS,
            )
            if "A" in image.getbands():
                rgba = image.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                image = Image.alpha_composite(background, rgba).convert("RGB")
            else:
                image = image.convert("RGB")

            output = BytesIO()
            image.save(output, format="WEBP", quality=86, method=6)
            return output.getvalue()
    except ValueError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("No se pudo leer la imagen. Elige un archivo JPG, PNG o WebP válido.") from exc
